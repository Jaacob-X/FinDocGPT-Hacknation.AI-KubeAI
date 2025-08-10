from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging
import threading
from typing import Dict, Any

from .models import IterativeAnalysis
from .serializers import (
    IterativeAnalysisSerializer, 
    AnalysisCreateSerializer, 
    AnalysisSummarySerializer
)
from services.iterative_analysis_service import IterativeAnalysisService

logger = logging.getLogger(__name__)

class IterativeAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet for managing iterative financial analysis"""
    
    queryset = IterativeAnalysis.objects.all()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return AnalysisCreateSerializer
        elif self.action == 'list':
            return AnalysisSummarySerializer
        else:
            return IterativeAnalysisSerializer
    
    @method_decorator(csrf_exempt)
    def create(self, request):
        """Start a new iterative analysis"""
        serializer = AnalysisCreateSerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data['query']
            company_filter = serializer.validated_data.get('company_filter')
            
            # Create analysis record
            analysis = IterativeAnalysis.objects.create(
                query=query,
                company_filter=company_filter,
                status='IN_PROGRESS'
            )
            
            # Start analysis in background thread
            def run_analysis():
                self._process_analysis_async(analysis.id, query, company_filter)
            
            analysis_thread = threading.Thread(target=run_analysis)
            analysis_thread.daemon = True
            analysis_thread.start()
            
            # Return immediate response
            return Response({
                'id': analysis.id,
                'message': 'Iterative analysis started',
                'query': query,
                'company_filter': company_filter,
                'status': 'IN_PROGRESS',
                'estimated_completion': '2-5 minutes depending on complexity'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _process_analysis_async(self, analysis_id: int, query: str, company_filter: str = None):
        """Process analysis asynchronously in background"""
        try:
            analysis = IterativeAnalysis.objects.get(id=analysis_id)
            service = IterativeAnalysisService()
            
            logger.info(f"Starting iterative analysis {analysis_id} for query: {query[:50]}...")
            
            # Run the iterative analysis with cooperative cancellation
            results = service.run_iterative_analysis(
                query,
                company_filter,
                should_cancel=lambda: IterativeAnalysis.objects.filter(id=analysis.id, cancel_requested=True).exists(),
                analysis_id=analysis_id
            )
            
            if results.get('cancelled') or results.get('error') == 'cancelled':
                analysis.mark_cancelled(results, message='User cancelled analysis')
                logger.info(f"Analysis {analysis_id} cancelled by user")
            elif 'error' in results:
                # Pass partial results to mark_failed if available
                partial_results = {k: v for k, v in results.items() if k != 'error'}
                analysis.mark_failed(results['error'], partial_results if partial_results else None)
                logger.error(f"Analysis {analysis_id} failed: {results['error']}")
            else:
                analysis.mark_completed(results)
                logger.info(f"Analysis {analysis_id} completed successfully")

        except Exception as e:
            logger.error(f"Error processing analysis {analysis_id}: {str(e)}")
            try:
                analysis = IterativeAnalysis.objects.get(id=analysis_id)
                analysis.mark_failed(str(e))
            except:
                pass
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get analysis status and progress"""
        try:
            analysis = self.get_object()
            
            response_data = {
                'id': analysis.id,
                'status': analysis.status,
                'query': analysis.query,
                'company_filter': analysis.company_filter,
                'cancel_requested': analysis.cancel_requested,
                'created_at': analysis.created_at,
                'completed_at': analysis.completed_at if analysis.status == 'COMPLETED' else None,
                'progress': {
                    'total_iterations': analysis.total_iterations,
                    'documents_analyzed': analysis.documents_analyzed,
                    'rag_queries_executed': analysis.rag_queries_executed,
                    'final_completeness_score': analysis.final_completeness_score
                }
            }
            
            if analysis.status == 'COMPLETED':
                response_data['final_recommendation'] = analysis.get_final_recommendation()
                response_data['confidence_level'] = analysis.get_confidence_level()
            elif analysis.status in ['FAILED', 'CANCELLED']:
                if analysis.status == 'FAILED':
                    response_data['error_message'] = analysis.error_message

                # Include partial results information for terminated analyses
                response_data['has_partial_results'] = analysis.has_partial_results()
                if analysis.has_partial_results():
                    latest_analysis = analysis.get_latest_iteration_analysis()
                    if latest_analysis:
                        response_data['latest_iteration_analysis'] = latest_analysis
                    response_data['termination_reason'] = (
                        'Analysis was cancelled by user' if analysis.status == 'CANCELLED'
                        else f'Analysis failed: {analysis.error_message}'
                    )
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error getting analysis status: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get complete analysis results or partial results for terminated analyses"""
        try:
            analysis = self.get_object()

            # Allow results for completed analyses or terminated analyses with partial results
            if analysis.status == 'COMPLETED':
                # Full results for completed analyses
                pass
            elif analysis.status in ['CANCELLED', 'FAILED'] and analysis.has_partial_results():
                # Partial results for terminated analyses
                pass
            else:
                return Response({
                    'error': f'Analysis not completed and no partial results available. Current status: {analysis.status}',
                    'status': analysis.status
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return complete results
            serializer = IterativeAnalysisSerializer(analysis)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting analysis results: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Request cancellation of an in-progress analysis"""
        try:
            analysis = self.get_object()
            if analysis.status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                return Response({
                    'status': analysis.status,
                    'message': 'Analysis is no longer running'
                }, status=status.HTTP_200_OK)

            analysis.mark_cancel_requested()
            return Response({
                'id': analysis.id,
                'status': analysis.status,
                'cancel_requested': True,
                'message': 'Cancellation requested'
            })
        except Exception as e:
            logger.error(f"Error requesting cancellation: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Delete an analysis"""
        try:
            analysis = self.get_object()

            # Prevent deletion of running analyses
            if analysis.status == 'IN_PROGRESS':
                return Response({
                    'error': 'Cannot delete a running analysis. Please cancel it first.',
                    'status': analysis.status
                }, status=status.HTTP_400_BAD_REQUEST)

            analysis_id = analysis.id
            analysis_query = analysis.query[:50] + "..." if len(analysis.query) > 50 else analysis.query

            # Delete the analysis
            analysis.delete()

            logger.info(f"Analysis {analysis_id} deleted successfully")

            return Response({
                'message': f'Analysis "{analysis_query}" deleted successfully',
                'deleted_id': analysis_id
            }, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting analysis: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """Delete multiple analyses"""
        try:
            # Get analysis IDs from request data
            data = getattr(request, 'data', {}) or getattr(request, 'POST', {})
            analysis_ids = data.get('analysis_ids', [])

            if not analysis_ids:
                return Response({
                    'error': 'No analysis IDs provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get analyses to delete
            analyses = IterativeAnalysis.objects.filter(id__in=analysis_ids)

            # Check for running analyses
            running_analyses = analyses.filter(status='IN_PROGRESS')
            if running_analyses.exists():
                return Response({
                    'error': f'Cannot delete running analyses. Please cancel them first.',
                    'running_analyses': list(running_analyses.values_list('id', flat=True))
                }, status=status.HTTP_400_BAD_REQUEST)

            # Delete analyses
            deleted_count = analyses.count()
            analyses.delete()

            logger.info(f"Bulk deleted {deleted_count} analyses")

            return Response({
                'message': f'Successfully deleted {deleted_count} analyses',
                'deleted_count': deleted_count
            })

        except Exception as e:
            logger.error(f"Error bulk deleting analyses: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def iteration_details(self, request, pk=None):
        """Get detailed iteration history"""
        try:
            analysis = self.get_object()
            
            if not analysis.iteration_history:
                # Return empty history with 200 to allow frontend polling without errors
                return Response({
                    'analysis_id': analysis.id,
                    'query': analysis.query,
                    'total_iterations': analysis.total_iterations,
                    'final_score': analysis.final_completeness_score,
                    'iteration_history': [],
                    'status': analysis.status
                })
            
            # Process iteration history for better presentation
            formatted_history = []
            for iteration in analysis.iteration_history:
                formatted_iteration = {
                    'iteration': iteration.get('iteration', 0),
                    'type': iteration.get('type', 'unknown'),
                    'timestamp': iteration.get('timestamp'),
                }
                
                if iteration['type'] == 'initial_analysis':
                    formatted_iteration['summary'] = 'Generated comprehensive initial analysis'
                elif iteration['type'] == 'evaluation':
                    eval_data = iteration.get('evaluation', {})
                    formatted_iteration.update({
                        'completeness_score': eval_data.get('completeness_score', 0),
                        'is_complete': eval_data.get('is_analysis_complete', False),
                        'assessment': eval_data.get('overall_assessment', 'Unknown'),
                        'questions_raised': len(eval_data.get('specific_questions', []))
                    })
                elif iteration['type'] == 'rag_queries':
                    formatted_iteration.update({
                        'queries_executed': len(iteration.get('queries', [])),
                        'queries': iteration.get('queries', [])
                    })
                elif iteration['type'] == 'refined_analysis':
                    formatted_iteration['summary'] = 'Analysis refined with RAG results'
                
                formatted_history.append(formatted_iteration)
            
            return Response({
                'analysis_id': analysis.id,
                'query': analysis.query,
                'total_iterations': analysis.total_iterations,
                'final_score': analysis.final_completeness_score,
                'iteration_history': formatted_history
            })
            
        except Exception as e:
            logger.error(f"Error getting iteration details: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def service_status(self, request):
        """Check if the iterative analysis service is available"""
        try:
            service = IterativeAnalysisService()
            
            # Basic service check
            if not service.openai_client:
                return Response({
                    'available': False,
                    'error': 'OpenAI client not configured',
                    'requires': 'AGENT_LLM_API_KEY environment variable'
                })
            
            # Check Cognee service
            cognee_stats = service.cognee_service.get_registry_stats()
            
            return Response({
                'available': True,
                'service_ready': True,
                'documents_available': cognee_stats.get('total_documents', 0),
                'companies_available': len(cognee_stats.get('companies', [])),
                'capabilities': [
                    'Iterative analysis with self-improvement',
                    'RAG-powered document querying',
                    'Completeness evaluation and gap identification',
                    'Targeted information retrieval',
                    'Multi-iteration refinement'
                ]
            })
            
        except Exception as e:
            logger.error(f"Error checking service status: {str(e)}")
            return Response({
                'available': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def demo_analysis(self, request):
        """Run a quick demo analysis with predefined query"""
        demo_queries = [
            "Analyze Apple Inc's investment potential based on recent filings",
            "What are the key financial metrics and growth opportunities for the companies in our database?",
            "Provide a comprehensive risk assessment for investment decisions",
            "Compare the financial performance and market position of available companies"
        ]
        
        # Use first available demo query or custom query
        query = request.data.get('query', demo_queries[0])
        
        # Create and start analysis
        analysis = IterativeAnalysis.objects.create(
            query=query,
            status='IN_PROGRESS'
        )
        
        # Start analysis in background
        def run_demo():
            self._process_analysis_async(analysis.id, query)
        
        demo_thread = threading.Thread(target=run_demo)
        demo_thread.daemon = True
        demo_thread.start()
        
        return Response({
            'id': analysis.id,
            'message': 'Demo analysis started',
            'query': query,
            'demo_mode': True,
            'available_demo_queries': demo_queries
        }, status=status.HTTP_201_CREATED)
