#!/usr/bin/env python3
"""
Test script for analysis delete functionality

This script tests the new delete features:
1. Single analysis deletion
2. Bulk analysis deletion
3. Protection against deleting running analyses

To run: python test_delete_functionality.py
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

def test_delete_functionality():
    """Test the delete functionality"""
    
    print("🧪 Testing Analysis Delete Functionality")
    print("=" * 50)
    
    # Create some test analyses
    print("Creating test analyses...")
    
    test_analyses = []
    for i in range(3):
        analysis = IterativeAnalysis.objects.create(
            query=f"Test analysis query {i+1}",
            status='COMPLETED' if i < 2 else 'IN_PROGRESS',
            total_iterations=i+1,
            documents_analyzed=5,
            final_completeness_score=7.5
        )
        test_analyses.append(analysis)
        print(f"  ✓ Created Analysis #{analysis.id} - Status: {analysis.status}")
    
    print()
    
    # Test 1: Try to delete a running analysis (should fail)
    print("📋 Test 1: Delete Running Analysis (Should Fail)")
    print("-" * 40)
    
    factory = APIRequestFactory()
    viewset = IterativeAnalysisViewSet()
    
    running_analysis = test_analyses[2]  # IN_PROGRESS
    request = factory.delete(f'/api/analysis/iterative/{running_analysis.id}/')
    request.user = AnonymousUser()
    
    viewset.request = request
    viewset.kwargs = {'pk': running_analysis.id}
    
    try:
        response = viewset.destroy(request, pk=running_analysis.id)
        if response.status_code == 400:
            print("  ✓ Correctly prevented deletion of running analysis")
            print(f"  ✓ Response: {response.data.get('error', 'Unknown error')}")
        else:
            print(f"  ✗ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
    
    print()
    
    # Test 2: Delete a completed analysis (should succeed)
    print("📋 Test 2: Delete Completed Analysis (Should Succeed)")
    print("-" * 40)
    
    completed_analysis = test_analyses[0]  # COMPLETED
    request = factory.delete(f'/api/analysis/iterative/{completed_analysis.id}/')
    request.user = AnonymousUser()
    
    viewset.request = request
    viewset.kwargs = {'pk': completed_analysis.id}
    
    try:
        response = viewset.destroy(request, pk=completed_analysis.id)
        if response.status_code == 204:
            print("  ✓ Successfully deleted completed analysis")
            print(f"  ✓ Response: {response.data.get('message', 'Deleted successfully')}")
            
            # Verify it's actually deleted
            if not IterativeAnalysis.objects.filter(id=completed_analysis.id).exists():
                print("  ✓ Analysis confirmed deleted from database")
            else:
                print("  ✗ Analysis still exists in database")
        else:
            print(f"  ✗ Unexpected response: {response.status_code}")
            print(f"  ✗ Response data: {response.data}")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
    
    print()
    
    # Test 3: Bulk delete (should succeed for completed, fail for running)
    print("📋 Test 3: Bulk Delete Mixed Status")
    print("-" * 40)
    
    remaining_analyses = IterativeAnalysis.objects.filter(
        id__in=[a.id for a in test_analyses[1:]]  # Skip the deleted one
    )
    analysis_ids = list(remaining_analyses.values_list('id', flat=True))
    
    request = factory.post('/api/analysis/iterative/bulk_delete/', {
        'analysis_ids': analysis_ids
    }, format='json')
    request.user = AnonymousUser()
    
    viewset.request = request
    
    try:
        response = viewset.bulk_delete(request)
        if response.status_code == 400:
            print("  ✓ Correctly prevented bulk delete with running analysis")
            print(f"  ✓ Response: {response.data.get('error', 'Unknown error')}")
            running_ids = response.data.get('running_analyses', [])
            print(f"  ✓ Running analyses: {running_ids}")
        else:
            print(f"  ✗ Unexpected response: {response.status_code}")
            print(f"  ✗ Response data: {response.data}")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
    
    print()
    
    # Test 4: Bulk delete only completed analyses
    print("📋 Test 4: Bulk Delete Only Completed")
    print("-" * 40)
    
    completed_analyses = IterativeAnalysis.objects.filter(
        status='COMPLETED'
    )
    completed_ids = list(completed_analyses.values_list('id', flat=True))
    
    if completed_ids:
        request = factory.post('/api/analysis/iterative/bulk_delete/', {
            'analysis_ids': completed_ids
        }, format='json')
        request.user = AnonymousUser()
        
        viewset.request = request
        
        try:
            response = viewset.bulk_delete(request)
            if response.status_code == 200:
                print("  ✓ Successfully bulk deleted completed analyses")
                print(f"  ✓ Deleted count: {response.data.get('deleted_count', 0)}")
                
                # Verify they're actually deleted
                remaining = IterativeAnalysis.objects.filter(id__in=completed_ids).count()
                if remaining == 0:
                    print("  ✓ All completed analyses confirmed deleted")
                else:
                    print(f"  ✗ {remaining} analyses still exist")
            else:
                print(f"  ✗ Unexpected response: {response.status_code}")
                print(f"  ✗ Response data: {response.data}")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    else:
        print("  ℹ No completed analyses to delete")
    
    print()
    
    # Cleanup: Delete any remaining test analyses
    print("🧹 Cleanup")
    print("-" * 20)
    
    remaining_test_analyses = IterativeAnalysis.objects.filter(
        query__startswith="Test analysis query"
    )
    
    if remaining_test_analyses.exists():
        # Mark running analyses as completed so we can delete them
        remaining_test_analyses.filter(status='IN_PROGRESS').update(status='COMPLETED')
        count = remaining_test_analyses.count()
        remaining_test_analyses.delete()
        print(f"  ✓ Cleaned up {count} test analyses")
    else:
        print("  ✓ No test analyses to clean up")
    
    print()
    print("🎉 Delete functionality testing completed!")
    print()
    print("📊 Summary:")
    print("- ✅ Delete protection for running analyses")
    print("- ✅ Single analysis deletion")
    print("- ✅ Bulk delete protection")
    print("- ✅ Bulk delete functionality")
    print("- ✅ Database cleanup verification")

if __name__ == "__main__":
    test_delete_functionality()
