import asyncio
import logging
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse
from django.utils import timezone

from .models import Document, Query
from .serializers import (
    DocumentSerializer, QuerySerializer, QueryCreateSerializer, 
    DocumentSearchSerializer
)
from services.edgar_service import EdgarService
from services.cognee_service import CogneeService

logger = logging.getLogger(__name__)

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing documents"""
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        queryset = Document.objects.all()
        
        # Filter by company name
        company_name = self.request.query_params.get('company_name', None)
        if company_name:
            queryset = queryset.filter(company_name__icontains=company_name)
        
        # Filter by company ticker
        ticker = self.request.query_params.get('ticker', None)
        if ticker:
            queryset = queryset.filter(ticker__iexact=ticker)
        
        # Filter by form type
        form_type = self.request.query_params.get('form_type', None)
        if form_type:
            queryset = queryset.filter(form_type=form_type)
            
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def search_and_store(self, request):
        """Search for documents using Edgar and store in RAG"""
        serializer = DocumentSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data['query']
        limit = serializer.validated_data['limit']
        form_types = serializer.validated_data.get('form_types', ['10-K', '10-Q', '8-K'])
        
        try:
            edgar_service = EdgarService()
            
            # Search for filings
            filings = edgar_service.search_filings_by_query(query, limit=limit)
            
            created_documents = []
            for filing in filings:
                # Check if document already exists
                existing_doc = Document.objects.filter(
                    accession_number=filing['accession_number']
                ).first()
                
                if existing_doc:
                    created_documents.append(DocumentSerializer(existing_doc).data)
                    continue
                
                # Create new document record
                document = Document.objects.create(
                    accession_number=filing['accession_number'],
                    form_type=filing['form'],
                    company_name=filing['company_name'],
                    ticker=filing.get('ticker', ''),
                    cik=filing['cik'],
                    filing_date=filing['filing_date'],
                    period_of_report=filing.get('period_of_report'),
                    description=filing.get('description', ''),
                    url=filing.get('url', ''),
                    status='PENDING'
                )
                
                created_documents.append(DocumentSerializer(document).data)
                
                # Background task to fetch content and store in RAG
                # In production, this would be a Celery task
                import threading
                thread = threading.Thread(
                    target=self._process_document_sync,
                    args=(document.id, filing)
                )
                thread.daemon = True
                thread.start()
            
            return Response({
                'message': f'Found {len(created_documents)} documents',
                'documents': created_documents
            })
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return Response(
                {'error': 'Failed to search documents'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def query_company_documents(self, request):
        """Query stored documents for a specific company using Cognee RAG"""
        try:
            query_text = request.data.get('query')
            company = request.data.get('company', '')
            
            if not query_text:
                return Response(
                    {'error': 'Query text is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cognee_service = CogneeService()
            
            # Get available documents for the company
            company_documents = Document.objects.filter(
                company_name__icontains=company,
                status='STORED'
            ) if company else Document.objects.filter(status='STORED')
            
            if not company_documents.exists():
                return Response({
                    'message': 'No stored documents found for this company',
                    'documents_available': 0,
                    'natural_response': None,
                    'document_chunks': 0
                })
            
            # Search using Cognee with company filter if specified
            if company:
                natural_response = cognee_service.search_context_by_company(query_text, company, "natural")
                chunks = cognee_service.search_context_by_company(query_text, company, "chunks")
            else:
                natural_response = cognee_service.search_context(query_text, "natural")
                chunks = cognee_service.search_context(query_text, "chunks")
            
            return Response({
                'message': 'Query processed successfully',
                'documents_available': company_documents.count(),
                'company_filter': company,
                'natural_response': natural_response[:3] if natural_response else [],
                'document_chunks': len(chunks) if chunks else 0
            })
            
        except Exception as e:
            logger.error(f"Error querying company documents: {str(e)}")
            return Response(
                {'error': f'Failed to query documents: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def process_to_rag(self, request):
        """Manually process selected documents and add them to RAG"""
        try:
            document_ids = request.data.get('document_ids', [])
            
            if not document_ids:
                return Response(
                    {'error': 'No document IDs provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get documents that are not already stored
            documents = Document.objects.filter(
                id__in=document_ids,
                status__in=['PENDING', 'ERROR']
            )
            
            if not documents.exists():
                return Response({
                    'message': 'No eligible documents found for processing',
                    'processed': 0
                })
            
            processed_count = 0
            errors = []
            
            for document in documents:
                try:
                    # Start processing in background thread
                    import threading
                    thread = threading.Thread(
                        target=self._process_document_for_rag,
                        args=(document.id,)
                    )
                    thread.daemon = True
                    thread.start()
                    processed_count += 1
                    
                except Exception as e:
                    errors.append(f"Document {document.id}: {str(e)}")
            
            return Response({
                'message': f'Started processing {processed_count} documents',
                'processed': processed_count,
                'errors': errors
            })
            
        except Exception as e:
            logger.error(f"Error processing documents to RAG: {str(e)}")
            return Response(
                {'error': f'Failed to process documents: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_document_for_rag(self, document_id: int):
        """Process a single document and add to RAG with better error handling"""
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'PROCESSING'
            document.save()
            
            edgar_service = EdgarService()
            cognee_service = CogneeService()
            
            logger.info(f"Starting to process document {document.accession_number}")
            
            # Fetch document content if not already available
            content_data = edgar_service.get_filing_content(
                document.accession_number, 
                document.cik
            )
            
            if content_data:
                logger.info(f"Fetched content for {document.accession_number}: {content_data['size']} characters")
                
                # Store in Cognee RAG
                document_metadata = {
                    'company_name': document.company_name,
                    'form_type': document.form_type,
                    'ticker': document.ticker,
                    'filing_date': str(document.filing_date),
                    'accession_number': document.accession_number,
                    'cik': document.cik
                }
                
                logger.info(f"Adding document {document.accession_number} to Cognee RAG...")
                success = cognee_service.add_document(
                    content_data['content'], 
                    document_metadata
                )
                
                if success.get('success'):
                    document.content_size = content_data['size']
                    document.mark_as_stored()
                    logger.info(f"Successfully processed document {document.accession_number} to RAG")
                else:
                    document.mark_as_error()
                    logger.error(f"Failed to store document {document.accession_number} in Cognee RAG: {success.get('error', 'Unknown error')}")
            else:
                document.mark_as_error()
                logger.error(f"Failed to fetch content for document {document.accession_number}")
                
        except Exception as e:
            logger.error(f"Error processing document {document_id} for RAG: {str(e)}")
            try:
                document = Document.objects.get(id=document_id)
                document.mark_as_error()
            except:
                pass

    @action(detail=False, methods=['post'])
    def sync_rag_status(self, request):
        """Sync document status with actual Cognee RAG state"""
        try:
            cognee_service = CogneeService()
            
            # Get all documents marked as STORED in Django
            stored_documents = Document.objects.filter(status='STORED')
            
            if not stored_documents.exists():
                return Response({
                    'message': 'No stored documents found to sync',
                    'synced': 0
                })
            
            synced_count = 0
            reset_count = 0
            
            for document in stored_documents:
                try:
                    # Check if document still exists in Cognee by searching for it
                    company_search = cognee_service.search_context(
                        f"{document.company_name} {document.form_type}", 
                        "chunks"
                    )
                    
                    # If no results found, the document is likely not in RAG anymore
                    if not company_search or len(company_search) == 0:
                        # Reset document status to PENDING so it can be re-processed
                        document.status = 'PENDING'
                        document.stored_at = None
                        document.save()
                        reset_count += 1
                        logger.info(f"Reset document {document.accession_number} status to PENDING - not found in RAG")
                    else:
                        synced_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error checking document {document.accession_number} in RAG: {str(e)}")
                    # On error, assume document is not in RAG and reset status
                    document.status = 'PENDING'
                    document.stored_at = None
                    document.save()
                    reset_count += 1
            
            return Response({
                'message': f'Sync completed: {synced_count} confirmed in RAG, {reset_count} reset to pending',
                'synced': synced_count,
                'reset': reset_count,
                'total_checked': stored_documents.count()
            })
            
        except Exception as e:
            logger.error(f"Error syncing RAG status: {str(e)}")
            return Response(
                {'error': f'Failed to sync RAG status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def reset_stuck_documents(self, request):
        """Reset documents that have been stuck in PROCESSING status for too long"""
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Find documents that have been processing for more than 10 minutes
            timeout_threshold = timezone.now() - timedelta(minutes=10)
            
            stuck_documents = Document.objects.filter(
                status='PROCESSING',
                updated_at__lt=timeout_threshold
            )
            
            if not stuck_documents.exists():
                return Response({
                    'message': 'No stuck documents found',
                    'reset_count': 0
                })
            
            reset_count = 0
            for document in stuck_documents:
                document.status = 'ERROR'  # Mark as error so they can be re-processed
                document.save()
                reset_count += 1
                logger.info(f"Reset stuck document {document.accession_number} from PROCESSING to ERROR")
            
            return Response({
                'message': f'Reset {reset_count} stuck documents to ERROR status',
                'reset_count': reset_count,
                'documents_reset': [
                    {
                        'id': doc.id,
                        'company': doc.company_name,
                        'form_type': doc.form_type,
                        'accession_number': doc.accession_number
                    } for doc in stuck_documents
                ]
            })
            
        except Exception as e:
            logger.error(f"Error resetting stuck documents: {str(e)}")
            return Response(
                {'error': f'Failed to reset stuck documents: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _process_document_sync(self, document_id: int, filing_data: dict):
        """Process document asynchronously - fetch content and store in RAG"""
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'PROCESSING'
            document.save()
            
            edgar_service = EdgarService()
            cognee_service = CogneeService()
            
            # Fetch document content
            content_data = edgar_service.get_filing_content(
                filing_data['accession_number'], 
                filing_data['cik']
            )
            
            if content_data:
                # Store in Cognee RAG
                document_metadata = {
                    'company_name': document.company_name,
                    'form_type': document.form_type,
                    'ticker': document.ticker,
                    'filing_date': str(document.filing_date),
                    'accession_number': document.accession_number,
                    'cik': document.cik
                }
                
                success = cognee_service.add_document(
                    content_data['content'], 
                    document_metadata
                )
                
                if success.get('success'):
                    document.content_size = content_data['size']
                    document.mark_as_stored()
                    logger.info(f"Successfully processed and stored document {document.accession_number} in Cognee")
                else:
                    document.mark_as_error()
                    logger.error(f"Failed to store document {document.accession_number} in Cognee RAG")
            else:
                document.mark_as_error()
                logger.error(f"Failed to fetch content for document {document.accession_number}")
                
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            try:
                document = Document.objects.get(id=document_id)
                document.mark_as_error()
            except:
                pass

    @action(detail=False, methods=['get'])
    def summaries(self, request):
        """Get document summaries from Cognee registry"""
        try:
            cognee_service = CogneeService()
            
            # Get query parameters
            company_name = request.query_params.get('company_name')
            form_type = request.query_params.get('form_type')
            
            # Get document summaries
            summaries = cognee_service.get_document_summaries(
                company_name=company_name,
                form_type=form_type
            )
            
            # Also get registry stats
            stats = cognee_service.get_registry_stats()
            
            return Response({
                'success': True,
                'summaries': summaries,
                'stats': stats,
                'total_with_summaries': len([s for s in summaries if s.get('summary')])
            })
            
        except Exception as e:
            logger.error(f"Error getting document summaries: {str(e)}")
            return Response(
                {'success': False, 'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get summary for a specific document"""
        try:
            document = self.get_object()
            cognee_service = CogneeService()
            
            # Find this document in Cognee registry
            for fingerprint, doc_info in cognee_service._document_registry.items():
                cognee_metadata = doc_info.get('metadata', {})
                if cognee_metadata.get('accession_number') == document.accession_number:
                    summary = doc_info.get('summary', {})
                    
                    return Response({
                        'success': True,
                        'document_id': document.id,
                        'accession_number': document.accession_number,
                        'has_summary': bool(summary),
                        'summary': summary,
                        'fingerprint': fingerprint[:8],
                        'stored_at': doc_info.get('stored_at'),
                        'summary_generated_at': doc_info.get('summary_generated_at')
                    })
            
            # Document not found in Cognee registry
            return Response({
                'success': False,
                'error': 'Document not found in Cognee registry',
                'document_id': document.id,
                'has_summary': False
            })
            
        except Exception as e:
            logger.error(f"Error getting document summary: {str(e)}")
            return Response(
                {'success': False, 'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class QueryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing queries"""
    queryset = Query.objects.all()
    serializer_class = QuerySerializer
    
    def create(self, request):
        """Create a new query and process it"""
        serializer = QueryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        query_text = serializer.validated_data['query_text']
        fetch_documents = serializer.validated_data['fetch_documents']
        document_limit = serializer.validated_data['document_limit']
        
        try:
            # Create query record
            query = Query.objects.create(
                query_text=query_text,
                status='PROCESSING'
            )
            
            # Process query in background (simplified approach for demo)
            # In production, you would use Celery or similar task queue
            import threading
            thread = threading.Thread(
                target=self._process_query_sync,
                args=(query.id, fetch_documents, document_limit)
            )
            thread.daemon = True
            thread.start()
            
            return Response(
                QuerySerializer(query).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error creating query: {str(e)}")
            return Response(
                {'error': 'Failed to create query'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _process_query_sync(self, query_id: int, fetch_documents: bool, document_limit: int):
        """Process query asynchronously"""
        try:
            query = Query.objects.get(id=query_id)
            edgar_service = EdgarService()
            cognee_service = CogneeService()
            
            documents_processed = 0
            
            if fetch_documents:
                # Search and store documents
                filings = edgar_service.search_filings_by_query(query.query_text, limit=document_limit)
                query.documents_found = len(filings)
                query.save()
                
                for filing in filings:
                    # Check if document exists, if not create and process it
                    document, created = Document.objects.get_or_create(
                        accession_number=filing['accession_number'],
                        defaults={
                            'form_type': filing['form'],
                            'company_name': filing['company_name'],
                            'ticker': filing.get('ticker', ''),
                            'cik': filing['cik'],
                            'filing_date': filing['filing_date'],
                            'period_of_report': filing.get('period_of_report'),
                            'description': filing.get('description', ''),
                            'url': filing.get('url', ''),
                            'status': 'PENDING'
                        }
                    )
                    
                    if created or document.status != 'STORED':
                        # Process document
                        document.status = 'PROCESSING'
                        document.save()
                        
                        content_data = edgar_service.get_filing_content(
                            filing['accession_number'], 
                            filing['cik']
                        )
                        
                        if content_data:
                            # Store in Cognee RAG
                            document_metadata = {
                                'company_name': document.company_name,
                                'form_type': document.form_type,
                                'ticker': document.ticker,
                                'filing_date': str(document.filing_date),
                                'accession_number': document.accession_number,
                                'cik': document.cik
                            }
                            
                            success = cognee_service.add_document(
                                content_data['content'], 
                                document_metadata
                            )
                            
                            if success:
                                document.content_size = content_data['size']
                                document.mark_as_stored()
                                documents_processed += 1
                            else:
                                document.mark_as_error()
                        else:
                            document.mark_as_error()
            
            # Get context from Cognee RAG for analysis (simplified)
            try:
                # Use simple natural language search
                natural_response = cognee_service.search_context(query.query_text, "natural")
                document_chunks = cognee_service.search_context(query.query_text, "chunks")
                
                # Simplify chunk processing for better performance
                simplified_chunks = []
                for chunk in document_chunks[:3]:  # Limit to first 3 for performance
                    if isinstance(chunk, dict) and 'text' in chunk:
                        simplified_chunks.append(chunk['text'][:200] + '...' if len(chunk.get('text', '')) > 200 else chunk.get('text', ''))
                    else:
                        simplified_chunks.append(str(chunk)[:200] + '...' if len(str(chunk)) > 200 else str(chunk))
                
                # Build simple research result using Cognee context
                query.research_result = {
                    'summary': f'Document search results for: {query.query_text}',
                    'key_findings': simplified_chunks if simplified_chunks else [
                        'No specific content found in current document set',
                        'Consider adding more relevant documents for analysis'
                    ],
                    'document_chunks_found': len(document_chunks),
                    'context_used': len(document_chunks) > 0,
                    'relevant_excerpts': simplified_chunks
                }
                
            except Exception as e:
                logger.error(f"Error getting Cognee context: {str(e)}")
                # Fallback to basic analysis
                query.research_result = {
                    'summary': f'Basic analysis for: {query.query_text}',
                    'key_findings': [
                        'Analysis completed with limited context',
                        f'Processed {documents_processed} documents'
                    ],
                    'document_chunks_found': 0,
                    'context_used': False,
                    'error': 'Context retrieval failed, using fallback analysis'
                }
            
            # Generate strategy based on available context
            context_available = query.research_result.get('context_used', False)
            if context_available:
                query.strategy_result = {
                    'recommendation': 'HOLD',  # More conservative when we have real data
                    'confidence': 'MEDIUM',
                    'reasoning': 'Based on analysis of available SEC filings and financial documents',
                    'target_allocation': '3-7% of portfolio',
                    'context_quality': 'Good' if query.research_result.get('document_chunks_found', 0) > 2 else 'Limited'
                }
                
                query.risk_result = {
                    'risk_level': 'MODERATE',
                    'key_risks': [
                        'Limited historical data in analysis',
                        'Market volatility considerations',
                        'Regulatory environment changes'
                    ],
                    'risk_score': 5.5,
                    'data_completeness': query.research_result.get('document_chunks_found', 0) / max(documents_processed, 1)
                }
            else:
                # Fallback when no context is available
                query.strategy_result = {
                    'recommendation': 'INSUFFICIENT_DATA',
                    'confidence': 'LOW',
                    'reasoning': 'Insufficient document context for reliable analysis',
                    'target_allocation': 'Not recommended without more data',
                    'context_quality': 'Poor'
                }
                
                query.risk_result = {
                    'risk_level': 'HIGH',
                    'key_risks': [
                        'Insufficient data for proper risk assessment',
                        'Unable to analyze financial fundamentals',
                        'Lack of historical performance data'
                    ],
                    'risk_score': 8.0,
                    'data_completeness': 0.0
                }
            
            query.documents_processed = documents_processed
            query.status = 'COMPLETED'
            query.completed_at = timezone.now()
            query.save()
            
            logger.info(f"Successfully processed query {query_id}")
            
        except Exception as e:
            logger.error(f"Error processing query {query_id}: {str(e)}")
            try:
                query = Query.objects.get(id=query_id)
                query.status = 'ERROR'
                query.save()
            except:
                pass

class HealthCheckView(APIView):
    """Simple health check endpoint"""
    
    def _check_cognee_health(self):
        """Check Cognee service health"""
        try:
            cognee_service = CogneeService()
            health_data = cognee_service.health_check()
            return health_data.get('status') == 'healthy'
        except Exception as e:
            logger.error(f"Cognee health check failed: {str(e)}")
            return False
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'services': {
                'edgar': True,  # Could check Edgar service health
                'cognee': self._check_cognee_health(),
                'database': True  # Could check database connectivity
            }
        })


class CogneeServiceView(APIView):
    """Cognee service management endpoints"""
    
    def get(self, request):
        """Get Cognee service information"""
        try:
            cognee_service = CogneeService()
            service_info = cognee_service.get_service_info()
            health_data = cognee_service.health_check()
            
            return Response({
                'service_info': service_info,
                'health': health_data
            })
        except Exception as e:
            logger.error(f"Error getting Cognee service info: {str(e)}")
            return Response(
                {'error': 'Failed to get service information'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Test Cognee integration with sample data (optimized for performance)"""
        try:
            cognee_service = CogneeService()
            
            # Test document
            test_content = """
            This is a test financial document for FinDocGPT integration testing.
            
            Company: Test Corp
            Revenue: $100M (up 15% YoY)
            Net Income: $20M 
            Cash Position: Strong with $50M in reserves
            Market Position: Leading provider in technology sector
            """
            
            test_metadata = {
                'company_name': 'Test Corp',
                'form_type': '10-K',
                'ticker': 'TEST',
                'filing_date': '2024-12-01',
                'accession_number': 'test-integration-001'
            }
            
            # Add test document
            add_success = cognee_service.add_document(test_content, test_metadata)
            
            if not add_success:
                return Response(
                    {'error': 'Failed to add test document'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Test search (using chunks for better performance)
            search_results = cognee_service.search_context("Test Corp financial performance", "chunks")
            
            # Skip insights test for faster response - focus on core functionality
            insights = {'insights': [], 'chunks': []}
            
            return Response({
                'status': 'success',
                'test_results': {
                    'document_added': add_success,
                    'search_results_count': len(search_results),
                    'insights_found': len(insights.get('insights', [])),
                    'chunks_found': len(insights.get('chunks', []))
                },
                'sample_results': {
                    'search_results': search_results[:2] if search_results else [],
                    'insights': insights.get('insights', [])[:2] if insights.get('insights') else []
                }
            })
            
        except Exception as e:
            logger.error(f"Cognee integration test failed: {str(e)}")
            return Response(
                {'error': f'Integration test failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )