#!/usr/bin/env python3
"""
Test script for Gemini validation service

This script demonstrates how the new Gemini validation layer works:
1. Simulates a RAG query with a poor response
2. Shows how Gemini validates the response
3. Demonstrates Gemini search enhancement when validation fails

To run this test:
1. Set your GEMINI_API_KEY environment variable
2. Run: python test_gemini_validation.py
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

from services.gemini_validation_service import GeminiValidationService

def test_validation_service():
    """Test the Gemini validation service with example queries"""
    
    print("🧪 Testing Gemini Validation Service")
    print("=" * 50)
    
    # Initialize the service
    validation_service = GeminiValidationService()
    
    if not validation_service.is_configured:
        print("❌ Gemini validation service not configured.")
        print("Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
        return
    
    print("✅ Gemini validation service configured successfully")
    print()
    
    # Test Case 1: Poor RAG response that should fail validation
    print("📋 Test Case 1: Poor RAG Response")
    print("-" * 30)
    
    query1 = "What is Apple's current revenue growth rate?"
    poor_rag_response = [
        "Apple is a technology company.",
        "They make iPhones and computers.",
        "The company was founded by Steve Jobs."
    ]
    
    print(f"Query: {query1}")
    print(f"RAG Response: {poor_rag_response}")
    print()
    
    result1 = validation_service.validate_and_enhance_rag_response(query1, poor_rag_response)
    
    print("Validation Result:")
    validation = result1.get('validation_result', {})
    print(f"  - Validation Passed: {validation.get('validation_passed', 'Unknown')}")
    print(f"  - Reasoning: {validation.get('reasoning', 'No reasoning provided')}")
    print(f"  - Confidence Score: {validation.get('confidence_score', 'Unknown')}")
    print(f"  - Final Source: {result1.get('final_source', 'Unknown')}")
    
    enhanced = result1.get('enhanced_response')
    if enhanced and enhanced.get('search_available'):
        print(f"  - Enhanced Response Available: Yes")
        print(f"  - Enhanced Response Preview: {enhanced.get('response', '')[:200]}...")
    else:
        print(f"  - Enhanced Response Available: No")
    
    print()
    print("=" * 50)
    
    # Test Case 2: Good RAG response that should pass validation
    print("📋 Test Case 2: Good RAG Response")
    print("-" * 30)
    
    query2 = "What is the capital of France?"
    good_rag_response = [
        "The capital of France is Paris.",
        "Paris is located in the north-central part of France.",
        "It has been the capital since 987 AD and is the country's largest city."
    ]
    
    print(f"Query: {query2}")
    print(f"RAG Response: {good_rag_response}")
    print()
    
    result2 = validation_service.validate_and_enhance_rag_response(query2, good_rag_response)
    
    print("Validation Result:")
    validation2 = result2.get('validation_result', {})
    print(f"  - Validation Passed: {validation2.get('validation_passed', 'Unknown')}")
    print(f"  - Reasoning: {validation2.get('reasoning', 'No reasoning provided')}")
    print(f"  - Confidence Score: {validation2.get('confidence_score', 'Unknown')}")
    print(f"  - Final Source: {result2.get('final_source', 'Unknown')}")
    
    enhanced2 = result2.get('enhanced_response')
    if enhanced2 and enhanced2.get('search_available'):
        print(f"  - Enhanced Response Available: Yes")
    else:
        print(f"  - Enhanced Response Available: No")
    
    print()
    print("=" * 50)
    
    # Test Case 3: Direct Gemini search test
    print("📋 Test Case 3: Direct Gemini Search")
    print("-" * 30)
    
    search_query = "What is Tesla's stock performance in 2024?"
    print(f"Search Query: {search_query}")
    print()
    
    search_result = validation_service.search_with_gemini(search_query)
    
    print("Search Result:")
    print(f"  - Search Available: {search_result.get('search_available', 'Unknown')}")
    if search_result.get('search_available'):
        response = search_result.get('response', '')
        print(f"  - Response Preview: {response[:300]}...")
    else:
        print(f"  - Error: {search_result.get('reasoning', 'Unknown error')}")
    
    print()
    print("🎉 Testing completed!")

if __name__ == "__main__":
    test_validation_service()
