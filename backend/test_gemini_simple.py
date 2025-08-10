#!/usr/bin/env python3
"""
Simple test for Gemini validation service without Django dependencies

This script tests the Gemini validation service directly without requiring
Django setup. Useful for quick testing and debugging.

To run: python test_gemini_simple.py
"""

import sys
import os
from pathlib import Path

# Add the services directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'services'))

# Import the service directly
from gemini_validation_service import GeminiValidationService

def test_gemini_service():
    """Test the Gemini validation service directly"""
    
    print("🧪 Testing Gemini Validation Service (Simple)")
    print("=" * 50)
    
    # Initialize the service
    validation_service = GeminiValidationService()
    
    if not validation_service.is_configured:
        print("❌ Gemini validation service not configured.")
        print("Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
        print()
        print("To get an API key:")
        print("1. Visit https://aistudio.google.com/app/apikey")
        print("2. Create a new API key")
        print("3. Set it in your environment: export GEMINI_API_KEY=your_key_here")
        return
    
    print("✅ Gemini validation service configured successfully")
    print()
    
    # Test Case 1: Poor response that should fail validation
    print("📋 Test Case 1: Poor Financial Response (Tests Trusted Sources)")
    print("-" * 40)

    query1 = "What is Apple's current revenue growth rate and profit margins?"
    poor_response = [
        "Apple is a technology company.",
        "They make iPhones and computers.",
        "The company was founded by Steve Jobs."
    ]
    
    print(f"Query: {query1}")
    print(f"Response: {poor_response}")
    print()
    
    validation1 = validation_service.validate_rag_response(query1, poor_response)
    print("Validation Result:")
    print(f"  ✓ Available: {validation1.get('validation_available', 'Unknown')}")
    print(f"  ✓ Passed: {validation1.get('validation_passed', 'Unknown')}")
    print(f"  ✓ Reasoning: {validation1.get('reasoning', 'No reasoning')}")
    print(f"  ✓ Confidence: {validation1.get('confidence_score', 'Unknown')}")
    
    if not validation1.get('validation_passed', True):
        print("\n🔍 Since validation failed, testing Gemini search...")
        search_result = validation_service.search_with_gemini(query1)
        
        if search_result.get('search_available'):
            print("  ✓ Search successful!")
            response = search_result.get('response', '')
            print(f"  ✓ Response preview: {response[:200]}...")

            # Check quality assessment
            quality = search_result.get('quality_assessment', {})
            if quality:
                print(f"  ✓ Quality score: {quality.get('quality_score', 'Unknown')}")
                print(f"  ✓ Meets financial standards: {quality.get('meets_financial_standards', 'Unknown')}")
                print(f"  ✓ Has trusted sources: {quality.get('quality_indicators', {}).get('has_sources', 'Unknown')}")
        else:
            print(f"  ✗ Search failed: {search_result.get('reasoning', 'Unknown')}")
    
    print()
    print("=" * 50)
    
    # Test Case 2: Good response that should pass validation
    print("📋 Test Case 2: Good Response")
    print("-" * 40)
    
    query2 = "What is the capital of France?"
    good_response = [
        "The capital of France is Paris.",
        "Paris is located in the north-central part of France and serves as the country's political, economic, and cultural center.",
        "It has been the capital since 987 AD and is the largest city in France with over 2 million inhabitants."
    ]
    
    print(f"Query: {query2}")
    print(f"Response: {good_response}")
    print()
    
    validation2 = validation_service.validate_rag_response(query2, good_response)
    print("Validation Result:")
    print(f"  ✓ Available: {validation2.get('validation_available', 'Unknown')}")
    print(f"  ✓ Passed: {validation2.get('validation_passed', 'Unknown')}")
    print(f"  ✓ Reasoning: {validation2.get('reasoning', 'No reasoning')}")
    print(f"  ✓ Confidence: {validation2.get('confidence_score', 'Unknown')}")
    
    print()
    print("=" * 50)
    
    # Test Case 3: Complete pipeline test
    print("📋 Test Case 3: Complete Pipeline")
    print("-" * 40)
    
    query3 = "What are the latest developments in Tesla's autonomous driving technology?"
    poor_tesla_response = [
        "Tesla makes electric cars.",
        "Elon Musk is the CEO."
    ]
    
    print(f"Query: {query3}")
    print(f"Poor Response: {poor_tesla_response}")
    print()
    
    complete_result = validation_service.validate_and_enhance_rag_response(query3, poor_tesla_response)
    
    print("Complete Pipeline Result:")
    validation = complete_result.get('validation_result', {})
    print(f"  ✓ Validation Passed: {validation.get('validation_passed', 'Unknown')}")
    print(f"  ✓ Final Source: {complete_result.get('final_source', 'Unknown')}")
    
    enhanced = complete_result.get('enhanced_response')
    if enhanced and enhanced.get('search_available'):
        print("  ✓ Enhancement: Available")
        final_response = validation_service.get_final_response(complete_result)
        if final_response:
            print(f"  ✓ Final Response Preview: {final_response[0][:200]}...")
    else:
        print("  ✗ Enhancement: Not available")
    
    print()
    print("🎉 Simple testing completed!")
    print()
    print("💡 Next steps:")
    print("1. If tests passed, try running: python test_gemini_validation.py")
    print("2. Set up your .env file with GEMINI_API_KEY if not already done")
    print("3. Test the full integration with your RAG system")

if __name__ == "__main__":
    test_gemini_service()
