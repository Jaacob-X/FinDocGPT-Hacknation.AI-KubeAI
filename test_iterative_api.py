#!/usr/bin/env python3
"""
Test script for the Iterative Analysis API

This script tests the new API endpoints for iterative analysis.
Run the Django server first, then run this script.
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_service_status():
    """Test if the iterative analysis service is available"""
    print("🔍 Testing service status...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/analysis/iterative/service_status/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service available: {data.get('available', False)}")
            print(f"   Documents available: {data.get('documents_available', 0)}")
            print(f"   Companies available: {data.get('companies_available', 0)}")
            return True
        else:
            print(f"❌ Service status check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking service status: {str(e)}")
        return False

def test_create_analysis():
    """Test creating a new iterative analysis"""
    print("\n🚀 Testing analysis creation...")
    
    test_query = "Analyze Apple Inc's investment potential based on recent SEC filings"
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analysis/iterative/",
            json={
                "query": test_query,
                "company_filter": "Apple Inc."
            }
        )
        
        if response.status_code == 201:
            data = response.json()
            analysis_id = data.get('id')
            print(f"✅ Analysis created successfully!")
            print(f"   ID: {analysis_id}")
            print(f"   Status: {data.get('status')}")
            print(f"   Estimated completion: {data.get('estimated_completion')}")
            return analysis_id
        else:
            print(f"❌ Analysis creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating analysis: {str(e)}")
        return None

def test_analysis_status(analysis_id):
    """Test checking analysis status"""
    print(f"\n📊 Testing analysis status (ID: {analysis_id})...")
    
    max_checks = 20  # Maximum number of status checks
    check_interval = 15  # Seconds between checks
    
    for check in range(max_checks):
        try:
            response = requests.get(f"{BASE_URL}/api/analysis/iterative/{analysis_id}/status/")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                progress = data.get('progress', {})
                
                print(f"   Check {check + 1}: Status = {status}")
                print(f"   Progress: {progress.get('total_iterations', 0)} iterations, " +
                      f"{progress.get('rag_queries_executed', 0)} RAG queries")
                
                if status == 'COMPLETED':
                    print(f"✅ Analysis completed!")
                    print(f"   Final recommendation: {data.get('final_recommendation', 'N/A')}")
                    print(f"   Confidence level: {data.get('confidence_level', 'N/A')}")
                    return True
                elif status == 'FAILED':
                    print(f"❌ Analysis failed: {data.get('error_message', 'Unknown error')}")
                    return False
                elif status == 'IN_PROGRESS':
                    print(f"   ⏳ Still processing... waiting {check_interval} seconds")
                    time.sleep(check_interval)
                else:
                    print(f"   ❓ Unknown status: {status}")
                    time.sleep(check_interval)
                    
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking status: {str(e)}")
            return False
    
    print(f"⏰ Analysis did not complete within {max_checks * check_interval} seconds")
    return False

def test_analysis_results(analysis_id):
    """Test getting complete analysis results"""
    print(f"\n📋 Testing analysis results (ID: {analysis_id})...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/analysis/iterative/{analysis_id}/results/")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Results retrieved successfully!")
            print(f"   Query: {data.get('query', 'N/A')[:50]}...")
            print(f"   Total iterations: {data.get('total_iterations', 0)}")
            print(f"   Documents analyzed: {data.get('documents_analyzed', 0)}")
            print(f"   Final completeness score: {data.get('final_completeness_score', 0)}/10")
            
            # Show final analysis summary
            final_analysis = data.get('final_analysis', {})
            if final_analysis:
                print(f"\n📊 Final Analysis Summary:")
                print(f"   Executive Summary: {final_analysis.get('executive_summary', 'N/A')[:100]}...")
                print(f"   Recommendation: {final_analysis.get('recommendation', 'N/A')}")
                print(f"   Confidence: {final_analysis.get('confidence_level', 'N/A')}")
            
            return True
        else:
            print(f"❌ Results retrieval failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting results: {str(e)}")
        return False

def test_iteration_details(analysis_id):
    """Test getting detailed iteration history"""
    print(f"\n🔍 Testing iteration details (ID: {analysis_id})...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/analysis/iterative/{analysis_id}/iteration_details/")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Iteration details retrieved!")
            print(f"   Total iterations: {data.get('total_iterations', 0)}")
            print(f"   Final score: {data.get('final_score', 0)}/10")
            
            iteration_history = data.get('iteration_history', [])
            print(f"\n📈 Iteration History ({len(iteration_history)} steps):")
            
            for iteration in iteration_history:
                iter_type = iteration.get('type', 'unknown')
                iter_num = iteration.get('iteration', 0)
                
                if iter_type == 'evaluation':
                    score = iteration.get('completeness_score', 0)
                    questions = iteration.get('questions_raised', 0)
                    print(f"   Iteration {iter_num}: Evaluation (Score: {score}/10, Questions: {questions})")
                elif iter_type == 'rag_queries':
                    queries = iteration.get('queries_executed', 0)
                    print(f"   Iteration {iter_num}: RAG Queries ({queries} executed)")
                else:
                    print(f"   Iteration {iter_num}: {iter_type.replace('_', ' ').title()}")
            
            return True
        else:
            print(f"❌ Iteration details retrieval failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting iteration details: {str(e)}")
        return False

def test_demo_analysis():
    """Test the demo analysis endpoint"""
    print("\n🎮 Testing demo analysis...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analysis/iterative/demo_analysis/",
            json={"query": "Quick demo analysis of available companies"}
        )
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Demo analysis started!")
            print(f"   ID: {data.get('id')}")
            print(f"   Demo mode: {data.get('demo_mode', False)}")
            return data.get('id')
        else:
            print(f"❌ Demo analysis failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting demo: {str(e)}")
        return None

def main():
    """Run all API tests"""
    print("🧪 FinDocGPT Iterative Analysis API Test")
    print("=" * 50)
    print(f"Testing against: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Service status
    if not test_service_status():
        print("\n❌ Service not available. Make sure:")
        print("   1. Django server is running (python manage.py runserver)")
        print("   2. AGENT_LLM_API_KEY is set")
        print("   3. Documents are loaded in the database")
        return
    
    # Test 2: Create analysis
    analysis_id = test_create_analysis()
    if not analysis_id:
        print("\n❌ Cannot proceed without successful analysis creation")
        return
    
    # Test 3: Monitor analysis status
    completed = test_analysis_status(analysis_id)
    if not completed:
        print(f"\n⚠️  Analysis may still be running. Check status manually:")
        print(f"   GET {BASE_URL}/api/analysis/iterative/{analysis_id}/status/")
        return
    
    # Test 4: Get results
    test_analysis_results(analysis_id)
    
    # Test 5: Get iteration details
    test_iteration_details(analysis_id)
    
    # Test 6: Demo analysis (optional)
    print("\n" + "=" * 50)
    demo_id = test_demo_analysis()
    if demo_id:
        print(f"   Demo analysis started with ID: {demo_id}")
        print(f"   Monitor at: {BASE_URL}/api/analysis/iterative/{demo_id}/status/")
    
    print("\n🎉 API testing complete!")
    print("\n📚 Available endpoints:")
    print(f"   POST   {BASE_URL}/api/analysis/iterative/")
    print(f"   GET    {BASE_URL}/api/analysis/iterative/{{id}}/status/")
    print(f"   GET    {BASE_URL}/api/analysis/iterative/{{id}}/results/")
    print(f"   GET    {BASE_URL}/api/analysis/iterative/{{id}}/iteration_details/")
    print(f"   GET    {BASE_URL}/api/analysis/iterative/service_status/")
    print(f"   POST   {BASE_URL}/api/analysis/iterative/demo_analysis/")

if __name__ == "__main__":
    main()
