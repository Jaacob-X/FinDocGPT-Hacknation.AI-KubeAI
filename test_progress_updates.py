#!/usr/bin/env python3
"""
Test script to verify that progress updates are working during iterative analysis
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_progress_updates():
    """Test that progress updates work during analysis"""
    print("🧪 Testing Progress Updates During Iterative Analysis")
    print("=" * 60)
    
    # Step 1: Create a new analysis
    print("\n1️⃣ Creating new analysis...")
    response = requests.post(
        f"{BASE_URL}/api/analysis/iterative/",
        json={
            "query": "Analyze Apple Inc's investment potential based on recent SEC filings",
            "company_filter": "Apple Inc."
        }
    )
    
    if response.status_code != 201:
        print(f"❌ Failed to create analysis: {response.status_code}")
        print(response.text)
        return
    
    analysis_data = response.json()
    analysis_id = analysis_data['id']
    print(f"✅ Analysis created with ID: {analysis_id}")
    
    # Step 2: Monitor progress updates
    print(f"\n2️⃣ Monitoring progress updates...")
    print("Time | Status | Iterations | RAG Queries | Score | History Length")
    print("-" * 70)
    
    previous_state = {}
    updates_detected = []
    
    for check in range(60):  # Monitor for up to 10 minutes (60 * 10 seconds)
        try:
            # Get status
            status_response = requests.get(f"{BASE_URL}/api/analysis/iterative/{analysis_id}/status/")
            if status_response.status_code != 200:
                print(f"❌ Failed to get status: {status_response.status_code}")
                break
                
            status_data = status_response.json()
            
            # Get iteration details
            details_response = requests.get(f"{BASE_URL}/api/analysis/iterative/{analysis_id}/iteration_details/")
            if details_response.status_code != 200:
                print(f"❌ Failed to get iteration details: {details_response.status_code}")
                break
                
            details_data = details_response.json()
            
            # Extract current state
            current_state = {
                'status': status_data.get('status'),
                'iterations': status_data.get('progress', {}).get('total_iterations', 0),
                'rag_queries': status_data.get('progress', {}).get('rag_queries_executed', 0),
                'score': status_data.get('progress', {}).get('final_completeness_score', 0),
                'history_length': len(details_data.get('iteration_history', []))
            }
            
            # Check for updates
            if current_state != previous_state:
                timestamp = time.strftime("%H:%M:%S")
                print(f"{timestamp} | {current_state['status']:11} | {current_state['iterations']:10} | {current_state['rag_queries']:11} | {current_state['score']:5.1f} | {current_state['history_length']:14}")
                
                # Record the update
                updates_detected.append({
                    'time': timestamp,
                    'state': current_state.copy()
                })
                
                previous_state = current_state.copy()
            
            # Stop if analysis is complete
            if current_state['status'] in ['COMPLETED', 'FAILED', 'CANCELLED']:
                print(f"\n✅ Analysis finished with status: {current_state['status']}")
                break
                
        except Exception as e:
            print(f"❌ Error during monitoring: {str(e)}")
            break
            
        time.sleep(10)  # Check every 10 seconds
    
    # Step 3: Analyze results
    print(f"\n3️⃣ Analysis Results:")
    print(f"Total updates detected: {len(updates_detected)}")
    
    if len(updates_detected) > 1:
        print("✅ Progress updates are working! Detected incremental changes:")
        for i, update in enumerate(updates_detected):
            print(f"  {i+1}. {update['time']} - {update['state']}")
    else:
        print("❌ No progress updates detected - the issue persists")
        
    return len(updates_detected) > 1

if __name__ == "__main__":
    success = test_progress_updates()
    if success:
        print("\n🎉 Test PASSED: Progress updates are working!")
    else:
        print("\n❌ Test FAILED: Progress updates are not working")
