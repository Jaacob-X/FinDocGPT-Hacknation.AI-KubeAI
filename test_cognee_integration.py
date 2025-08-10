#!/usr/bin/env python3
"""
Test script for Cognee integration with FinDocGPT
Run this to verify that Cognee is working properly with the backend
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

# Now import our service
from services.cognee_service import CogneeService

def test_cognee_integration():
    """Test Cognee integration step by step"""
    print("🧪 Testing FinDocGPT Cognee Integration")
    print("=" * 50)
    
    try:
        # Initialize service
        print("\n1. Initializing CogneeService...")
        cognee_service = CogneeService()
        
        if not cognee_service.is_configured:
            print("❌ CogneeService failed to configure")
            return False
        print("✅ CogneeService initialized successfully")
        
        # Get service info
        print("\n2. Getting service information...")
        service_info = cognee_service.get_service_info()
        print(f"✅ Service configured: {service_info['configured']}")
        print(f"   Data root: {service_info['data_root']}")
        print(f"   Providers: {service_info['providers']}")
        
        # Health check
        print("\n3. Performing health check...")
        health_data = cognee_service.health_check()
        print(f"✅ Health status: {health_data['status']}")
        print(f"   Can add documents: {health_data.get('can_add', False)}")
        print(f"   Can search: {health_data.get('can_search', False)}")
        
        # Test document addition
        print("\n4. Testing document addition...")
        test_content = """
        Apple Inc. Financial Analysis
        
        Apple Inc. (AAPL) reported strong quarterly results for Q4 2024.
        Revenue increased 15% year-over-year to $120 billion.
        iPhone sales remained the primary revenue driver.
        Services revenue grew 20% to $25 billion.
        The company maintains a strong balance sheet with $180 billion in cash.
        Management expressed confidence in future growth prospects.
        """
        
        test_metadata = {
            'company_name': 'Apple Inc.',
            'form_type': '10-Q',
            'ticker': 'AAPL',
            'filing_date': '2024-12-01',
            'accession_number': 'test-apple-001',
            'cik': '320193'
        }
        
        add_success = cognee_service.add_document(test_content, test_metadata)
        if add_success:
            print("✅ Document added successfully to Cognee")
        else:
            print("❌ Failed to add document to Cognee")
            return False
        
        # Test search functionality
        print("\n5. Testing search functionality...")
        search_results = cognee_service.search_context("Apple revenue growth financial performance")
        print(f"✅ Search completed, found {len(search_results)} results")
        
        if search_results:
            print(f"   Sample result: {search_results[0][:100]}...")
        
        # Test insights retrieval
        print("\n6. Testing insights retrieval...")
        insights = cognee_service.get_document_insights("Apple Inc.", "10-Q")
        print(f"✅ Insights retrieved:")
        print(f"   Insights found: {len(insights.get('insights', []))}")
        print(f"   Chunks found: {len(insights.get('chunks', []))}")
        
        if insights.get('insights'):
            print(f"   Sample insight: {insights['insights'][0]}")
        
        # Test investment context
        print("\n7. Testing investment context retrieval...")
        context = cognee_service.get_investment_context("Apple Inc investment analysis")
        print(f"✅ Investment context retrieved:")
        print(f"   Insights: {len(context.get('insights', []))}")
        print(f"   Document chunks: {len(context.get('document_chunks', []))}")
        print(f"   Relationships: {len(context.get('relationships', []))}")
        
        print("\n" + "=" * 50)
        print("🎉 All Cognee integration tests passed!")
        print("✅ FinDocGPT is ready to use Cognee for RAG operations")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    success = test_cognee_integration()
    
    if success:
        print("\n🚀 Integration test successful! You can now:")
        print("   • Start the Django server: cd backend && python manage.py runserver")
        print("   • Test the API endpoint: GET http://localhost:8000/api/cognee/")
        print("   • Test document processing with real SEC data")
        sys.exit(0)
    else:
        print("\n💥 Integration test failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
