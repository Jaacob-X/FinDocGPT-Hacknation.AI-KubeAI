import asyncio
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from functools import lru_cache
import hashlib
import json

# Configure Cognee paths BEFORE importing cognee
def _configure_cognee_paths():
    """Configure Cognee paths at module level"""
    try:
        # Get project root (3 levels up from this file)
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        data_root = os.path.join(project_root, '.cognee_data')
        system_root = os.path.join(project_root, '.cognee_system')
        
        # Ensure directories exist
        os.makedirs(data_root, exist_ok=True)
        os.makedirs(system_root, exist_ok=True)
        
        # Set environment variables that Cognee might use
        os.environ['COGNEE_DATA_ROOT'] = data_root
        os.environ['COGNEE_SYSTEM_ROOT'] = system_root
        
        # Import and configure cognee
        import cognee
        
        # Try multiple configuration approaches
        try:
            cognee.config.data_root_directory(data_root)
            cognee.config.system_root_directory(system_root)
        except Exception as config_error:
            print(f"Config method failed: {config_error}")
            # Try alternative configuration if available
            pass
        
        print(f"Cognee configured - Data: {data_root}, System: {system_root}")
        return data_root, system_root, cognee
    except Exception as e:
        print(f"Failed to configure Cognee paths: {e}")
        import cognee
        return None, None, cognee

# Configure paths and get cognee module
DATA_ROOT, SYSTEM_ROOT, cognee = _configure_cognee_paths()

from cognee.api.v1.search import SearchType
from openai import OpenAI

logger = logging.getLogger(__name__)

class CogneeService:
    """Service class for Cognee RAG operations"""
    
    def _configure_cognee(self):
        """Configure Cognee with environment settings"""
        try:
            # Store paths for reference (already configured at module level)
            self._data_root = DATA_ROOT
            self._system_root = SYSTEM_ROOT
            
            # Set default providers if not configured in environment
            # These will use the defaults (SQLite, NetworkX, LanceDB) if no env vars are set
            if not os.getenv('GRAPH_DATABASE_PROVIDER'):
                cognee.config.set_graph_db_config({
                    "graph_database_provider": "networkx"
                })
            
            if not os.getenv('VECTOR_DB_PROVIDER'):
                cognee.config.set_vector_db_config({
                    "vector_db_provider": "lancedb"
                })
            
            if not os.getenv('DB_PROVIDER'):
                cognee.config.set_relational_db_config({
                    "db_provider": "sqlite",
                    "db_name": "cognee_db"
                })
            
            self.is_configured = True
            logger.info("Cognee service configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure Cognee: {str(e)}")
            self.is_configured = False
    
    def _configure_openai(self):
        """Configure OpenAI client for validation"""
        try:
            api_key = os.getenv('AGENT_LLM_API_KEY')
            base_url = os.getenv('AGENT_BASE_URL')
            if api_key:
                self._openai_client = OpenAI(api_key=api_key, base_url=base_url)
                logger.info("OpenAI client configured for insight validation")
            else:
                logger.warning("No OpenAI API key found - insight validation disabled")
        except Exception as e:
            logger.error(f"Failed to configure OpenAI: {str(e)}")
            self._openai_client = None
    
    def __init__(self):
        """Initialize CogneeService with configuration"""
        self.is_configured = False
        self._search_cache = {}
        self._openai_client = None
        self._document_registry = {}  # Track stored documents
        self._registry_file = None
        self._configure_cognee()
        self._configure_openai()
        self._load_document_registry()
    
    def _load_document_registry(self):
        """Load document registry from persistent storage"""
        try:
            if self._data_root:
                self._registry_file = os.path.join(self._data_root, 'document_registry.pkl')
                if os.path.exists(self._registry_file):
                    import pickle
                    with open(self._registry_file, 'rb') as f:
                        self._document_registry = pickle.load(f)
                    logger.info(f"Loaded document registry with {len(self._document_registry)} entries")
                else:
                    self._document_registry = {}
            else:
                logger.warning("No data root configured - registry will not persist")
                self._document_registry = {}
        except Exception as e:
            logger.error(f"Failed to load document registry: {str(e)}")
            self._document_registry = {}
    
    def _save_document_registry(self):
        """Save document registry to persistent storage"""
        try:
            if self._registry_file:
                os.makedirs(os.path.dirname(self._registry_file), exist_ok=True)
                import pickle
                with open(self._registry_file, 'wb') as f:
                    pickle.dump(self._document_registry, f)
                logger.info(f"Saved document registry with {len(self._document_registry)} entries")
        except Exception as e:
            logger.error(f"Failed to save document registry: {str(e)}")
    
    def _create_document_fingerprint(self, content: str, metadata: Dict[str, Any]) -> str:
        """Create a unique fingerprint for a document based on content and metadata"""
        # Create a comprehensive fingerprint
        fingerprint_data = {
            'content_hash': hashlib.sha256(content.encode('utf-8')).hexdigest(),
            'company_name': metadata.get('company_name', '').lower(),
            'form_type': metadata.get('form_type', '').lower(),
            'filing_date': metadata.get('filing_date', ''),
            'accession_number': metadata.get('accession_number', ''),
        }
        
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the document registry"""
        try:
            stats = {
                'total_documents': len(self._document_registry),
                'companies': set(),
                'form_types': set(),
                'date_range': {'earliest': None, 'latest': None},
                'storage_dates': [],
                'documents_with_summaries': 0
            }
            
            for doc_info in self._document_registry.values():
                metadata = doc_info['metadata']
                stats['companies'].add(metadata.get('company_name', 'Unknown'))
                stats['form_types'].add(metadata.get('form_type', 'Unknown'))
                
                # Count documents with summaries
                if 'summary' in doc_info:
                    stats['documents_with_summaries'] += 1
                
                filing_date = metadata.get('filing_date')
                if filing_date:
                    if not stats['date_range']['earliest'] or filing_date < stats['date_range']['earliest']:
                        stats['date_range']['earliest'] = filing_date
                    if not stats['date_range']['latest'] or filing_date > stats['date_range']['latest']:
                        stats['date_range']['latest'] = filing_date
                
                stored_at = doc_info.get('stored_at')
                if stored_at:
                    stats['storage_dates'].append(stored_at[:10])  # Just the date part
            
            # Convert sets to lists for JSON serialization
            stats['companies'] = list(stats['companies'])
            stats['form_types'] = list(stats['form_types'])
            stats['storage_dates'] = list(set(stats['storage_dates']))  # Unique dates
            
            return stats
            
        except Exception as e:
            return {'error': str(e), 'total_documents': 0}
    
    def get_document_summaries(self, company_name: str = None, form_type: str = None) -> List[Dict[str, Any]]:
        """Get document summaries for agent query planning"""
        try:
            summaries = []
            
            for fingerprint, doc_info in self._document_registry.items():
                metadata = doc_info['metadata']
                
                # Filter by company if specified (allow partial matches)
                if company_name:
                    stored_company = metadata.get('company_name', '').lower()
                    filter_company = company_name.lower()
                    # Allow partial matches - filter passes if either name contains the other
                    if not (filter_company in stored_company or stored_company in filter_company):
                        continue
                    
                # Filter by form type if specified  
                if form_type and metadata.get('form_type', '').lower() != form_type.lower():
                    continue
                
                summary_info = {
                    'fingerprint': fingerprint[:8],  # Short ID for reference
                    'company_name': metadata.get('company_name'),
                    'form_type': metadata.get('form_type'),
                    'filing_date': metadata.get('filing_date'),
                    'ticker': metadata.get('ticker'),
                    'summary': doc_info.get('summary', {}),
                    'content_length': doc_info.get('content_length', 0),
                    'stored_at': doc_info.get('stored_at')
                }
                
                summaries.append(summary_info)
            
            # Sort by filing date (newest first)
            summaries.sort(key=lambda x: x.get('filing_date', ''), reverse=True)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error getting document summaries: {str(e)}")
            return []
    
    def get_summary_based_query_suggestions(self, investment_query: str) -> List[str]:
        """Generate specific Cognee queries based on available document summaries"""
        try:
            # Get all summaries
            summaries = self.get_document_summaries()
            
            if not summaries:
                return ["No documents available for analysis"]
            
            query_suggestions = []
            
            # Analyze the investment query to suggest specific document-based queries
            query_lower = investment_query.lower()
            
            for summary_info in summaries[:5]:  # Limit to top 5 most recent
                company = summary_info['company_name']
                form_type = summary_info['form_type']
                summary = summary_info.get('summary', {})
                
                # Generate targeted queries based on summary content
                if 'revenue' in query_lower or 'financial' in query_lower:
                    if summary.get('financial_highlights'):
                        query_suggestions.append(f"What are the key financial metrics for {company} from their latest {form_type}?")
                
                if 'risk' in query_lower:
                    if summary.get('risk_factors'):
                        query_suggestions.append(f"What are the main risk factors for {company} mentioned in their {form_type}?")
                
                if 'growth' in query_lower or 'opportunity' in query_lower:
                    if summary.get('investment_insights'):
                        query_suggestions.append(f"What growth opportunities does {company} highlight in their {form_type}?")
                
                # General company analysis query
                query_suggestions.append(f"Provide investment analysis for {company} based on their {form_type} filing")
            
            # Remove duplicates and return unique suggestions
            return list(set(query_suggestions))
            
        except Exception as e:
            logger.error(f"Error generating query suggestions: {str(e)}")
            return ["Error generating query suggestions"]
    
    def get_agent_context_with_summaries(self, query: str, agent_type: str = "general") -> Dict[str, Any]:
        """
        Enhanced context retrieval for agents using document summaries for better targeting
        
        This method demonstrates how agents can use summaries to:
        1. Identify relevant documents before deep search
        2. Craft more precise Cognee queries
        3. Understand document scope and content
        
        Args:
            query: User's investment query
            agent_type: Type of agent ("research", "strategy", "risk", "general")
        
        Returns:
            Enhanced context with summaries and targeted search results
        """
        try:
            # Step 1: Get document summaries to understand available content
            summaries = self.get_document_summaries()
            
            # Step 2: Analyze summaries to identify most relevant documents
            relevant_docs = self._identify_relevant_documents(query, summaries, agent_type)
            
            # Step 3: Generate targeted queries based on summaries and agent type
            targeted_queries = self._generate_agent_queries(query, relevant_docs, agent_type)
            
            # Step 4: Execute searches with targeted queries
            search_results = []
            for targeted_query in targeted_queries:
                results = self.search_context(targeted_query, "graph")
                search_results.extend(results)
            
            # Step 5: Combine everything for agent consumption
            enhanced_context = {
                'original_query': query,
                'agent_type': agent_type,
                'available_documents': len(summaries),
                'relevant_documents': relevant_docs,
                'targeted_queries_used': targeted_queries,
                'search_results': search_results,
                'document_summaries': summaries[:3],  # Top 3 most recent for context
                'retrieval_strategy': 'summary-enhanced',
                'timestamp': datetime.now().isoformat()
            }
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Error getting agent context with summaries: {str(e)}")
            return {
                'original_query': query,
                'agent_type': agent_type,
                'error': str(e),
                'search_results': [],
                'fallback_used': True
            }
    
    def _identify_relevant_documents(self, query: str, summaries: List[Dict], agent_type: str) -> List[Dict]:
        """Identify most relevant documents based on summaries and agent focus"""
        query_lower = query.lower()
        relevant_docs = []
        
        for summary_info in summaries:
            relevance_score = 0
            summary = summary_info.get('summary', {})
            
            # Check relevance based on agent type and query content
            if agent_type == "research" or agent_type == "general":
                # Research agents care about financial highlights and business insights
                financial_highlights = summary.get('financial_highlights', '').lower()
                if any(term in financial_highlights for term in ['revenue', 'earnings', 'growth', 'performance']):
                    relevance_score += 2
                if any(term in query_lower for term in ['financial', 'earnings', 'revenue', 'profit']):
                    relevance_score += 1
            
            if agent_type == "strategy" or agent_type == "general":
                # Strategy agents focus on investment insights and opportunities
                investment_insights = summary.get('investment_insights', '').lower()
                if any(term in investment_insights for term in ['growth', 'opportunity', 'market', 'competitive']):
                    relevance_score += 2
                if any(term in query_lower for term in ['strategy', 'investment', 'opportunity', 'growth']):
                    relevance_score += 1
            
            if agent_type == "risk" or agent_type == "general":
                # Risk agents focus on risk factors and challenges
                risk_factors = summary.get('risk_factors', '').lower()
                if any(term in risk_factors for term in ['risk', 'challenge', 'uncertainty', 'competition']):
                    relevance_score += 2
                if any(term in query_lower for term in ['risk', 'challenge', 'threat', 'uncertainty']):
                    relevance_score += 1
            
            # Company name matching
            company_name = summary_info.get('company_name', '').lower()
            if company_name and company_name in query_lower:
                relevance_score += 3
            
            # Add to relevant docs if above threshold
            if relevance_score > 0:
                summary_info['relevance_score'] = relevance_score
                relevant_docs.append(summary_info)
        
        # Sort by relevance score and return top 5
        relevant_docs.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return relevant_docs[:5]
    
    def _generate_agent_queries(self, original_query: str, relevant_docs: List[Dict], agent_type: str) -> List[str]:
        """Generate targeted Cognee queries based on document summaries and agent type"""
        queries = []
        
        if not relevant_docs:
            # Fallback to general query if no relevant docs found
            return [f"Provide {agent_type} analysis for: {original_query}"]
        
        for doc in relevant_docs[:3]:  # Top 3 most relevant
            company = doc.get('company_name')
            form_type = doc.get('form_type')
            summary = doc.get('summary', {})
            
            if agent_type == "research":
                if summary.get('financial_highlights'):
                    queries.append(f"What are the detailed financial metrics and performance indicators for {company} from their {form_type}?")
                queries.append(f"Provide comprehensive business analysis of {company} based on their {form_type} filing")
                
            elif agent_type == "strategy":
                if summary.get('investment_insights'):
                    queries.append(f"What investment opportunities and strategic advantages does {company} present in their {form_type}?")
                queries.append(f"Analyze the investment potential and strategic positioning of {company} from their {form_type}")
                
            elif agent_type == "risk":
                if summary.get('risk_factors'):
                    queries.append(f"What are the specific risk factors and potential threats for {company} mentioned in their {form_type}?")
                queries.append(f"Assess the investment risks and challenges for {company} based on their {form_type} filing")
                
            else:  # general
                queries.append(f"Provide comprehensive investment analysis for {company} covering financial performance, opportunities, and risks from their {form_type}")
        
        # Remove duplicates
        return list(set(queries))
    
    # Example usage method for demonstration
    def demonstrate_summary_benefits(self, query: str) -> Dict[str, Any]:
        """
        Demonstrate the difference between summary-enhanced vs basic retrieval
        This shows the value of implementing document summaries
        """
        try:
            # Method 1: Basic retrieval (current approach without summaries)
            basic_results = self.search_context(query, "graph")
            
            # Method 2: Summary-enhanced retrieval (new approach)
            enhanced_context = self.get_agent_context_with_summaries(query, "general")
            
            # Compare the approaches
            comparison = {
                'query': query,
                'basic_approach': {
                    'method': 'Direct query to Cognee',
                    'results_count': len(basic_results),
                    'results': basic_results[:2],  # First 2 results
                    'targeted': False
                },
                'enhanced_approach': {
                    'method': 'Summary-guided targeted queries',
                    'relevant_documents_identified': len(enhanced_context.get('relevant_documents', [])),
                    'targeted_queries_generated': len(enhanced_context.get('targeted_queries_used', [])),
                    'results_count': len(enhanced_context.get('search_results', [])),
                    'results': enhanced_context.get('search_results', [])[:2],  # First 2 results
                    'targeted': True,
                    'context_richness': 'High - includes document summaries and targeted analysis'
                },
                'benefits_demonstrated': [
                    "Agents can identify relevant documents before searching",
                    "More targeted queries lead to better retrieval accuracy", 
                    "Document summaries provide context for query planning",
                    "Reduced noise from irrelevant document sections",
                    "Better understanding of available information scope"
                ]
            }
            
            return comparison
            
        except Exception as e:
            return {
                'query': query,
                'error': str(e),
                'demonstration_failed': True
            }
    
    def demonstrate_parallel_processing(self, query: str) -> Dict[str, Any]:
        """
        Demonstrate how the new parallel processing works:
        1. Summary generation (agent metadata)
        2. RAG storage (raw documents)
        3. Agent workflow using summaries before RAG queries
        """
        try:
            # Step 1: Show available summaries (agent metadata)
            summaries = self.get_document_summaries()
            
            # Step 2: Agent reads summaries to understand available content
            agent_planning = []
            for summary_info in summaries[:3]:
                company = summary_info.get('company_name')
                form_type = summary_info.get('form_type')
                summary = summary_info.get('summary', {})
                
                # Agent analyzes summary to plan queries
                planning_info = {
                    'document': f"{company} {form_type}",
                    'summary_insights': {
                        'executive_summary': summary.get('executive_summary', '')[:100] + '...',
                        'has_financial_data': bool(summary.get('financial_highlights')),
                        'has_risk_factors': bool(summary.get('risk_factors')),
                        'has_investment_insights': bool(summary.get('investment_insights'))
                    },
                    'recommended_queries': []
                }
                
                # Based on summary, suggest specific RAG queries
                if 'revenue' in query.lower() and summary.get('financial_highlights'):
                    planning_info['recommended_queries'].append(f"What are the specific revenue figures for {company}?")
                
                if 'risk' in query.lower() and summary.get('risk_factors'):
                    planning_info['recommended_queries'].append(f"What are the detailed risk factors for {company}?")
                
                agent_planning.append(planning_info)
            
            # Step 3: Execute targeted RAG queries (on raw documents)
            rag_results = []
            for plan in agent_planning:
                for recommended_query in plan['recommended_queries']:
                    results = self.search_context(recommended_query, "graph")
                    rag_results.append({
                        'query': recommended_query,
                        'results_count': len(results),
                        'sample_result': results[0] if results else 'No results'
                    })
            
            return {
                'demonstration': 'Parallel Processing with Summary-Guided RAG',
                'workflow': [
                    '1. Documents processed in parallel: Summary + RAG storage',
                    '2. Agent reads summaries (metadata) to understand content',
                    '3. Agent crafts targeted queries based on summaries',
                    '4. RAG search executes on raw documents (no summary contamination)',
                    '5. Agent gets precise results from clean RAG'
                ],
                'benefits': [
                    'Clean RAG storage (no summary contamination)',
                    'Fast parallel processing',
                    'Summary as agent planning tool',
                    'Targeted queries = better retrieval accuracy'
                ],
                'agent_planning': agent_planning,
                'rag_results': rag_results,
                'processing_separation': {
                    'summaries': 'Stored as agent metadata only',
                    'rag_content': 'Raw documents with basic metadata only',
                    'query_strategy': 'Summary-informed, RAG-executed'
                }
            }
            
        except Exception as e:
            return {
                'demonstration': 'Failed',
                'error': str(e)
            }
    
    def _create_cache_key(self, query: str, search_type: str) -> str:
        """Create a cache key for search results"""
        key_data = f"{query}:{search_type}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _run_async(self, coro):
        """Helper to run async functions in sync context"""
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to run in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(coro)
    
    async def _generate_document_summary(self, content: str, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Generate structured summary of document for better agent retrieval - processes ENTIRE document"""
        if not self._openai_client:
            logger.warning("OpenAI client not configured - using basic summary")
            return self._generate_basic_summary(content, metadata)
        
        try:
            # Process the ENTIRE document without truncation as requested
            logger.info(f"Generating summary for complete document ({len(content):,} characters) - no truncation applied")
            
            company_name = metadata.get('company_name', 'Unknown Company')
            form_type = metadata.get('form_type', 'Unknown Form')
            
            summary_prompt = f"""You are an expert financial analyst. Create a structured summary of this {form_type} filing for {company_name} that will help AI agents make better investment decisions.

COMPLETE DOCUMENT CONTENT:
{content}

Please provide a JSON response with these exact keys:

1. "executive_summary": A 2-3 sentence overview of the document's main purpose and key points
2. "financial_highlights": Key financial metrics, performance indicators, and numerical data (3-4 bullet points)
3. "investment_insights": Investment-relevant information like growth opportunities, market position, competitive advantages (3-4 bullet points)  
4. "risk_factors": Major risks, challenges, or concerns mentioned in the document (3-4 bullet points)

Format as valid JSON with these keys. Keep each section concise but informative for AI agents to understand what queries this document can answer.
"""

            response = self._openai_client.chat.completions.create(
                model="gemini-2.5-flash",  # Efficient model that can handle large documents
                messages=[
                    {"role": "system", "content": "You are a financial document summarization expert. Process the complete document and always respond with valid JSON containing the requested summary structure."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3,  # Some creativity for varied summaries
                # No max_tokens limit - let the model generate complete summaries
            )
            
            summary_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                if summary_text.startswith('```json'):
                    summary_text = summary_text.split('```json')[1].split('```')[0]
                elif summary_text.startswith('```'):
                    summary_text = summary_text.split('```')[1].split('```')[0]
                
                summary_data = json.loads(summary_text)
                
                # Validate required keys
                required_keys = ['executive_summary', 'financial_highlights', 'investment_insights', 'risk_factors']
                for key in required_keys:
                    if key not in summary_data:
                        summary_data[key] = f"No {key.replace('_', ' ')} available"
                
                logger.info(f"Generated AI summary for {company_name} {form_type}")
                return summary_data
                
            except json.JSONDecodeError:
                logger.error("Failed to parse summary JSON, using basic summary")
                return self._generate_basic_summary(content, metadata)
                
        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}, using basic summary")
            return self._generate_basic_summary(content, metadata)
    
    def _generate_basic_summary(self, content: str, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Generate basic summary when AI summarization is not available"""
        company_name = metadata.get('company_name', 'Unknown Company')
        form_type = metadata.get('form_type', 'Unknown Form')
        filing_date = metadata.get('filing_date', 'Unknown Date')
        
        # Extract some basic insights from content
        content_lower = content.lower()
        
        # Basic financial keywords
        financial_terms = ['revenue', 'net income', 'earnings', 'cash flow', 'assets', 'debt', 'profit', 'loss']
        found_terms = [term for term in financial_terms if term in content_lower]
        
        # Basic risk keywords  
        risk_terms = ['risk', 'uncertainty', 'challenge', 'competition', 'regulatory', 'litigation']
        found_risks = [term for term in risk_terms if term in content_lower]
        
        return {
            'executive_summary': f"This is a {form_type} filing for {company_name} dated {filing_date}. The document contains standard regulatory disclosures and business information.",
            'financial_highlights': f"Document contains references to: {', '.join(found_terms[:4]) if found_terms else 'general financial information'}",
            'investment_insights': f"This {form_type} filing provides regulatory disclosures and business updates that may be relevant for investment analysis.",
            'risk_factors': f"Document mentions: {', '.join(found_risks[:4]) if found_risks else 'standard business risks'}"
        }
    
    async def _add_document_async(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add document to Cognee RAG (async version) - parallel summary generation and RAG storage"""
        try:
            # Create two parallel tasks:
            # 1. Generate summary from complete document (for agent metadata)
            # 2. Store raw document in Cognee RAG (for retrieval)
            
            import asyncio
            
            # Task 1: Generate summary (agent metadata only)
            summary_task = asyncio.create_task(
                self._generate_document_summary(content, metadata)
            )
            
            # Task 2: Prepare and store document in RAG (without summary)
            document_text = f"""
            Document Metadata:
            - Company: {metadata.get('company_name', 'Unknown')}
            - Form Type: {metadata.get('form_type', 'Unknown')}
            - Filing Date: {metadata.get('filing_date', 'Unknown')}
            - Ticker: {metadata.get('ticker', 'Unknown')}
            - Accession Number: {metadata.get('accession_number', 'Unknown')}
            
            Document Content:
            {content}
            """
            
            # Store document in Cognee RAG (parallel with summary generation)
            rag_storage_task = asyncio.create_task(
                self._store_document_in_rag(document_text)
            )
            
            # Wait for both tasks to complete in parallel
            summary, rag_success = await asyncio.gather(summary_task, rag_storage_task)
            
            if rag_success:
                # Process the document to build knowledge graph
                await cognee.cognify()
                
                logger.info(f"Successfully processed document {metadata.get('accession_number')} - RAG storage and summary generation completed in parallel")
                return {
                    'success': True,
                    'summary': summary,  # Summary as separate metadata for agents
                    'rag_stored': True,
                    'processing_method': 'parallel'
                }
            else:
                logger.error(f"Failed to store document {metadata.get('accession_number')} in RAG")
                return {
                    'success': False,
                    'summary': summary,  # Summary still generated even if RAG fails
                    'rag_stored': False,
                    'error': 'RAG storage failed'
                }
            
        except Exception as e:
            logger.error(f"Failed to process document: {str(e)}")
            return {
                'success': False,
                'summary': None,
                'error': str(e)
            }
    
    async def _store_document_in_rag(self, document_text: str) -> bool:
        """Store document in Cognee RAG without summary (separate from summary generation)"""
        try:
            # Add only the raw document with basic metadata to Cognee
            await cognee.add(document_text)
            return True
        except Exception as e:
            logger.error(f"Failed to store document in RAG: {str(e)}")
            return False
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add document to Cognee RAG with registry tracking and duplicate detection"""
        if not self.is_configured:
            logger.error("Cognee service not configured properly")
            return {
                'success': False,
                'error': 'Cognee service not configured properly'
            }
        
        try:
            # Check for duplicates first
            fingerprint = self._create_document_fingerprint(content, metadata)
            
            if fingerprint in self._document_registry:
                existing_doc = self._document_registry[fingerprint]
                return {
                    'success': False,
                    'duplicate': True,
                    'reason': 'Document already exists in registry',
                    'existing_document': {
                        'company': existing_doc['metadata'].get('company_name'),
                        'form_type': existing_doc['metadata'].get('form_type'),
                        'stored_at': existing_doc.get('stored_at'),
                        'fingerprint': fingerprint
                    }
                }
            
            # Check for similar documents (same company and form type)
            for existing_fingerprint, doc_info in self._document_registry.items():
                existing_meta = doc_info['metadata']
                if (existing_meta.get('company_name', '').lower() == metadata.get('company_name', '').lower() and
                    existing_meta.get('form_type', '').lower() == metadata.get('form_type', '').lower() and
                    existing_meta.get('filing_date') == metadata.get('filing_date')):
                    
                    return {
                        'success': False,
                        'duplicate': True,
                        'reason': f'Similar document exists: {existing_meta.get("company_name")} {existing_meta.get("form_type")} from {existing_meta.get("filing_date")}',
                        'existing_document': {
                            'company': existing_meta.get('company_name'),
                            'form_type': existing_meta.get('form_type'),
                            'stored_at': doc_info.get('stored_at'),
                            'fingerprint': existing_fingerprint
                        }
                    }
            
            # Add document to Cognee (returns both success status and generated summary)
            cognee_result = self._run_async(self._add_document_async(content, metadata))
            
            if cognee_result.get('success'):
                # Use the summary generated during document processing (no double generation)
                summary = cognee_result.get('summary')
                
                # Register document in our registry with FULL content and summary
                doc_info = {
                    'fingerprint': fingerprint,
                    'metadata': metadata,
                    'summary': summary,  # Store structured summary
                    'content_length': len(content),
                    'content_preview': content[:2000],  # Store preview for similarity checks
                    'full_content': content,  # Store COMPLETE content for validation
                    'stored_at': datetime.now().isoformat(),
                    'content_hash': hashlib.sha256(content.encode('utf-8')).hexdigest()
                }
                
                self._document_registry[fingerprint] = doc_info
                self._save_document_registry()
                
                logger.info(f"Successfully registered document: {metadata.get('company_name')} {metadata.get('form_type')} ({fingerprint[:8]})")
                
                return {
                    'success': True,
                    'fingerprint': fingerprint,
                    'registered': True,
                    'content_length': len(content)
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to add document to Cognee RAG: {cognee_result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _search_context_async(self, query: str, search_type: SearchType = SearchType.GRAPH_COMPLETION) -> List[str]:
        """Search for relevant context from Cognee (async version)"""
        try:
            # Use the proper Cognee search method based on search type
            if search_type == SearchType.GRAPH_COMPLETION:
                # This returns natural language answers like the example
                results = await cognee.search(
                    query_type=search_type,
                    query_text=query
                )
            else:
                # For other search types, use the specific type
                results = await cognee.search(
                    query_type=search_type,
                    query_text=query
                )
            
            # Handle different result formats
            if isinstance(results, list):
                # Convert complex objects to readable strings
                formatted_results = []
                for result in results:
                    if isinstance(result, str):
                        formatted_results.append(result)
                    elif hasattr(result, 'text'):
                        formatted_results.append(result.text)
                    elif isinstance(result, dict) and 'text' in result:
                        formatted_results.append(result['text'])
                    else:
                        # For complex objects, try to extract meaningful content
                        result_str = str(result)
                        if len(result_str) > 500:
                            result_str = result_str[:500] + "..."
                        formatted_results.append(result_str)
                return formatted_results
            else:
                return [str(results)]
                
        except Exception as e:
            logger.error(f"Failed to search Cognee: {str(e)}")
            return []
    
    def search_context(self, query: str, search_type: str = "insights") -> List[str]:
        """Search for relevant context from Cognee with caching"""
        if not self.is_configured:
            logger.error("Cognee service not configured properly")
            return []
        
        # Create cache key
        cache_key = self._create_cache_key(query, search_type)
        
        # Check cache first
        if cache_key in self._search_cache:
            logger.info(f"Returning cached results for query: {query[:50]}...")
            return self._search_cache[cache_key]
        
        # Map string search type to SearchType enum
        search_type_map = {
            "insights": SearchType.INSIGHTS,
            "chunks": SearchType.CHUNKS,
            "graph": SearchType.GRAPH_COMPLETION,
            "completion": SearchType.GRAPH_COMPLETION,
            "summaries": SearchType.SUMMARIES,
            "natural": SearchType.GRAPH_COMPLETION  # Natural language answers
        }
        
        cognee_search_type = search_type_map.get(search_type.lower(), SearchType.GRAPH_COMPLETION)
        
        # Get results and cache them
        results = self._run_async(self._search_context_async(query, cognee_search_type))
        self._search_cache[cache_key] = results
        
        return results
    
    def detect_company_from_query(self, query: str) -> Optional[str]:
        """Detect company name from query text"""
        query_lower = query.lower()
        
        # Check against companies in our registry first
        for doc_info in self._document_registry.values():
            company_name = doc_info['metadata'].get('company_name', '')
            if company_name and company_name.lower() in query_lower:
                return company_name
        
        # Common company name patterns
        company_patterns = {
            'apple': 'Apple Inc.',
            'microsoft': 'Microsoft Corporation',
            'google': 'Alphabet Inc.',
            'amazon': 'Amazon.com Inc.',
            'tesla': 'Tesla, Inc.',
            'meta': 'Meta Platforms, Inc.',
            'nvidia': 'NVIDIA Corporation'
        }
        
        for pattern, company_name in company_patterns.items():
            if pattern in query_lower:
                return company_name
        
        return None
    
    def search_context_by_company(self, query: str, company_name: str, search_type: str = "insights") -> List[str]:
        """Search for context filtered by company"""
        if not self.is_configured:
            logger.error("Cognee service not configured properly")
            return []
        
        # Enhance query with company name for better filtering
        enhanced_query = f"{query} {company_name}"
        
        # Use regular search - Cognee should filter based on the enhanced query
        return self.search_context(enhanced_query, search_type)
    
    async def _get_document_insights_async(self, company_name: str, form_type: str = None) -> Dict[str, Any]:
        """Get insights about a specific company/document type (async version)"""
        try:
            # Build query based on parameters
            if form_type:
                query = f"What are the key insights from {company_name} {form_type} filings?"
            else:
                query = f"What are the key insights about {company_name}?"
            
            # Use GRAPH_COMPLETION for natural language insights
            completion_insights = await cognee.search(
                query_type=SearchType.GRAPH_COMPLETION,
                query_text=query
            )
            
            # Also get relationship insights
            relationship_insights = await cognee.search(
                query_type=SearchType.INSIGHTS,
                query_text=query
            )
            
            # Get relevant chunks for supporting details
            chunks = await cognee.search(
                query_type=SearchType.CHUNKS,
                query_text=query
            )
            
            # Format results
            formatted_insights = []
            if isinstance(completion_insights, list):
                formatted_insights.extend([str(result) for result in completion_insights])
            else:
                formatted_insights.append(str(completion_insights))
            
            return {
                'insights': formatted_insights,
                'relationship_insights': relationship_insights,
                'chunks': chunks,
                'query': query
            }
            
        except Exception as e:
            logger.error(f"Failed to get document insights: {str(e)}")
            return {'insights': [], 'relationship_insights': [], 'chunks': [], 'query': query}
    
    def get_document_insights(self, company_name: str, form_type: str = None) -> Dict[str, Any]:
        """Get insights about a specific company/document type"""
        if not self.is_configured:
            logger.error("Cognee service not configured properly")
            return {'insights': [], 'chunks': [], 'query': ''}
        
        return self._run_async(self._get_document_insights_async(company_name, form_type))
    
    async def _get_investment_context_async(self, query_text: str) -> Dict[str, Any]:
        """Get comprehensive context for investment analysis (async version) - optimized"""
        try:
            # Use GRAPH_COMPLETION for natural language answers about the investment query
            completion_results = await cognee.search(
                query_type=SearchType.GRAPH_COMPLETION,
                query_text=f"Provide investment analysis insights for: {query_text}"
            )
            
            # Also get specific chunks for detailed information
            chunks = await cognee.search(
                query_type=SearchType.CHUNKS,
                query_text=query_text
            )
            
            # Format completion results as insights
            insights = []
            if isinstance(completion_results, list):
                insights = [str(result) for result in completion_results]
            else:
                insights = [str(completion_results)]
            
            # Build comprehensive context
            context = {
                'insights': insights,  # Natural language insights from GRAPH_COMPLETION
                'document_chunks': chunks,  # Raw chunks for detailed analysis
                'natural_language_analysis': completion_results,  # Full completion results
                'query': query_text,
                'timestamp': datetime.now().isoformat(),
                'search_method': 'graph_completion_plus_chunks'
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get investment context: {str(e)}")
            return {
                'insights': [],
                'document_chunks': [],
                'natural_language_analysis': [],
                'query': query_text,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_investment_context(self, query_text: str) -> Dict[str, Any]:
        """Get comprehensive context for investment analysis"""
        if not self.is_configured:
            logger.error("Cognee service not configured properly")
            return {
                'insights': [],
                'document_chunks': [],
                'relationships': [],
                'query': query_text,
                'timestamp': datetime.now().isoformat()
            }
        
        return self._run_async(self._get_investment_context_async(query_text))
    
    async def _prune_data_async(self) -> bool:
        """Clear all data from Cognee (async version)"""
        try:
            # First try Cognee's prune method
            await cognee.prune.prune_data()
            
            # Also manually clear our project directories to ensure clean state
            import shutil
            if self._data_root and os.path.exists(self._data_root):
                for file in os.listdir(self._data_root):
                    file_path = os.path.join(self._data_root, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Removed data file: {file}")
            
            if self._system_root and os.path.exists(self._system_root):
                system_db_path = os.path.join(self._system_root, 'databases')
                if os.path.exists(system_db_path):
                    shutil.rmtree(system_db_path)
                    os.makedirs(system_db_path, exist_ok=True)
                    logger.info("Cleared system databases directory")
            
            # Clear registry
            self._document_registry.clear()
            
            logger.info("Successfully pruned Cognee data, cleared project directories and registry")
            return True
        except Exception as e:
            logger.error(f"Failed to prune Cognee data: {str(e)}")
            return False
    
    def prune_data(self) -> bool:
        """Clear all data from Cognee"""
        if not self.is_configured:
            logger.error("Cognee service not configured properly")
            return False
        
        return self._run_async(self._prune_data_async())
    
    def complete_reset(self) -> bool:
        """Completely reset Cognee by removing all directories and recreating them"""
        try:
            import shutil
            
            print("🧹 Performing complete Cognee reset...")
            
            # Remove data directory completely
            if self._data_root and os.path.exists(self._data_root):
                shutil.rmtree(self._data_root)
                print(f"✅ Removed data directory: {self._data_root}")
            
            # Remove system directory completely
            if self._system_root and os.path.exists(self._system_root):
                shutil.rmtree(self._system_root)
                print(f"✅ Removed system directory: {self._system_root}")
            
            # Recreate directories
            if self._data_root:
                os.makedirs(self._data_root, exist_ok=True)
                print(f"✅ Recreated data directory: {self._data_root}")
            
            if self._system_root:
                os.makedirs(self._system_root, exist_ok=True)
                print(f"✅ Recreated system directory: {self._system_root}")
            
            # Clear cache and registry
            self._search_cache.clear()
            self._document_registry.clear()
            print("✅ Cleared search cache and document registry")
            
            print("🎉 Complete reset successful!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to perform complete reset: {str(e)}")
            print(f"❌ Reset failed: {str(e)}")
            return False
    
    async def _health_check_async(self) -> Dict[str, Any]:
        """Check Cognee service health (async version)"""
        try:
            # Test basic functionality by adding a small piece of text
            test_text = "Health check test document for FinDocGPT integration"
            await cognee.add(test_text)
            await cognee.cognify()
            
            # Test natural language search (like the example)
            results = await cognee.search("Tell me about the health check")
            
            # Test specific search type
            chunk_results = await cognee.search(
                query_type=SearchType.CHUNKS,
                query_text="health check"
            )
            
            return {
                'status': 'healthy',
                'configured': self.is_configured,
                'can_add': True,
                'can_search': len(results) >= 0 if results else True,
                'can_search_chunks': len(chunk_results) >= 0 if chunk_results else True,
                'natural_language_response': str(results[0]) if results else 'No response',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Cognee health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'configured': self.is_configured,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Check Cognee service health"""
        return self._run_async(self._health_check_async())
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the Cognee service configuration"""
        return {
            'configured': self.is_configured,
            'data_root': getattr(self, '_data_root', 'Not configured'),
            'system_root': getattr(self, '_system_root', 'Not configured'),
            'cache_size': len(self._search_cache),
            'openai_validation_enabled': self._openai_client is not None,
            'providers': {
                'graph_db': os.getenv('GRAPH_DATABASE_PROVIDER', 'networkx'),
                'vector_db': os.getenv('VECTOR_DB_PROVIDER', 'lancedb'),
                'relational_db': os.getenv('DB_PROVIDER', 'sqlite')
            },
            'performance_optimizations': {
                'caching_enabled': True,
                'simplified_context_retrieval': True,
                'async_optimization': True
            },
            'document_processing': {
                'summary_generation': 'Complete document processing - no truncation',
                'summary_timing': 'Generated in parallel with RAG storage',
                'summary_purpose': 'Agent metadata only - not stored in RAG',
                'rag_storage': 'Raw document only - no summary contamination',
                'processing_method': 'Parallel tasks for optimal performance',
                'full_document_analysis': True
            }
        }
    
    def get_document_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about document processing and summarization"""
        try:
            stats = {
                'total_documents_processed': len(self._document_registry),
                'documents_with_ai_summaries': 0,
                'documents_with_basic_summaries': 0,
                'average_document_size': 0,
                'largest_document_processed': 0,
                'processing_method': 'Parallel: Summary generation + RAG storage',
                'summary_storage': 'Agent metadata only (not in RAG)',
                'rag_content': 'Raw documents only'
            }
            
            total_size = 0
            for doc_info in self._document_registry.values():
                doc_size = doc_info.get('content_length', 0)
                total_size += doc_size
                
                if doc_size > stats['largest_document_processed']:
                    stats['largest_document_processed'] = doc_size
                
                # Check if summary exists and determine type
                summary = doc_info.get('summary', {})
                if summary:
                    # Basic summaries have simple patterns, AI summaries are more detailed
                    exec_summary = summary.get('executive_summary', '')
                    if 'standard regulatory disclosures' in exec_summary:
                        stats['documents_with_basic_summaries'] += 1
                    else:
                        stats['documents_with_ai_summaries'] += 1
            
            if stats['total_documents_processed'] > 0:
                stats['average_document_size'] = int(total_size / stats['total_documents_processed'])
            
            return stats
            
        except Exception as e:
            return {
                'error': str(e),
                'total_documents_processed': 0
            }
    
    def validate_insight_with_llm(self, insight: str, query: str, raw_document_content: str, document_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate a RAG-generated insight against the raw document content using OpenAI LLM
        
        Args:
            insight: The insight generated by Cognee RAG
            query: The original user query
            raw_document_content: The full raw text of the document
            document_metadata: Optional metadata about the document
            
        Returns:
            Dict containing validation results including accuracy score, explanation, and corrections
        """
        if not self._openai_client:
            return {
                'validation_available': False,
                'error': 'OpenAI client not configured - validation disabled'
            }
        
        try:
            # Truncate document if too long (OpenAI has token limits)
            max_doc_length = 15000  # Conservative limit for GPT-4
            if len(raw_document_content) > max_doc_length:
                truncated_content = raw_document_content[:max_doc_length] + "\n\n[Document truncated for validation...]"
                logger.info(f"Document truncated from {len(raw_document_content)} to {len(truncated_content)} characters for validation")
            else:
                truncated_content = raw_document_content
            
            # Create validation prompt
            validation_prompt = f"""You are an expert financial analyst tasked with validating AI-generated insights against source documents.

USER QUERY: "{query}"

RAG-GENERATED INSIGHT:
{insight}

ORIGINAL DOCUMENT CONTENT:
{truncated_content}

Please evaluate the RAG-generated insight and provide:

1. ACCURACY SCORE (0-10): How accurate is the insight based on the document?
2. CORRECTNESS: Is the insight factually correct? (Yes/No/Partially)
3. COMPLETENESS: Does the insight adequately address the user's query? (Complete/Partial/Incomplete)
4. SPECIFIC ISSUES: List any factual errors, omissions, or misinterpretations
5. SUPPORTING EVIDENCE: Quote specific parts of the document that support or contradict the insight
6. IMPROVED INSIGHT: If needed, provide a corrected or enhanced version of the insight

Format your response as JSON with these exact keys:
- accuracy_score (integer 0-10)
- correctness (string: "Yes", "No", or "Partially")
- completeness (string: "Complete", "Partial", or "Incomplete")  
- issues (array of strings)
- supporting_evidence (array of strings)
- improved_insight (string, only if corrections needed)
- explanation (string: brief summary of your evaluation)
"""

            # Call OpenAI API
            response = self._openai_client.chat.completions.create(
                model="gemini-2.5-flash",  # Use cost-effective model for validation
                messages=[
                    {"role": "system", "content": "You are a precise financial document analyst. Always respond with valid JSON."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent validation
                # max_tokens=1500
            )
            
            # Parse the response
            validation_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON from response
            try:
                # Remove markdown code blocks if present
                if validation_text.startswith('```json'):
                    validation_text = validation_text.split('```json')[1].split('```')[0]
                elif validation_text.startswith('```'):
                    validation_text = validation_text.split('```')[1].split('```')[0]
                
                validation_result = json.loads(validation_text)
                
                # Add metadata
                validation_result.update({
                    'validation_available': True,
                    'query': query,
                    'original_insight': insight,
                    'document_truncated': len(raw_document_content) > max_doc_length,
                    'document_length': len(raw_document_content),
                    'validation_timestamp': datetime.now().isoformat()
                })
                
                if document_metadata:
                    validation_result['document_metadata'] = document_metadata
                
                logger.info(f"Insight validation completed - Accuracy: {validation_result.get('accuracy_score', 'N/A')}/10")
                return validation_result
                
            except json.JSONDecodeError:
                logger.error("Failed to parse validation response as JSON")
                return {
                    'validation_available': True,
                    'error': 'Failed to parse validation response',
                    'raw_response': validation_text,
                    'query': query,
                    'original_insight': insight
                }
        
        except Exception as e:
            logger.error(f"Error during insight validation: {str(e)}")
            return {
                'validation_available': False,
                'error': str(e),
                'query': query,
                'original_insight': insight
            }
    
    def get_document_content_for_validation(self, document_metadata: Dict[str, Any]) -> str:
        """
        Retrieve the raw document content for validation purposes
        This is a helper method to get the original document content
        """
        # For now, return a placeholder - in production this would fetch from storage
        # The interactive script will pass the content directly
        return "Document content not available - please pass content directly to validation method"
