#!/usr/bin/env python3
"""
Script to check the status of document summaries in FinDocGPT.
"""

import os
import sys
import json

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.cognee_service import CogneeService

def check_summaries():
    """Check the status of document summaries"""
    
    print("🔍 Checking Document Summaries Status")
    print("="*50)
    
    # Initialize service
    cognee_service = CogneeService()
    
    if not cognee_service.is_configured:
        print("❌ CogneeService not configured!")
        return
    
    # Get registry stats
    stats = cognee_service.get_registry_stats()
    processing_stats = cognee_service.get_document_processing_stats()
    
    print(f"📊 Registry Statistics:")
    print(f"   Total documents: {stats.get('total_documents', 0)}")
    print(f"   Documents with summaries: {stats.get('documents_with_summaries', 0)}")
    print(f"   Companies: {len(stats.get('companies', []))}")
    print(f"   Form types: {stats.get('form_types', [])}")
    
    print(f"\n📈 Processing Statistics:")
    print(f"   AI summaries: {processing_stats.get('documents_with_ai_summaries', 0)}")
    print(f"   Basic summaries: {processing_stats.get('documents_with_basic_summaries', 0)}")
    print(f"   Average document size: {processing_stats.get('average_document_size', 0):,} characters")
    print(f"   Largest document: {processing_stats.get('largest_document_processed', 0):,} characters")
    
    # Get detailed document list
    summaries = cognee_service.get_document_summaries()
    
    if summaries:
        print(f"\n📋 Document Details:")
        for i, doc in enumerate(summaries, 1):
            company = doc.get('company_name', 'Unknown')
            form_type = doc.get('form_type', 'Unknown')
            filing_date = doc.get('filing_date', 'Unknown')
            content_length = doc.get('content_length', 0)
            fingerprint = doc.get('fingerprint', 'Unknown')
            
            summary_info = doc.get('summary', {})
            has_summary = bool(summary_info)
            
            status = "✅" if has_summary else "❌"
            print(f"   {i}. {status} {company} {form_type} ({filing_date})")
            print(f"      ID: {fingerprint} | Size: {content_length:,} chars")
            
            if has_summary:
                exec_summary = summary_info.get('executive_summary', '')
                if exec_summary:
                    preview = exec_summary[:80] + "..." if len(exec_summary) > 80 else exec_summary
                    print(f"      Summary: {preview}")
            
            print()
    
    # Check service configuration
    service_info = cognee_service.get_service_info()
    doc_processing = service_info.get('document_processing', {})
    
    print(f"⚙️  Service Configuration:")
    print(f"   Summary generation: {doc_processing.get('summary_generation', 'Unknown')}")
    print(f"   Summary purpose: {doc_processing.get('summary_purpose', 'Unknown')}")
    print(f"   RAG storage: {doc_processing.get('rag_storage', 'Unknown')}")
    print(f"   Processing method: {doc_processing.get('processing_method', 'Unknown')}")
    
    return stats

if __name__ == "__main__":
    check_summaries()
