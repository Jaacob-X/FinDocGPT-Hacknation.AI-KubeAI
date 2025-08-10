#!/usr/bin/env python3
"""
Demo script for the Iterative Analysis System

This script demonstrates the new iterative analysis architecture:
1. Document summaries provide context
2. Initial comprehensive analysis
3. Analysis completeness evaluation
4. Targeted RAG queries based on gaps
5. Analysis refinement with RAG results
6. Loop until complete

Run this script to see the iterative analysis in action.
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finDocGPT.settings')
django.setup()

from services.iterative_analysis_service import IterativeAnalysisService
from services.cognee_service import CogneeService
import json
from datetime import datetime

def print_section(title: str, content: str = "", separator: str = "="):
    """Print a formatted section"""
    print(f"\n{separator * 60}")
    print(f"{title}")
    print(f"{separator * 60}")
    if content:
        print(content)

def print_json_pretty(data: dict, max_length: int = 500):
    """Print JSON data in a readable format"""
    json_str = json.dumps(data, indent=2)
    if len(json_str) > max_length:
        print(json_str[:max_length] + "...")
    else:
        print(json_str)

def demo_iterative_analysis():
    """Demonstrate the iterative analysis system"""
    
    print_section("🚀 FinDocGPT Iterative Analysis Demo", 
                  "Demonstrating the new self-improving analysis architecture")
    
    # Initialize services
    print("\n📋 Initializing services...")
    analysis_service = IterativeAnalysisService()
    cognee_service = CogneeService()
    
    # Check if services are ready
    if not analysis_service.openai_client:
        print("❌ Error: OpenAI client not configured")
        print("Please set AGENT_LLM_API_KEY environment variable")
        return
    
    print("✅ Services initialized successfully")
    
    # Check available documents
    print_section("📊 Available Documents", separator="-")
    document_summaries = cognee_service.get_document_summaries()
    
    if not document_summaries:
        print("❌ No documents available in RAG database")
        print("Please run the document processing scripts first to add documents")
        return
    
    print(f"✅ Found {len(document_summaries)} documents in RAG database:")
    for i, doc in enumerate(document_summaries[:3], 1):  # Show first 3
        summary = doc.get('summary', {})
        print(f"\n{i}. {doc.get('company_name')} - {doc.get('form_type')} ({doc.get('filing_date')})")
        print(f"   Executive Summary: {summary.get('executive_summary', 'N/A')[:100]}...")
    
    if len(document_summaries) > 3:
        print(f"   ... and {len(document_summaries) - 3} more documents")
    
    # Demo queries
    demo_queries = [
        "Analyze Apple Inc's investment potential based on recent SEC filings",
        "What are the key financial metrics and growth opportunities for the companies in our database?",
        "Provide a comprehensive risk assessment for investment in the available companies"
    ]
    
    print_section("🎯 Demo Queries Available")
    for i, query in enumerate(demo_queries, 1):
        print(f"{i}. {query}")
    
    # Let user choose or use default
    print(f"\nUsing demo query 1 for demonstration...")
    selected_query = demo_queries[0]
    
    print_section("🔄 Starting Iterative Analysis", 
                  f"Query: {selected_query}")
    
    # Run the iterative analysis
    start_time = datetime.now()
    results = analysis_service.run_iterative_analysis(selected_query)
    end_time = datetime.now()
    
    if 'error' in results:
        print(f"❌ Analysis failed: {results['error']}")
        return
    
    # Display results
    duration = (end_time - start_time).total_seconds()
    print_section("✅ Analysis Completed", 
                  f"Duration: {duration:.1f} seconds")
    
    # Summary statistics
    print_section("📈 Analysis Summary", separator="-")
    print(f"Total Iterations: {results['total_iterations']}")
    print(f"Documents Analyzed: {results['documents_analyzed']}")
    print(f"RAG Queries Executed: {results['analysis_quality']['rag_queries_executed']}")
    print(f"Final Completeness Score: {results['analysis_quality']['final_completeness_score']}/10")
    
    # Final analysis
    final_analysis = results['final_analysis']
    print_section("💡 Final Investment Analysis", separator="-")
    
    if 'executive_summary' in final_analysis:
        print(f"Executive Summary: {final_analysis['executive_summary']}")
    
    if 'recommendation' in final_analysis:
        print(f"\n📊 Recommendation: {final_analysis['recommendation']}")
    
    if 'confidence_level' in final_analysis:
        print(f"Confidence Level: {final_analysis['confidence_level']}")
    
    # Show iteration details
    print_section("🔍 Iteration Details", separator="-")
    iteration_history = results['iteration_history']
    
    for iteration in iteration_history:
        iter_num = iteration.get('iteration', 0)
        iter_type = iteration.get('type', 'unknown')
        timestamp = iteration.get('timestamp', '')
        
        if iter_type == 'initial_analysis':
            print(f"\n📝 Iteration {iter_num}: Initial Analysis Generated")
            
        elif iter_type == 'evaluation':
            evaluation = iteration.get('evaluation', {})
            score = evaluation.get('completeness_score', 0)
            is_complete = evaluation.get('is_analysis_complete', False)
            questions = evaluation.get('specific_questions', [])
            
            print(f"\n🔍 Iteration {iter_num}: Completeness Evaluation")
            print(f"   Score: {score}/10")
            print(f"   Complete: {'Yes' if is_complete else 'No'}")
            print(f"   Questions Raised: {len(questions)}")
            
            if questions and len(questions) > 0:
                print(f"   Sample Question: {questions[0][:100]}...")
                
        elif iter_type == 'rag_queries':
            queries = iteration.get('queries', [])
            print(f"\n🔎 Iteration {iter_num}: RAG Queries Executed")
            print(f"   Queries: {len(queries)}")
            if queries:
                print(f"   Sample: {queries[0][:80]}...")
                
        elif iter_type == 'refined_analysis':
            print(f"\n✨ Iteration {iter_num}: Analysis Refined")
    
    # Demonstrate RAG tool functionality
    print_section("🛠️  RAG Tool Demonstration", separator="-")
    rag_tool = analysis_service.create_rag_query_tool("", "")
    
    print("Tool Definition:")
    tool_def = rag_tool["tool_definition"]
    print(f"Name: {tool_def['function']['name']}")
    print(f"Description: {tool_def['function']['description']}")
    
    # Test the tool
    print("\n🧪 Testing RAG Tool:")
    test_query = "What are Apple's key financial metrics?"
    print(f"Query: {test_query}")
    
    execute_function = rag_tool["execute_function"]
    tool_result = execute_function(test_query, "graph")
    
    print(f"Results: {len(tool_result.get('results', []))} items found")
    print(f"Relevant Documents: {len(tool_result.get('relevant_documents', []))}")
    
    if tool_result.get('results'):
        print(f"Sample Result: {str(tool_result['results'][0])[:150]}...")
    
    print_section("🎉 Demo Complete!", 
                  "The iterative analysis system successfully demonstrated:\n" +
                  "✅ Self-improving analysis through iteration\n" +
                  "✅ Gap identification and targeted RAG queries\n" +
                  "✅ Quality control and completeness evaluation\n" +
                  "✅ Integration with existing document summaries\n" +
                  "✅ LLM-callable RAG tools")

def demo_architecture_comparison():
    """Demonstrate the benefits of iterative vs multi-agent architecture"""
    
    print_section("🏗️  Architecture Comparison", 
                  "Iterative Analysis vs Multi-Agent Systems")
    
    comparison = {
        "Traditional Multi-Agent": {
            "approach": "Multiple specialized agents working in parallel",
            "pros": [
                "Specialized expertise per agent",
                "Parallel processing",
                "Clear separation of concerns"
            ],
            "cons": [
                "High cost (multiple model calls)",
                "Coordination complexity",
                "No self-improvement",
                "Fixed analysis depth"
            ]
        },
        "Iterative Analysis": {
            "approach": "Single sophisticated model with self-improvement loop",
            "pros": [
                "Self-correcting and improving",
                "Dynamic depth based on needs",
                "Cost-effective (single model)",
                "Quality assurance built-in",
                "Adaptive to different queries"
            ],
            "cons": [
                "Sequential processing",
                "Requires sophisticated prompting"
            ]
        }
    }
    
    for approach, details in comparison.items():
        print(f"\n📋 {approach}:")
        print(f"   Approach: {details['approach']}")
        print(f"   Pros: {', '.join(details['pros'])}")
        print(f"   Cons: {', '.join(details['cons'])}")
    
    print("\n🏆 Winner: Iterative Analysis")
    print("   Reasons: Better quality control, cost-effective, self-improving")

if __name__ == "__main__":
    try:
        print("🌟 Welcome to FinDocGPT Iterative Analysis Demo")
        print("=" * 60)
        
        # Check environment
        if not os.getenv('AGENT_LLM_API_KEY'):
            print("⚠️  Warning: AGENT_LLM_API_KEY not set")
            print("The demo will show the architecture but may not execute fully")
        
        # Run demos
        demo_iterative_analysis()
        demo_architecture_comparison()
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
