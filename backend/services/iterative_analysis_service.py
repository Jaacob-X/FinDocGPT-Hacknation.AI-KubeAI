import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from openai import OpenAI
import os

from .cognee_service import CogneeService
from .gemini_validation_service import GeminiValidationService

logger = logging.getLogger(__name__)

class IterativeAnalysisService:
    """
    Iterative Financial Analysis Service
    
    Architecture:
    1. Gather all document summaries with metadata
    2. Generate comprehensive initial analysis
    3. Question the analysis for completeness
    4. Generate targeted RAG queries based on gaps
    5. Refine analysis with RAG results
    6. Loop until analysis is complete
    """
    
    def __init__(self):
        self.cognee_service = CogneeService()
        self.gemini_validation_service = GeminiValidationService()
        self._configure_openai()
        self.max_iterations = 10  # Prevent infinite loops
        
    def _configure_openai(self):
        """Configure OpenAI client for analysis"""
        try:
            api_key = os.getenv('AGENT_LLM_API_KEY')
            base_url = os.getenv('AGENT_BASE_URL')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key, base_url=base_url)
                logger.info("OpenAI client configured for iterative analysis")
            else:
                logger.error("No OpenAI API key found - analysis service disabled")
                self.openai_client = None
        except Exception as e:
            logger.error(f"Failed to configure OpenAI: {str(e)}")
            self.openai_client = None
    
    def create_rag_query_tool(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        Create a RAG query tool that can be called by LLMs
        
        Args:
            query: The specific question to query the RAG database
            context: Additional context to help focus the search
            
        Returns:
            Dict containing the tool definition and execution function
        """
        def execute_rag_query(question: str, search_type: str = "graph") -> Dict[str, Any]:
            """Execute a RAG query and return structured results with Gemini validation"""
            try:
                # Get context from RAG
                results = self.cognee_service.search_context(question, search_type)

                # Get document summaries for context
                summaries = self.cognee_service.get_document_summaries()

                # Find relevant documents
                relevant_docs = []
                for summary in summaries:
                    # Simple relevance check - could be enhanced
                    company = summary.get('company_name', '').lower()
                    if any(term in question.lower() for term in [company] if company):
                        relevant_docs.append({
                            'company': summary.get('company_name'),
                            'form_type': summary.get('form_type'),
                            'filing_date': summary.get('filing_date'),
                            'summary': summary.get('summary', {})
                        })

                # Validate RAG response with Gemini and enhance if needed
                validation_result = self.gemini_validation_service.validate_and_enhance_rag_response(
                    question, results
                )

                # Get the final response to use (either RAG or Gemini-enhanced)
                final_results = self.gemini_validation_service.get_final_response(validation_result)

                return {
                    'query': question,
                    'search_type': search_type,
                    'results': final_results,
                    'original_rag_results': results,
                    'validation_result': validation_result,
                    'relevant_documents': relevant_docs,
                    'result_count': len(final_results),
                    'original_result_count': len(results),
                    'source': validation_result.get('final_source', 'rag'),
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error executing RAG query: {str(e)}")
                return {
                    'query': question,
                    'error': str(e),
                    'results': [],
                    'relevant_documents': []
                }
        
        # Tool definition for LLM
        tool_definition = {
            "type": "function",
            "function": {
                "name": "query_rag_database",
                "description": "Query the RAG database for specific financial information about companies and documents. Use this when you need detailed information that might not be in the document summaries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The specific question to query the RAG database. Be specific and include company names when relevant."
                        },
                        "search_type": {
                            "type": "string",
                            "enum": ["graph", "chunks", "insights", "natural"],
                            "default": "graph",
                            "description": "Type of search to perform. 'graph' for comprehensive analysis, 'chunks' for specific details, 'insights' for relationships, 'natural' for conversational responses."
                        }
                    },
                    "required": ["question"]
                }
            }
        }
        
        return {
            "tool_definition": tool_definition,
            "execute_function": execute_rag_query
        }
    
    def generate_initial_analysis(self, query: str, document_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive initial analysis based on document summaries
        
        Args:
            query: User's investment query
            document_summaries: List of document summaries with metadata
            
        Returns:
            Initial analysis with structured insights
        """
        if not self.openai_client:
            return {"error": "OpenAI client not configured"}
        
        try:
            # Prepare document context
            documents_context = self._format_documents_for_analysis(document_summaries)
            
            analysis_prompt = f"""You are an expert financial analyst. Based on the provided document summaries, generate a comprehensive investment analysis for the following query:

INVESTMENT QUERY: "{query}"

AVAILABLE DOCUMENTS WITH SUMMARIES:
{documents_context}

Please provide a comprehensive analysis in JSON format with these sections:

1. "executive_summary": 2-3 sentence overview of your investment recommendation
2. "financial_analysis": Analysis of financial performance, metrics, and trends
3. "investment_opportunities": Growth opportunities and competitive advantages
4. "risk_assessment": Key risks and potential challenges
5. "market_position": Company's position in the market and competitive landscape
6. "valuation_insights": Insights on company valuation and pricing
7. "recommendation": Clear investment recommendation (Buy/Hold/Sell) with rationale
8. "confidence_level": Your confidence in this analysis (High/Medium/Low)
9. "data_gaps": Areas where you need more specific information to improve the analysis

Focus on actionable insights for investment decisions. Be specific about what documents inform each conclusion.
"""

            response = self.openai_client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are a senior financial analyst with expertise in investment research. Always provide detailed, evidence-based analysis in valid JSON format."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                if analysis_text.startswith('```json'):
                    analysis_text = analysis_text.split('```json')[1].split('```')[0]
                elif analysis_text.startswith('```'):
                    analysis_text = analysis_text.split('```')[1].split('```')[0]
                
                analysis_data = json.loads(analysis_text)
                
                # Add metadata
                analysis_data.update({
                    'query': query,
                    'documents_analyzed': len(document_summaries),
                    'analysis_type': 'initial_comprehensive',
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.info(f"Generated initial analysis for query: {query[:50]}...")
                return analysis_data
                
            except json.JSONDecodeError:
                logger.error("Failed to parse initial analysis JSON")
                return {
                    'error': 'Failed to parse analysis response',
                    'raw_response': analysis_text,
                    'query': query
                }
                
        except Exception as e:
            logger.error(f"Error generating initial analysis: {str(e)}")
            return {
                'error': str(e),
                'query': query
            }
    
    def question_analysis_completeness(self, analysis: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Question the analysis for completeness and identify gaps
        
        Args:
            analysis: The initial analysis to evaluate
            query: Original user query
            
        Returns:
            Evaluation results with specific questions and gaps identified
        """
        if not self.openai_client:
            return {"error": "OpenAI client not configured"}
        
        try:
            questioning_prompt = f"""You are a senior investment committee member reviewing an analyst's report. Your job is to identify gaps, weaknesses, and areas that need more detailed investigation, while recognizing that practical investment decisions often need to be made with reasonable information rather than perfect completeness.

ORIGINAL INVESTMENT QUERY: "{query}"

ANALYST'S REPORT:
{json.dumps(analysis, indent=2)}

Please evaluate this analysis and provide feedback in JSON format with these sections:

1. "overall_assessment": Your overall assessment of the analysis quality (Excellent/Good/Fair/Poor)
2. "completeness_score": Score from 1-10 on how complete the analysis is (consider that 7+ indicates sufficient completeness for practical decision-making)
3. "specific_questions": List of specific questions that need to be answered to improve the analysis
4. "missing_areas": Areas of analysis that are missing or insufficient
5. "data_needs": Specific data points or information needed for better analysis
6. "methodology_concerns": Any concerns about the analytical approach
7. "actionability": How actionable is the current recommendation (High/Medium/Low)
8. "next_steps": Specific next steps to improve the analysis
9. "is_analysis_complete": Boolean - true if analysis is sufficient for practical investment decision-making, false if needs more work

Be thorough but balanced in your evaluation, recognizing that investment decisions often require working with available information rather than waiting for perfect completeness.
"""

            response = self.openai_client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are an experienced investment committee chair who balances thoroughness with practical decision-making needs, recognizing that good investment decisions can be made with reasonable analysis rather than perfect completeness."},
                    {"role": "user", "content": questioning_prompt}
                ],
                temperature=0.3  # Slightly higher temperature for more balanced evaluation
            )
            
            evaluation_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                if evaluation_text.startswith('```json'):
                    evaluation_text = evaluation_text.split('```json')[1].split('```')[0]
                elif evaluation_text.startswith('```'):
                    evaluation_text = evaluation_text.split('```')[1].split('```')[0]
                
                evaluation_data = json.loads(evaluation_text)
                
                # Add metadata
                evaluation_data.update({
                    'query': query,
                    'evaluation_timestamp': datetime.now().isoformat(),
                    'analysis_evaluated': True
                })
                
                logger.info(f"Completed analysis evaluation - Completeness: {evaluation_data.get('completeness_score', 'N/A')}/10")
                return evaluation_data
                
            except json.JSONDecodeError:
                logger.error("Failed to parse evaluation JSON")
                return {
                    'error': 'Failed to parse evaluation response',
                    'raw_response': evaluation_text,
                    'query': query
                }
                
        except Exception as e:
            logger.error(f"Error evaluating analysis completeness: {str(e)}")
            return {
                'error': str(e),
                'query': query
            }
    
    def generate_targeted_rag_queries(self, evaluation: Dict[str, Any], document_summaries: List[Dict[str, Any]]) -> List[str]:
        """
        Generate specific RAG queries based on the evaluation gaps
        
        Args:
            evaluation: Results from analysis evaluation
            document_summaries: Available document summaries for context
            
        Returns:
            List of targeted RAG queries to fill identified gaps
        """
        if not self.openai_client:
            return []
        
        try:
            # Get available document info for context
            available_docs = self._format_documents_for_analysis(document_summaries)
            
            query_generation_prompt = f"""Based on the analysis evaluation, generate specific RAG database queries to fill the identified gaps.

ANALYSIS EVALUATION:
{json.dumps(evaluation, indent=2)}

AVAILABLE DOCUMENTS:
{available_docs}

Generate 3-5 specific, targeted queries that would help address the gaps and questions identified in the evaluation. Each query should:
1. Be specific and actionable
2. Target information likely to be in the available documents
3. Address the most critical gaps first
4. Include company names and specific metrics when relevant

Provide the queries as a JSON array of strings, like:
["query 1", "query 2", "query 3"]

Focus on queries that will provide the most valuable additional insights for the investment decision.
"""

            response = self.openai_client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are an expert at crafting precise database queries to extract financial information. Generate specific, targeted queries."},
                    {"role": "user", "content": query_generation_prompt}
                ],
                temperature=0.3
            )
            
            queries_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                if queries_text.startswith('```json'):
                    queries_text = queries_text.split('```json')[1].split('```')[0]
                elif queries_text.startswith('```'):
                    queries_text = queries_text.split('```')[1].split('```')[0]
                
                queries = json.loads(queries_text)
                
                # Ensure we have a list of strings
                if isinstance(queries, list):
                    logger.info(f"Generated {len(queries)} targeted RAG queries")
                    return queries
                else:
                    logger.warning("Generated queries not in expected format")
                    return []
                
            except json.JSONDecodeError:
                logger.error("Failed to parse RAG queries JSON")
                return []
                
        except Exception as e:
            logger.error(f"Error generating RAG queries: {str(e)}")
            return []
    
    def refine_analysis_with_rag_results(self, original_analysis: Dict[str, Any], rag_results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """
        Refine the original analysis using RAG query results
        
        Args:
            original_analysis: The original analysis to refine
            rag_results: Results from RAG queries
            query: Original user query
            
        Returns:
            Refined and enhanced analysis
        """
        if not self.openai_client:
            return {"error": "OpenAI client not configured"}
        
        try:
            # Format RAG results for context
            rag_context = self._format_rag_results(rag_results)
            
            refinement_prompt = f"""You are a senior financial analyst refining your investment analysis with additional detailed information from the document database.

ORIGINAL INVESTMENT QUERY: "{query}"

ORIGINAL ANALYSIS:
{json.dumps(original_analysis, indent=2)}

ADDITIONAL INFORMATION FROM RAG DATABASE:
{rag_context}

Please provide a refined and enhanced analysis in JSON format. Keep the same structure as the original analysis but:

1. Integrate the new information where relevant
2. Update conclusions based on additional data
3. Strengthen weak areas identified in the original analysis
4. Provide more specific metrics and details
5. Update confidence levels if appropriate
6. Revise recommendations if new information changes the outlook

Maintain the same JSON structure as the original analysis but enhance the content with the additional information. Mark sections that have been significantly updated.
"""

            response = self.openai_client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are a senior financial analyst integrating new information to enhance investment analysis. Maintain analytical rigor and update conclusions based on evidence."},
                    {"role": "user", "content": refinement_prompt}
                ],
                temperature=0.3
            )
            
            refined_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                if refined_text.startswith('```json'):
                    refined_text = refined_text.split('```json')[1].split('```')[0]
                elif refined_text.startswith('```'):
                    refined_text = refined_text.split('```')[1].split('```')[0]
                
                refined_analysis = json.loads(refined_text)
                
                # Add metadata about refinement
                refined_analysis.update({
                    'query': query,
                    'analysis_type': 'refined_with_rag',
                    'rag_queries_used': len(rag_results),
                    'refinement_timestamp': datetime.now().isoformat(),
                    'original_analysis_timestamp': original_analysis.get('timestamp'),
                    'enhancement_applied': True
                })
                
                logger.info(f"Successfully refined analysis with {len(rag_results)} RAG query results")
                return refined_analysis
                
            except json.JSONDecodeError:
                logger.error("Failed to parse refined analysis JSON")
                return {
                    'error': 'Failed to parse refined analysis response',
                    'raw_response': refined_text,
                    'query': query
                }
                
        except Exception as e:
            logger.error(f"Error refining analysis: {str(e)}")
            return {
                'error': str(e),
                'query': query,
                'original_analysis': original_analysis
            }
    
    def run_iterative_analysis(self, query: str, company_filter: str = None, should_cancel: Optional[callable] = None, analysis_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the complete iterative analysis process
        
        Args:
            query: User's investment query
            company_filter: Optional company name to filter documents
            
        Returns:
            Complete analysis results with iteration history
        """
        if not self.openai_client:
            return {"error": "OpenAI client not configured"}
        
        try:
            logger.info(f"Starting iterative analysis for query: {query}")

            # Helper function to update progress in database
            def update_analysis_progress(**kwargs):
                if analysis_id:
                    try:
                        from analysis.models import IterativeAnalysis
                        analysis = IterativeAnalysis.objects.get(id=analysis_id)
                        analysis.update_progress(**kwargs)
                    except Exception as e:
                        logger.warning(f"Failed to update progress: {str(e)}")

            # Step 1: Gather document summaries
            document_summaries = self.cognee_service.get_document_summaries(company_filter)
            if not document_summaries:
                return {
                    'error': 'No documents available for analysis',
                    'query': query,
                    'company_filter': company_filter
                }

            # Update initial progress
            update_analysis_progress(documents_analyzed=len(document_summaries))
            
            # Cooperative cancellation check
            if should_cancel and should_cancel():
                logger.info("Cancellation requested before starting initial analysis")
                return {
                    'error': 'cancelled',
                    'cancelled': True,
                    'final_analysis': {},
                    'iteration_history': [],
                    'total_iterations': 0,
                    'documents_analyzed': len(document_summaries),
                    'analysis_quality': {
                        'final_completeness_score': 0,
                        'improvement_achieved': False,
                        'rag_queries_executed': 0
                    },
                    'termination_reason': 'User cancelled before analysis started'
                }

            # Step 2: Generate initial comprehensive analysis
            logger.info("Generating initial comprehensive analysis...")
            current_analysis = self.generate_initial_analysis(query, document_summaries)
            if 'error' in current_analysis:
                return current_analysis

            # Track iteration history
            iteration_history = [{
                'iteration': 0,
                'type': 'initial_analysis',
                'timestamp': datetime.now().isoformat(),
                'analysis': current_analysis
            }]

            # Update progress with initial analysis
            update_analysis_progress(
                iteration_history=iteration_history,
                final_analysis=current_analysis
            )
            
            # Step 3: Iterative refinement loop
            for iteration in range(1, self.max_iterations + 1):
                logger.info(f"Starting iteration {iteration} - evaluating analysis completeness...")
                if should_cancel and should_cancel():
                    logger.info("Cancellation requested during evaluation phase")
                    break
                
                # Question the analysis
                evaluation = self.question_analysis_completeness(current_analysis, query)
                if 'error' in evaluation:
                    logger.error(f"Evaluation failed in iteration {iteration}")
                    break
                
                # Check if analysis is complete
                is_complete = evaluation.get('is_analysis_complete', False)
                completeness_score = evaluation.get('completeness_score', 0)
                
                iteration_history.append({
                    'iteration': iteration,
                    'type': 'evaluation',
                    'timestamp': datetime.now().isoformat(),
                    'evaluation': evaluation,
                    'completeness_score': completeness_score,
                    'is_complete': is_complete
                })

                # Update progress after evaluation
                update_analysis_progress(
                    total_iterations=iteration,
                    final_completeness_score=completeness_score,
                    iteration_history=iteration_history
                )

                if is_complete or completeness_score >= 7:
                    logger.info(f"Analysis complete after {iteration} iterations (score: {completeness_score}/10)")
                    break
                
                # Generate targeted RAG queries
                logger.info(f"Generating targeted RAG queries for iteration {iteration}...")
                rag_queries = self.generate_targeted_rag_queries(evaluation, document_summaries)
                
                if not rag_queries:
                    logger.warning(f"No RAG queries generated in iteration {iteration}")
                    break
                
                # Execute RAG queries
                logger.info(f"Executing {len(rag_queries)} RAG queries...")
                rag_results = []
                rag_tool = self.create_rag_query_tool("", "")
                execute_function = rag_tool["execute_function"]
                
                for rag_query in rag_queries:
                    if should_cancel and should_cancel():
                        logger.info("Cancellation requested during RAG execution")
                        break
                    result = execute_function(rag_query, "graph")
                    rag_results.append(result)
                
                iteration_history.append({
                    'iteration': iteration,
                    'type': 'rag_queries',
                    'timestamp': datetime.now().isoformat(),
                    'queries': rag_queries,
                    'results': rag_results
                })

                # Update progress after RAG queries
                total_rag_queries = sum(len(h.get('queries', [])) for h in iteration_history if h['type'] == 'rag_queries')
                update_analysis_progress(
                    rag_queries_executed=total_rag_queries,
                    iteration_history=iteration_history
                )
                
                # Refine analysis with RAG results
                logger.info(f"Refining analysis with RAG results in iteration {iteration}...")
                if should_cancel and should_cancel():
                    logger.info("Cancellation requested before refinement")
                    break
                refined_analysis = self.refine_analysis_with_rag_results(current_analysis, rag_results, query)
                
                if 'error' not in refined_analysis:
                    current_analysis = refined_analysis
                    iteration_history.append({
                        'iteration': iteration,
                        'type': 'refined_analysis',
                        'timestamp': datetime.now().isoformat(),
                        'analysis': refined_analysis
                    })

                    # Update progress after refinement
                    update_analysis_progress(
                        final_analysis=current_analysis,
                        iteration_history=iteration_history
                    )
                else:
                    logger.error(f"Refinement failed in iteration {iteration}")
                    break
            
            # Final results
            final_results = {
                'query': query,
                'company_filter': company_filter,
                'final_analysis': current_analysis,
                'total_iterations': len([h for h in iteration_history if h['type'] == 'evaluation']),
                'documents_analyzed': len(document_summaries),
                'iteration_history': iteration_history,
                'completed_timestamp': datetime.now().isoformat(),
                'analysis_quality': {
                    'final_completeness_score': self._get_final_completeness_score(iteration_history),
                    'improvement_achieved': True,
                    'rag_queries_executed': sum(len(h.get('queries', [])) for h in iteration_history if h['type'] == 'rag_queries')
                }
            }
            
            # Check for cancellation and mark appropriately
            if should_cancel and should_cancel():
                final_results['cancelled'] = True
                final_results['termination_reason'] = 'User cancelled analysis'
                logger.info(f"Analysis cancelled after {final_results['total_iterations']} iterations")
            else:
                logger.info(f"Iterative analysis completed - {final_results['total_iterations']} iterations, {final_results['analysis_quality']['rag_queries_executed']} RAG queries")

            return final_results
            
        except Exception as e:
            logger.error(f"Error in iterative analysis: {str(e)}")

            # Try to capture any partial results that were generated before the error
            partial_results = {
                'error': str(e),
                'query': query,
                'company_filter': company_filter,
                'termination_reason': f'Analysis failed: {str(e)}'
            }

            # Include any partial data that was generated
            if 'current_analysis' in locals():
                partial_results['final_analysis'] = current_analysis
            if 'iteration_history' in locals():
                partial_results['iteration_history'] = iteration_history
                partial_results['total_iterations'] = len(iteration_history)
            if 'document_summaries' in locals():
                partial_results['documents_analyzed'] = len(document_summaries)

            return partial_results
    
    def _format_documents_for_analysis(self, document_summaries: List[Dict[str, Any]]) -> str:
        """Format document summaries for LLM consumption"""
        if not document_summaries:
            return "No documents available."
        
        formatted_docs = []
        for i, doc in enumerate(document_summaries, 1):
            summary = doc.get('summary', {})
            formatted_doc = f"""
Document {i}: {doc.get('company_name', 'Unknown')} - {doc.get('form_type', 'Unknown')} ({doc.get('filing_date', 'Unknown Date')})
- Executive Summary: {summary.get('executive_summary', 'Not available')}
- Financial Highlights: {summary.get('financial_highlights', 'Not available')}
- Investment Insights: {summary.get('investment_insights', 'Not available')}
- Risk Factors: {summary.get('risk_factors', 'Not available')}
- Content Length: {doc.get('content_length', 0):,} characters
"""
            formatted_docs.append(formatted_doc)
        
        return "\n".join(formatted_docs)
    
    def _format_rag_results(self, rag_results: List[Dict[str, Any]]) -> str:
        """Format RAG results for LLM consumption"""
        if not rag_results:
            return "No RAG results available."
        
        formatted_results = []
        for i, result in enumerate(rag_results, 1):
            query = result.get('query', 'Unknown query')
            results = result.get('results', [])
            result_text = "\n".join(str(r) for r in results[:3])  # Top 3 results
            
            formatted_result = f"""
RAG Query {i}: "{query}"
Results ({len(results)} total):
{result_text}
"""
            formatted_results.append(formatted_result)
        
        return "\n".join(formatted_results)

    def _get_final_completeness_score(self, iteration_history: List[Dict[str, Any]]) -> float:
        """Extract the final completeness score from the last evaluation iteration"""
        # Find the last evaluation iteration
        for iteration in reversed(iteration_history):
            if iteration.get('type') == 'evaluation':
                return iteration.get('completeness_score', 0.0)
        return 0.0
