#!/usr/bin/env python3
"""
Demo script showing the interactive FinDocGPT capabilities
This demonstrates the flow without requiring user input
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finDocGPT.settings')
django.setup()

# Import services
from services.edgar_service import EdgarService
from services.cognee_service import CogneeService

def demo_flow():
    """Demonstrate the complete flow"""
    print("🚀 FinDocGPT Interactive Demo")
    print("="*50)
    
    # Initialize services
    print("\n1. Initializing services...")
    edgar_service = EdgarService()
    cognee_service = CogneeService()
    
    if not cognee_service.is_configured:
        print("❌ Cognee not configured. Please check your .env file.")
        return
    
    print("✅ Services initialized")
    
    # Demo search
    print("\n2. Searching for Apple Inc documents...")
    try:
        filings = edgar_service.search_filings_by_query("Apple Inc", limit=2)
        print(f"✅ Found {len(filings)} documents:")
        
        for filing in filings:
            print(f"  • {filing['form']} - {filing['company_name']} ({filing['filing_date']})")
        
        if not filings:
            print("❌ No documents found")
            return
        
        # Demo document processing
        print(f"\n3. Processing first document: {filings[0]['form']} - {filings[0]['company_name']}")
        
        content_data = edgar_service.get_filing_content(
            filings[0]['accession_number'], 
            filings[0]['cik']
        )
        
        if content_data:
            print(f"✅ Content fetched ({content_data['size']} characters)")
            
            # Store in Cognee
            print("4. Storing in Cognee RAG...")
            metadata = {
                'company_name': filings[0]['company_name'],
                'form_type': filings[0]['form'],
                'ticker': filings[0].get('ticker', ''),
                'filing_date': str(filings[0]['filing_date']),
                'accession_number': filings[0]['accession_number'],
                'cik': filings[0]['cik']
            }
            
            success = cognee_service.add_document(content_data['content'], metadata)
            
            if success:
                print("✅ Document stored in Cognee")
                
                # Demo querying
                print("\n5. Querying stored document...")
                
                test_queries = [
                    "What is Apple's revenue?",
                    "What are the main business segments?", 
                    "What are key risk factors?"
                ]
                
                for query in test_queries:
                    print(f"\n💬 Query: '{query}'")
                    
                    # Use natural language search (like the Cognee example)
                    natural_results = cognee_service.search_context(query, "natural")
                    print(f"✅ Natural language response generated: {len(natural_results) > 0}")
                    
                    if natural_results:
                        # Show natural language response
                        response = str(natural_results[0])[:300] + "..."
                        print(f"🤖 AI Response: {response}")
                    
                    # Also test investment context
                    context = cognee_service.get_investment_context(query)
                    if context.get('insights'):
                        print(f"💡 Investment insights: {len(context['insights'])} generated")
                        if context['insights']:
                            insight_sample = str(context['insights'][0])[:200] + "..."
                            print(f"   Sample insight: {insight_sample}")
                
                print("\n🎉 Demo completed successfully!")
                print("\n💡 To use interactively, run:")
                print("   python interactive_cognee_edgar.py")
                
            else:
                print("❌ Failed to store document")
        else:
            print("❌ Failed to fetch document content")
            
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")

if __name__ == "__main__":
    demo_flow()
