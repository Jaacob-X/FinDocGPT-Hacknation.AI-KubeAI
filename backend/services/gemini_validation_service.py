import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI SDK not available. Gemini validation will be disabled.")

logger = logging.getLogger(__name__)

class GeminiValidationService:
    """
    Service for validating RAG responses using Gemini and enhancing with internet search
    
    This service:
    1. Validates if RAG responses adequately answer user queries
    2. Uses Gemini's search capabilities to find internet-based answers when RAG fails
    3. Provides enhanced responses with source attribution
    """
    
    def __init__(self):
        self.client = None
        self.is_configured = False
        self.validation_enabled = True
        self._configure_gemini()
    
    def _configure_gemini(self):
        """Configure Gemini client with API key"""
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini SDK not available - validation service disabled")
            self.validation_enabled = False
            return
        
        try:
            # Get API key from environment
            api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if not api_key:
                logger.warning("No Gemini API key found in environment variables (GEMINI_API_KEY or GOOGLE_API_KEY)")
                self.validation_enabled = False
                return
            
            # Configure the client
            self.client = genai.Client(api_key=api_key)
            self.is_configured = True
            logger.info("Gemini validation service configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {str(e)}")
            self.validation_enabled = False
    
    def validate_rag_response(self, query: str, rag_response: List[str]) -> Dict[str, Any]:
        """
        Validate if the RAG response adequately answers the user query
        
        Args:
            query: The original user query
            rag_response: List of RAG response strings
            
        Returns:
            Dict containing validation results
        """
        if not self.is_configured or not self.validation_enabled:
            return {
                'validation_available': False,
                'validation_passed': True,  # Default to passing if validation unavailable
                'reasoning': 'Gemini validation not available',
                'confidence_score': 0.5
            }
        
        try:
            # Combine RAG responses into a single text
            combined_response = "\n".join(rag_response) if rag_response else "No response available"
            
            validation_prompt = f"""
You are an expert financial information evaluator. Please assess whether the provided response adequately answers the user's financial question with appropriate accuracy and completeness.

User Question: {query}

Response to Evaluate: {combined_response}

FINANCIAL INFORMATION EVALUATION CRITERIA:
1. Does the response directly address the specific financial question asked?
2. Is the information relevant, specific, and actionable for financial decision-making?
3. Are there significant gaps or missing critical financial information?
4. Is the response substantive enough to be helpful for investment/financial analysis?
5. For financial data: Are specific numbers, dates, and sources provided when needed?
6. For market information: Is the timeframe and context clearly specified?
7. For company information: Are the metrics relevant to the financial question?

SPECIAL REQUIREMENTS FOR FINANCIAL QUERIES:
- Current market data (stock prices, rates) requires real-time or very recent information
- Financial metrics should include context (time period, comparison benchmarks)
- Regulatory or policy questions need authoritative sources
- Investment advice should be clearly distinguished from factual data

Respond with a JSON object containing:
- "validation_passed": true/false
- "reasoning": detailed explanation focusing on financial information quality
- "confidence_score": 0.0-1.0 indicating confidence in the response quality for financial use
- "missing_aspects": list of key financial aspects not addressed (if any)
- "requires_current_data": true/false if the question needs real-time financial information

Be VERY strict in your evaluation - only pass responses that provide genuinely useful financial information that could support investment or business decisions.
"""

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=validation_prompt
            )
            
            # Parse the response
            response_text = response.text.strip()
            
            # Extract JSON from response
            import json
            try:
                if response_text.startswith('```json'):
                    response_text = response_text.split('```json')[1].split('```')[0]
                elif response_text.startswith('```'):
                    response_text = response_text.split('```')[1].split('```')[0]
                
                validation_result = json.loads(response_text)
                
                logger.info(f"Validation result for query '{query[:50]}...': {validation_result.get('validation_passed', False)}")
                return validation_result
                
            except json.JSONDecodeError:
                logger.error("Failed to parse Gemini validation response as JSON")
                return {
                    'validation_available': True,
                    'validation_passed': False,
                    'reasoning': 'Failed to parse validation response',
                    'confidence_score': 0.0
                }
                
        except Exception as e:
            logger.error(f"Error during Gemini validation: {str(e)}")
            return {
                'validation_available': False,
                'validation_passed': True,  # Default to passing on error
                'reasoning': f'Validation error: {str(e)}',
                'confidence_score': 0.5
            }
    
    def search_with_gemini(self, query: str) -> Dict[str, Any]:
        """
        Use Gemini's search capabilities to find internet-based answers
        
        Args:
            query: The search query
            
        Returns:
            Dict containing search results and response
        """
        if not self.is_configured or not self.validation_enabled:
            return {
                'search_available': False,
                'response': None,
                'reasoning': 'Gemini search not available'
            }
        
        try:
            # Define the grounding tool for search
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            
            # Configure generation settings
            config = types.GenerateContentConfig(
                tools=[grounding_tool]
            )
            
            # Enhance the query for better financial context with emphasis on trusted sources
            enhanced_query = f"""
Please provide a comprehensive answer to this financial/investment question using current information from TRUSTED and AUTHORITATIVE sources only:

{query}

CRITICAL REQUIREMENTS for financial information:
- ONLY use information from trusted financial sources such as:
  * Official company filings (SEC, 10-K, 10-Q, 8-K reports)
  * Reputable financial news outlets (Reuters, Bloomberg, Wall Street Journal, Financial Times)
  * Government financial agencies (Federal Reserve, Treasury, SEC, BLS)
  * Established financial data providers (Yahoo Finance, Google Finance, MarketWatch)
  * Major investment banks and research firms (Goldman Sachs, Morgan Stanley, etc.)
  * Credit rating agencies (Moody's, S&P, Fitch)

- AVOID unverified sources, social media, blogs, or unofficial websites
- When providing specific numbers (stock prices, financial metrics), cite the exact source and timestamp
- If conflicting information exists, mention the discrepancy and source reliability
- Clearly distinguish between factual data and analyst opinions/projections

Focus on:
- Recent financial data and trends from official sources
- Market analysis from reputable financial institutions
- Regulatory or industry developments from government agencies
- Quantitative metrics with proper source attribution

Always include source citations and timestamps when available. If reliable sources cannot be found for specific claims, explicitly state this limitation.
"""
            
            # Make the search request
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=enhanced_query,
                config=config
            )
            
            search_response = response.text.strip()

            # Validate the search response for financial information quality
            quality_check = self._validate_financial_search_quality(search_response, query)

            logger.info(f"Gemini search completed for query: {query[:50]}... - Quality: {quality_check.get('quality_score', 'Unknown')}")

            return {
                'search_available': True,
                'response': search_response,
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'source': 'gemini_search',
                'quality_assessment': quality_check
            }
            
        except Exception as e:
            logger.error(f"Error during Gemini search: {str(e)}")
            return {
                'search_available': False,
                'response': None,
                'reasoning': f'Search error: {str(e)}',
                'error': str(e)
            }
    
    def validate_and_enhance_rag_response(self, query: str, rag_response: List[str]) -> Dict[str, Any]:
        """
        Complete validation and enhancement pipeline
        
        Args:
            query: The original user query
            rag_response: List of RAG response strings
            
        Returns:
            Dict containing validation results and enhanced response if needed
        """
        # Step 1: Validate the RAG response
        validation_result = self.validate_rag_response(query, rag_response)
        
        # Step 2: If validation fails, search with Gemini
        enhanced_response = None
        if validation_result.get('validation_passed', True) == False:
            logger.info(f"RAG validation failed for query: {query[:50]}... - searching with Gemini")
            enhanced_response = self.search_with_gemini(query)
        
        # Step 3: Return comprehensive results
        return {
            'query': query,
            'original_rag_response': rag_response,
            'validation_result': validation_result,
            'enhanced_response': enhanced_response,
            'final_source': 'gemini_search' if enhanced_response and enhanced_response.get('search_available') else 'rag',
            'timestamp': datetime.now().isoformat()
        }
    
    def _validate_financial_search_quality(self, search_response: str, query: str) -> Dict[str, Any]:
        """
        Validate the quality of Gemini search results for financial information

        Args:
            search_response: The response from Gemini search
            query: The original query

        Returns:
            Dict containing quality assessment
        """
        try:
            # Check for key quality indicators
            quality_indicators = {
                'has_sources': any(indicator in search_response.lower() for indicator in [
                    'reuters', 'bloomberg', 'wall street journal', 'financial times',
                    'sec filing', '10-k', '10-q', 'federal reserve', 'treasury',
                    'yahoo finance', 'marketwatch', 'source:', 'according to'
                ]),
                'has_specific_data': any(indicator in search_response for indicator in [
                    '$', '%', 'billion', 'million', 'quarter', 'Q1', 'Q2', 'Q3', 'Q4',
                    '2024', '2025', 'fiscal year'
                ]),
                'has_timeframe': any(indicator in search_response.lower() for indicator in [
                    'as of', 'current', 'latest', 'recent', 'today', 'this year',
                    'january', 'february', 'march', 'april', 'may', 'june',
                    'july', 'august', 'september', 'october', 'november', 'december'
                ]),
                'appropriate_length': 100 < len(search_response) < 2000,
                'no_disclaimers_only': not (
                    len(search_response) < 200 and
                    any(phrase in search_response.lower() for phrase in [
                        'cannot provide', 'unable to access', 'no information available'
                    ])
                )
            }

            # Calculate quality score
            quality_score = sum(quality_indicators.values()) / len(quality_indicators)

            # Determine if response meets financial information standards
            meets_standards = (
                quality_indicators['has_specific_data'] and
                quality_indicators['appropriate_length'] and
                quality_indicators['no_disclaimers_only'] and
                quality_score >= 0.6
            )

            return {
                'quality_score': quality_score,
                'meets_financial_standards': meets_standards,
                'quality_indicators': quality_indicators,
                'assessment_timestamp': datetime.now().isoformat(),
                'recommendation': 'use' if meets_standards else 'review_carefully'
            }

        except Exception as e:
            logger.error(f"Error validating search quality: {str(e)}")
            return {
                'quality_score': 0.5,
                'meets_financial_standards': False,
                'error': str(e),
                'recommendation': 'review_carefully'
            }

    def get_final_response(self, validation_result: Dict[str, Any]) -> List[str]:
        """
        Extract the final response to use based on validation results

        Args:
            validation_result: Result from validate_and_enhance_rag_response

        Returns:
            List of response strings to use
        """
        enhanced_response = validation_result.get('enhanced_response')

        if (enhanced_response and
            enhanced_response.get('search_available') and
            enhanced_response.get('response')):

            # Check quality assessment if available
            quality_assessment = enhanced_response.get('quality_assessment', {})
            if quality_assessment.get('meets_financial_standards', True):
                # Use Gemini search response if it meets financial standards
                return [enhanced_response['response']]
            else:
                # Add quality warning to the response
                warning = "\n\n[Note: This information from web search may not meet all financial data quality standards. Please verify with authoritative sources.]"
                return [enhanced_response['response'] + warning]
        else:
            # Fall back to original RAG response
            return validation_result.get('original_rag_response', [])
