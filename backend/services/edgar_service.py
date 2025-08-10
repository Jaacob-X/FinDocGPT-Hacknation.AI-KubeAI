"""
EdgarTools service for fetching SEC filings and company data
"""
import os
import logging
from typing import List, Dict, Any, Optional
from edgar import Company, get_filings, find
from datetime import datetime

logger = logging.getLogger(__name__)

class EdgarService:
    """Service for interacting with SEC Edgar database using EdgarTools"""
    
    def __init__(self):
        self.user_agent = os.getenv('EDGAR_USER_AGENT', 'FinDocGPT (demo@example.com)')
        # Set user agent for Edgar requests
        import edgar
        if hasattr(edgar, 'set_identity'):
            edgar.set_identity(self.user_agent)
        
    def search_company(self, query: str) -> List[Dict[str, Any]]:
        """Search for companies by name or ticker symbol"""
        try:
            # Try to get company by ticker first
            try:
                company = Company(query.upper())
                return [{
                    'cik': company.cik,
                    'name': company.name,
                    'ticker': company.ticker,
                    'sic': getattr(company, 'sic', None),
                    'industry': getattr(company, 'industry', None)
                }]
            except Exception:
                # If ticker search fails, try name search
                # For demo purposes, we'll return a mock result
                # In production, you'd implement proper company search
                return [{
                    'cik': '0000320193',
                    'name': 'Apple Inc.',
                    'ticker': 'AAPL',
                    'sic': '3571',
                    'industry': 'Electronic Computers'
                }]
                
        except Exception as e:
            logger.error(f"Error searching for company {query}: {str(e)}")
            return []
    
    def get_company_filings(self, ticker: str, form_types: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent filings for a company"""
        if form_types is None:
            form_types = ['10-K', '10-Q', '8-K']
            
        try:
            company = Company(ticker.upper())
            filings = []
            
            # Get filings for all requested form types
            company_filings = company.get_filings(form=form_types)
            
            # Convert to our format, limiting results
            for filing in company_filings.head(limit):
                try:
                    filings.append({
                        'accession_number': filing.accession_no,
                        'form': filing.form,
                        'filing_date': filing.filing_date,
                        'period_of_report': getattr(filing, 'period_of_report', None),
                        'company_name': filing.company,
                        'ticker': ticker.upper(),
                        'cik': str(filing.cik),
                        'description': f"{filing.form} filing for {filing.company}",
                        'url': f"https://www.sec.gov/Archives/edgar/data/{filing.cik}/{filing.accession_no.replace('-', '')}/{filing.accession_no}-index.html"
                    })
                except Exception as e:
                    logger.warning(f"Error processing filing {filing.accession_no}: {str(e)}")
                    continue
                    
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {str(e)}")
            return []
    
    def get_filing_content(self, accession_number: str, cik: str) -> Optional[Dict[str, Any]]:
        """Get the content of a specific filing"""
        try:
            # For EdgarTools, we need to find the filing first
            # This is a simplified approach - in production you might cache filings
            company = Company(cik)
            company_filings = company.get_filings()
            
            # Find the specific filing by accession number
            target_filing = None
            for filing in company_filings:
                if filing.accession_no == accession_number:
                    target_filing = filing
                    break
            
            if not target_filing:
                logger.error(f"Filing {accession_number} not found for CIK {cik}")
                return None
            
            # Get text content
            text_content = target_filing.text()
            
            return {
                'accession_number': accession_number,
                'content': text_content,
                'content_type': 'text',
                'size': len(text_content) if text_content else 0,
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching filing content for {accession_number}: {str(e)}")
            return None
    
    def search_filings_by_query(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for filings based on a natural language query"""
        # Extract potential ticker symbols or company names from query
        query_upper = query.upper()
        
        # Common ticker symbols for demo
        demo_companies = {
            'APPLE': 'AAPL',
            'MICROSOFT': 'MSFT', 
            'GOOGLE': 'GOOGL',
            'AMAZON': 'AMZN',
            'TESLA': 'TSLA',
            'META': 'META',
            'NVIDIA': 'NVDA'
        }
        
        # Try to extract ticker from query
        ticker = None
        for company_name, company_ticker in demo_companies.items():
            if company_name in query_upper or company_ticker in query_upper:
                ticker = company_ticker
                break
        
        if ticker:
            return self.get_company_filings(ticker, limit=limit)
        else:
            # Default to Apple for demo if no company found
            return self.get_company_filings('AAPL', limit=5)
