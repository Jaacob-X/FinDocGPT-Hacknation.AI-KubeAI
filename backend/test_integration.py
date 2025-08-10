#!/usr/bin/env python3
"""
Integration test for the enhanced RAG system with Gemini validation

This test demonstrates the complete flow:
1. RAG query execution
2. Gemini validation
3. Enhancement with web search (if needed)
4. Integration with iterative analysis

To run: python test_integration.py
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finDocGPT.settings')
django.setup()

from services.iterative_analysis_service import IterativeAnalysisService

def test_enhanced_rag_integration():
    """Test the complete enhanced RAG pipeline"""
    
    print("🔬 Testing Enhanced RAG Integration")
    print("=" * 50)
    
    # Initialize the service (includes Gemini validation)
    analysis_service = IterativeAnalysisService()
    
    # Check if Gemini validation is available
    gemini_available = analysis_service.gemini_validation_service.is_configured
    print(f"Gemini Validation Available: {'✅ Yes' if gemini_available else '❌ No'}")
    
    if not gemini_available:
        print("Note: Gemini validation not configured. Set GEMINI_API_KEY to test enhancement.")
        print("The system will still work but will only use RAG responses.")
    
    print()
    
    # Create the RAG query tool
    rag_tool = analysis_service.create_rag_query_tool("", "")
    execute_function = rag_tool["execute_function"]
    
    # Test queries that are likely to have poor RAG responses
    test_queries = [
        "What is the current stock price of Tesla?",
        "What are the latest market trends in renewable energy?",
        "How has inflation affected consumer spending in 2024?",
        "What is the current Federal Reserve interest rate?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"📋 Test Query {i}: {query}")
        print("-" * 40)
        
        # Execute the enhanced RAG query
        result = execute_function(query, "graph")
        
        # Display results
        print(f"Query: {result.get('query', 'Unknown')}")
        print(f"Source: {result.get('source', 'Unknown')}")
        print(f"Result Count: {result.get('result_count', 0)}")
        print(f"Original RAG Count: {result.get('original_result_count', 0)}")
        
        # Show validation details if available
        validation = result.get('validation_result', {})
        if validation:
            val_result = validation.get('validation_result', {})
            print(f"Validation Passed: {val_result.get('validation_passed', 'Unknown')}")
            print(f"Validation Reasoning: {val_result.get('reasoning', 'No reasoning')}")
            
            enhanced = validation.get('enhanced_response')
            if enhanced and enhanced.get('search_available'):
                print("Enhancement: ✅ Gemini search used")
                response_preview = enhanced.get('response', '')[:150]
                print(f"Enhanced Response Preview: {response_preview}...")
            else:
                print("Enhancement: ❌ Not used")
        
        # Show response preview
        results = result.get('results', [])
        if results:
            response_preview = results[0][:150] if results[0] else "No response"
            print(f"Response Preview: {response_preview}...")
        else:
            print("Response: No results returned")
        
        print()
    
    print("=" * 50)
    print("🎉 Integration testing completed!")
    print()
    
    # Summary
    print("📊 Summary:")
    print("- The enhanced RAG system is now active")
    print("- Gemini validation will evaluate RAG responses")
    print("- Poor responses will be enhanced with web search")
    print("- Source attribution is included in all responses")
    print("- The iterative analysis will receive higher quality information")

if __name__ == "__main__":
    test_enhanced_rag_integration()
