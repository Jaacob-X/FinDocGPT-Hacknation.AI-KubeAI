#!/usr/bin/env python3
"""
Script to check ALL documents from both Django database and Cognee registry.
This script shows the complete picture of your document storage.
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finDocGPT.settings')
django.setup()

from documents.models import Document
from services.cognee_service import CogneeService

def check_all_documents():
    """Check documents from both Django database and Cognee registry"""
    
    print("🔍 Complete Document Status Check")
    print("="*60)
    
    # Initialize Cognee service
    cognee_service = CogneeService()
    
    # Get Django documents (what frontend sees)
    django_docs = Document.objects.all().order_by('-filing_date')
    print(f"📊 Django Database (Frontend Source):")
    print(f"   Total documents: {django_docs.count()}")
    
    # Get Cognee registry documents
    cognee_docs = cognee_service._document_registry
    print(f"📊 Cognee Registry (Summary Source):")
    print(f"   Total documents: {len(cognee_docs)}")
    
    print(f"\n📋 Detailed Document Comparison:")
    print("-" * 60)
    
    # Check each Django document
    for i, doc in enumerate(django_docs, 1):
        print(f"{i}. {doc.company_name} {doc.form_type} ({doc.filing_date})")
        print(f"   Django ID: {doc.id} | Accession: {doc.accession_number}")
        print(f"   Status: {doc.status} | Size: {doc.content_size or 'Unknown'}")
        
        # Check if this document is in Cognee registry
        found_in_cognee = False
        has_summary = False
        cognee_fingerprint = None
        
        for fingerprint, cognee_doc in cognee_docs.items():
            cognee_metadata = cognee_doc.get('metadata', {})
            if cognee_metadata.get('accession_number') == doc.accession_number:
                found_in_cognee = True
                cognee_fingerprint = fingerprint[:8]
                has_summary = 'summary' in cognee_doc and cognee_doc['summary']
                break
        
        if found_in_cognee:
            status_icon = "✅" if has_summary else "⚠️"
            summary_status = "Has Summary" if has_summary else "No Summary"
            print(f"   Cognee: {status_icon} Found [{cognee_fingerprint}] - {summary_status}")
        else:
            print(f"   Cognee: ❌ Not found in registry")
        
        print()
    
    # Summary statistics
    django_count = django_docs.count()
    cognee_count = len(cognee_docs)
    
    # Count documents with summaries
    docs_with_summaries = 0
    for cognee_doc in cognee_docs.values():
        if 'summary' in cognee_doc and cognee_doc['summary']:
            docs_with_summaries += 1
    
    print("="*60)
    print("📈 Summary Statistics:")
    print(f"   Frontend shows: {django_count} documents")
    print(f"   Cognee registry has: {cognee_count} documents")
    print(f"   Documents with summaries: {docs_with_summaries}")
    print(f"   Documents missing from Cognee: {django_count - cognee_count}")
    print(f"   Documents needing summaries: {cognee_count - docs_with_summaries}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if django_count > cognee_count:
        print(f"   • {django_count - cognee_count} Django documents are not in Cognee registry")
        print(f"   • These documents may need to be reprocessed to add to RAG")
        
    if cognee_count > docs_with_summaries:
        print(f"   • {cognee_count - docs_with_summaries} Cognee documents need summaries")
        print(f"   • Run: python quick_add_summaries.py")
    
    if cognee_count == docs_with_summaries and django_count == cognee_count:
        print(f"   • ✅ All documents are properly processed with summaries!")
    
    return {
        'django_count': django_count,
        'cognee_count': cognee_count,
        'docs_with_summaries': docs_with_summaries
    }

def check_specific_documents():
    """Check specific document details"""
    
    print(f"\n🔍 Detailed Document Analysis:")
    print("-" * 60)
    
    # Get Django documents with STORED status
    stored_docs = Document.objects.filter(status='STORED')
    print(f"📊 Django documents with STORED status: {stored_docs.count()}")
    
    # Get Cognee service
    cognee_service = CogneeService()
    
    # Check each stored document
    for doc in stored_docs:
        print(f"\n📄 {doc.company_name} {doc.form_type}")
        print(f"   Accession: {doc.accession_number}")
        print(f"   Filing Date: {doc.filing_date}")
        print(f"   Content Size: {doc.content_size}")
        print(f"   Stored At: {doc.stored_at}")
        
        # Check in Cognee registry
        found_in_cognee = False
        for fingerprint, cognee_doc in cognee_service._document_registry.items():
            cognee_metadata = cognee_doc.get('metadata', {})
            if cognee_metadata.get('accession_number') == doc.accession_number:
                found_in_cognee = True
                has_full_content = 'full_content' in cognee_doc
                has_summary = 'summary' in cognee_doc and cognee_doc['summary']
                content_length = cognee_doc.get('content_length', 0)
                
                print(f"   Cognee Registry: ✅ Found [{fingerprint[:8]}]")
                print(f"   Full Content: {'✅' if has_full_content else '❌'} ({content_length:,} chars)")
                print(f"   Summary: {'✅' if has_summary else '❌'}")
                
                if has_summary:
                    summary = cognee_doc['summary']
                    exec_summary = summary.get('executive_summary', '')
                    if exec_summary:
                        preview = exec_summary[:100] + "..." if len(exec_summary) > 100 else exec_summary
                        print(f"   Summary Preview: {preview}")
                break
        
        if not found_in_cognee:
            print(f"   Cognee Registry: ❌ Not found")
            print(f"   Issue: Document marked as STORED but not in Cognee registry")

if __name__ == "__main__":
    stats = check_all_documents()
    check_specific_documents()
    
    print(f"\n" + "="*60)
    print(f"🎯 Next Steps:")
    
    if stats['django_count'] > stats['cognee_count']:
        print(f"1. Some documents are missing from Cognee registry")
        print(f"2. Check document processing pipeline")
        
    if stats['cognee_count'] > stats['docs_with_summaries']:
        print(f"1. Run: python quick_add_summaries.py")
        print(f"2. This will add summaries to {stats['cognee_count'] - stats['docs_with_summaries']} documents")
    
    print(f"3. Run: python check_all_documents.py (this script) to verify")
