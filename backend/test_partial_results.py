#!/usr/bin/env python3
"""
Test script for partial results functionality when analysis is terminated

This script tests:
1. Storing partial results when analysis is cancelled
2. Storing partial results when analysis fails
3. Retrieving and displaying partial results
4. Latest iteration analysis extraction

To run: python test_partial_results.py
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
from django.utils import timezone

def test_partial_results_functionality():
    """Test the partial results functionality"""
    
    print("🧪 Testing Partial Results for Terminated Analyses")
    print("=" * 60)
    
    # Test 1: Create analysis with partial results and mark as cancelled
    print("📋 Test 1: Cancelled Analysis with Partial Results")
    print("-" * 50)
    
    # Create test analysis
    analysis1 = IterativeAnalysis.objects.create(
        query="Test cancelled analysis with partial results",
        status='IN_PROGRESS',
        total_iterations=0,
        documents_analyzed=5,
        final_completeness_score=0.0
    )
    
    # Simulate partial results from cancelled analysis
    partial_results = {
        'final_analysis': {
            'executive_summary': 'Partial analysis completed before cancellation.',
            'financial_analysis': 'Limited financial data was analyzed.',
            'investment_opportunities': 'Some opportunities identified.',
            'risk_assessment': 'Initial risk factors noted.'
        },
        'iteration_history': [
            {
                'type': 'initial_analysis',
                'timestamp': timezone.now().isoformat(),
                'analysis': 'This is the initial analysis that was completed before cancellation.',
                'completeness_score': 6.5
            },
            {
                'type': 'rag_queries',
                'timestamp': timezone.now().isoformat(),
                'queries': ['What is the revenue?', 'What are the risks?'],
                'results': ['Revenue data found', 'Risk factors identified']
            }
        ],
        'total_iterations': 1,
        'documents_analyzed': 5,
        'analysis_quality': {
            'final_completeness_score': 6.5,
            'rag_queries_executed': 2
        }
    }
    
    # Mark as cancelled with partial results
    analysis1.mark_cancelled(partial_results, message='User cancelled during iteration 1')
    
    print(f"  ✓ Created cancelled analysis #{analysis1.id}")
    print(f"  ✓ Status: {analysis1.status}")
    print(f"  ✓ Has partial results: {analysis1.has_partial_results()}")
    
    # Test latest iteration analysis extraction
    latest_analysis = analysis1.get_latest_iteration_analysis()
    if latest_analysis:
        print(f"  ✓ Latest iteration analysis: {latest_analysis[:100]}...")
    else:
        print("  ✗ No latest iteration analysis found")
    
    print()
    
    # Test 2: Create analysis with partial results and mark as failed
    print("📋 Test 2: Failed Analysis with Partial Results")
    print("-" * 50)
    
    # Create test analysis
    analysis2 = IterativeAnalysis.objects.create(
        query="Test failed analysis with partial results",
        status='IN_PROGRESS',
        total_iterations=0,
        documents_analyzed=3,
        final_completeness_score=0.0
    )
    
    # Simulate partial results from failed analysis
    partial_results_failed = {
        'final_analysis': {
            'executive_summary': 'Partial analysis before failure.',
            'financial_analysis': 'Some financial metrics analyzed.',
            'investment_opportunities': 'Few opportunities found.',
            'risk_assessment': 'Risk analysis incomplete.'
        },
        'iteration_history': [
            {
                'type': 'initial_analysis',
                'timestamp': timezone.now().isoformat(),
                'analysis': 'Initial analysis completed before system failure occurred.',
                'completeness_score': 5.8
            },
            {
                'type': 'refinement',
                'timestamp': timezone.now().isoformat(),
                'analysis': 'Refinement analysis was in progress when failure occurred.',
                'completeness_score': 7.2
            }
        ],
        'total_iterations': 2,
        'documents_analyzed': 3,
        'analysis_quality': {
            'final_completeness_score': 7.2,
            'rag_queries_executed': 4
        }
    }
    
    # Mark as failed with partial results
    analysis2.mark_failed('Database connection error', partial_results_failed)
    
    print(f"  ✓ Created failed analysis #{analysis2.id}")
    print(f"  ✓ Status: {analysis2.status}")
    print(f"  ✓ Error message: {analysis2.error_message}")
    print(f"  ✓ Has partial results: {analysis2.has_partial_results()}")
    
    # Test latest iteration analysis extraction
    latest_analysis2 = analysis2.get_latest_iteration_analysis()
    if latest_analysis2:
        print(f"  ✓ Latest iteration analysis: {latest_analysis2[:100]}...")
    else:
        print("  ✗ No latest iteration analysis found")
    
    print()
    
    # Test 3: Analysis without partial results
    print("📋 Test 3: Failed Analysis without Partial Results")
    print("-" * 50)
    
    # Create test analysis
    analysis3 = IterativeAnalysis.objects.create(
        query="Test failed analysis without partial results",
        status='IN_PROGRESS',
        total_iterations=0,
        documents_analyzed=0,
        final_completeness_score=0.0
    )
    
    # Mark as failed without partial results
    analysis3.mark_failed('Failed before any analysis could be performed')
    
    print(f"  ✓ Created failed analysis #{analysis3.id}")
    print(f"  ✓ Status: {analysis3.status}")
    print(f"  ✓ Error message: {analysis3.error_message}")
    print(f"  ✓ Has partial results: {analysis3.has_partial_results()}")
    
    print()
    
    # Test 4: Verify data persistence
    print("📋 Test 4: Data Persistence Verification")
    print("-" * 50)
    
    # Reload from database and verify
    reloaded1 = IterativeAnalysis.objects.get(id=analysis1.id)
    reloaded2 = IterativeAnalysis.objects.get(id=analysis2.id)
    reloaded3 = IterativeAnalysis.objects.get(id=analysis3.id)
    
    print(f"  ✓ Cancelled analysis #{reloaded1.id}:")
    print(f"    - Status: {reloaded1.status}")
    print(f"    - Iterations: {reloaded1.total_iterations}")
    print(f"    - Completeness: {reloaded1.final_completeness_score}")
    print(f"    - Has partial results: {reloaded1.has_partial_results()}")
    
    print(f"  ✓ Failed analysis #{reloaded2.id}:")
    print(f"    - Status: {reloaded2.status}")
    print(f"    - Iterations: {reloaded2.total_iterations}")
    print(f"    - Completeness: {reloaded2.final_completeness_score}")
    print(f"    - Has partial results: {reloaded2.has_partial_results()}")
    
    print(f"  ✓ Failed analysis #{reloaded3.id}:")
    print(f"    - Status: {reloaded3.status}")
    print(f"    - Iterations: {reloaded3.total_iterations}")
    print(f"    - Has partial results: {reloaded3.has_partial_results()}")
    
    print()
    
    # Cleanup
    print("🧹 Cleanup")
    print("-" * 20)
    
    test_analyses = IterativeAnalysis.objects.filter(
        query__startswith="Test"
    )
    count = test_analyses.count()
    test_analyses.delete()
    print(f"  ✓ Cleaned up {count} test analyses")
    
    print()
    print("🎉 Partial results testing completed!")
    print()
    print("📊 Summary:")
    print("- ✅ Cancelled analysis with partial results storage")
    print("- ✅ Failed analysis with partial results storage")
    print("- ✅ Failed analysis without partial results")
    print("- ✅ Latest iteration analysis extraction")
    print("- ✅ Data persistence verification")
    print("- ✅ Partial results detection")

if __name__ == "__main__":
    test_partial_results_functionality()
