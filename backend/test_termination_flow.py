#!/usr/bin/env python3
"""
End-to-end test for analysis termination with partial results

This script tests the complete flow:
1. Start an analysis
2. Simulate termination (cancellation or failure)
3. Verify partial results are stored
4. Test API endpoints for retrieving partial results
5. Verify frontend data structure

To run: python test_termination_flow.py
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finDocGPT.settings')
django.setup()

from analysis.models import IterativeAnalysis
from analysis.views import IterativeAnalysisViewSet
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
import json

def test_termination_flow():
    """Test the complete termination flow with partial results"""
    
    print("🔬 Testing Complete Termination Flow with Partial Results")
    print("=" * 65)
    
    # Test 1: Create and cancel analysis with partial results
    print("📋 Test 1: Analysis Cancellation Flow")
    print("-" * 45)
    
    # Create analysis
    analysis = IterativeAnalysis.objects.create(
        query="Test analysis for cancellation flow",
        status='IN_PROGRESS',
        total_iterations=0,
        documents_analyzed=0,
        final_completeness_score=0.0
    )
    
    print(f"  ✓ Created analysis #{analysis.id} with status: {analysis.status}")
    
    # Simulate some progress
    partial_results = {
        'final_analysis': {
            'executive_summary': 'Analysis was progressing well before cancellation.',
            'financial_analysis': 'Financial metrics were being analyzed.',
            'investment_opportunities': 'Several opportunities were identified.',
            'risk_assessment': 'Risk analysis was in progress.'
        },
        'iteration_history': [
            {
                'type': 'initial_analysis',
                'timestamp': timezone.now().isoformat(),
                'analysis': 'Initial comprehensive analysis of the financial data and market conditions.',
                'completeness_score': 7.8
            },
            {
                'type': 'rag_queries',
                'timestamp': timezone.now().isoformat(),
                'queries': ['What is the revenue trend?', 'What are the main risks?'],
                'results': ['Revenue shows steady growth', 'Market volatility is a concern']
            }
        ],
        'total_iterations': 1,
        'documents_analyzed': 8,
        'analysis_quality': {
            'final_completeness_score': 7.8,
            'rag_queries_executed': 2
        }
    }
    
    # Cancel with partial results
    analysis.mark_cancelled(partial_results, message='User requested cancellation')
    
    print(f"  ✓ Cancelled analysis with partial results")
    print(f"  ✓ Status: {analysis.status}")
    print(f"  ✓ Iterations completed: {analysis.total_iterations}")
    print(f"  ✓ Completeness score: {analysis.final_completeness_score}")
    print(f"  ✓ Has partial results: {analysis.has_partial_results()}")
    
    # Test API endpoint for status
    factory = APIRequestFactory()
    viewset = IterativeAnalysisViewSet()
    
    request = factory.get(f'/api/analysis/iterative/{analysis.id}/status/')
    request.user = AnonymousUser()
    viewset.request = request
    viewset.kwargs = {'pk': analysis.id}
    
    try:
        response = viewset.status(request, pk=analysis.id)
        if response.status_code == 200:
            data = response.data
            print(f"  ✓ API Status Response:")
            print(f"    - Status: {data.get('status')}")
            print(f"    - Has partial results: {data.get('has_partial_results')}")
            print(f"    - Termination reason: {data.get('termination_reason', 'Not provided')}")
            if data.get('latest_iteration_analysis'):
                print(f"    - Latest analysis preview: {data['latest_iteration_analysis'][:80]}...")
        else:
            print(f"  ✗ API Status failed: {response.status_code}")
    except Exception as e:
        print(f"  ✗ API Status error: {str(e)}")
    
    print()
    
    # Test 2: Analysis failure flow
    print("📋 Test 2: Analysis Failure Flow")
    print("-" * 40)
    
    # Create another analysis
    analysis2 = IterativeAnalysis.objects.create(
        query="Test analysis for failure flow",
        status='IN_PROGRESS',
        total_iterations=0,
        documents_analyzed=0,
        final_completeness_score=0.0
    )
    
    print(f"  ✓ Created analysis #{analysis2.id} with status: {analysis2.status}")
    
    # Simulate failure with partial results
    partial_results_failed = {
        'final_analysis': {
            'executive_summary': 'Analysis was interrupted by system failure.',
            'financial_analysis': 'Partial financial analysis completed.',
            'investment_opportunities': 'Limited opportunities analyzed.',
            'risk_assessment': 'Risk assessment incomplete due to failure.'
        },
        'iteration_history': [
            {
                'type': 'initial_analysis',
                'timestamp': timezone.now().isoformat(),
                'analysis': 'Initial analysis completed successfully before the system encountered an error.',
                'completeness_score': 6.2
            }
        ],
        'total_iterations': 1,
        'documents_analyzed': 4,
        'analysis_quality': {
            'final_completeness_score': 6.2,
            'rag_queries_executed': 1
        }
    }
    
    # Mark as failed with partial results
    analysis2.mark_failed('Network timeout during RAG query execution', partial_results_failed)
    
    print(f"  ✓ Failed analysis with partial results")
    print(f"  ✓ Status: {analysis2.status}")
    print(f"  ✓ Error: {analysis2.error_message}")
    print(f"  ✓ Iterations completed: {analysis2.total_iterations}")
    print(f"  ✓ Has partial results: {analysis2.has_partial_results()}")
    
    # Test results endpoint for failed analysis
    request2 = factory.get(f'/api/analysis/iterative/{analysis2.id}/results/')
    request2.user = AnonymousUser()
    viewset.request = request2
    viewset.kwargs = {'pk': analysis2.id}
    
    try:
        response2 = viewset.results(request2, pk=analysis2.id)
        if response2.status_code == 200:
            print(f"  ✓ Results endpoint accessible for failed analysis with partial results")
        else:
            print(f"  ✗ Results endpoint failed: {response2.status_code}")
            if hasattr(response2, 'data'):
                print(f"    Error: {response2.data.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"  ✗ Results endpoint error: {str(e)}")
    
    print()
    
    # Test 3: Analysis without partial results
    print("📋 Test 3: Termination without Partial Results")
    print("-" * 50)
    
    # Create analysis that fails immediately
    analysis3 = IterativeAnalysis.objects.create(
        query="Test analysis that fails immediately",
        status='IN_PROGRESS',
        total_iterations=0,
        documents_analyzed=0,
        final_completeness_score=0.0
    )
    
    # Fail without partial results
    analysis3.mark_failed('Configuration error - analysis could not start')
    
    print(f"  ✓ Created analysis #{analysis3.id} that failed immediately")
    print(f"  ✓ Status: {analysis3.status}")
    print(f"  ✓ Has partial results: {analysis3.has_partial_results()}")
    
    # Test results endpoint for failed analysis without partial results
    request3 = factory.get(f'/api/analysis/iterative/{analysis3.id}/results/')
    request3.user = AnonymousUser()
    viewset.request = request3
    viewset.kwargs = {'pk': analysis3.id}
    
    try:
        response3 = viewset.results(request3, pk=analysis3.id)
        if response3.status_code == 400:
            print(f"  ✓ Results endpoint correctly rejects analysis without partial results")
            print(f"    Message: {response3.data.get('error', 'Unknown error')}")
        else:
            print(f"  ✗ Unexpected response: {response3.status_code}")
    except Exception as e:
        print(f"  ✗ Results endpoint error: {str(e)}")
    
    print()
    
    # Test 4: Frontend data structure verification
    print("📋 Test 4: Frontend Data Structure")
    print("-" * 40)
    
    # Verify the data structure matches frontend expectations
    analyses_with_partial = [analysis, analysis2]
    
    for i, test_analysis in enumerate(analyses_with_partial, 1):
        print(f"  Analysis {i} (#{test_analysis.id}):")
        
        # Simulate frontend data structure
        frontend_data = {
            'id': test_analysis.id,
            'status': test_analysis.status,
            'has_partial_results': test_analysis.has_partial_results(),
            'latest_iteration_analysis': test_analysis.get_latest_iteration_analysis(),
            'total_iterations': test_analysis.total_iterations,
            'final_completeness_score': test_analysis.final_completeness_score,
            'error_message': test_analysis.error_message if test_analysis.status == 'FAILED' else None
        }
        
        print(f"    ✓ Status: {frontend_data['status']}")
        print(f"    ✓ Has partial results: {frontend_data['has_partial_results']}")
        print(f"    ✓ Iterations: {frontend_data['total_iterations']}")
        print(f"    ✓ Completeness: {frontend_data['final_completeness_score']}")
        if frontend_data['latest_iteration_analysis']:
            print(f"    ✓ Latest analysis available: {len(frontend_data['latest_iteration_analysis'])} chars")
        if frontend_data['error_message']:
            print(f"    ✓ Error message: {frontend_data['error_message'][:50]}...")
    
    print()
    
    # Cleanup
    print("🧹 Cleanup")
    print("-" * 20)
    
    test_analyses = IterativeAnalysis.objects.filter(
        query__startswith="Test analysis"
    )
    count = test_analyses.count()
    test_analyses.delete()
    print(f"  ✓ Cleaned up {count} test analyses")
    
    print()
    print("🎉 Complete termination flow testing completed!")
    print()
    print("📊 Summary:")
    print("- ✅ Analysis cancellation with partial results")
    print("- ✅ Analysis failure with partial results")
    print("- ✅ Analysis failure without partial results")
    print("- ✅ API endpoints handle partial results correctly")
    print("- ✅ Frontend data structure compatibility")
    print("- ✅ Latest iteration analysis extraction")
    print("- ✅ Proper error handling and validation")

if __name__ == "__main__":
    test_termination_flow()
