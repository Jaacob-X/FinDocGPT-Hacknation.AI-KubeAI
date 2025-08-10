#!/usr/bin/env python3
"""
Diagnostic script to understand why some documents are in Cognee registry and others aren't.
This helps identify processing pipeline issues.
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finDocGPT.settings')
django.setup()

from documents.models import Document
from services.cognee_service import CogneeService
from services.edgar_service import EdgarService

def diagnose_document_inconsistency():
    """Diagnose why some documents are in Cognee registry and others aren't"""
    
    print("🔍 Document Processing Inconsistency Diagnosis")
    print("="*60)
    
    # Initialize services
    cognee_service = CogneeService()
    
    # Get all documents from Django
    django_docs = list(Document.objects.all().order_by('-filing_date'))
    cognee_docs = cognee_service._document_registry
    
    print(f"📊 Overview:")
    print(f"   Django Database: {len(django_docs)} documents")
    print(f"   Cognee Registry: {len(cognee_docs)} documents")
    
    # Analyze document statuses
    status_counts = {}
    for doc in django_docs:
        status = doc.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n📈 Django Document Status Breakdown:")
    for status, count in status_counts.items():
        print(f"   {status}: {count} documents")
    
    # Detailed analysis
    print(f"\n🔍 Detailed Document Analysis:")
    print("-" * 60)
    
    in_both = 0
    only_in_django = 0
    only_in_cognee = 0
    
    # Check each Django document
    for i, doc in enumerate(django_docs, 1):
        found_in_cognee = False
        cognee_info = None
        
        # Look for this document in Cognee registry
        for fingerprint, cognee_doc in cognee_docs.items():
            cognee_metadata = cognee_doc.get('metadata', {})
            if cognee_metadata.get('accession_number') == doc.accession_number:
                found_in_cognee = True
                cognee_info = {
                    'fingerprint': fingerprint[:8],
                    'has_full_content': 'full_content' in cognee_doc,
                    'has_summary': 'summary' in cognee_doc and cognee_doc['summary'],
                    'content_length': cognee_doc.get('content_length', 0),
                    'stored_at': cognee_doc.get('stored_at', 'Unknown')
                }
                in_both += 1
                break
        
        if not found_in_cognee:
            only_in_django += 1
        
        # Display status
        status_icon = "✅" if found_in_cognee else "❌"
        print(f"{i:2d}. {status_icon} {doc.company_name} {doc.form_type} ({doc.filing_date})")
        print(f"     Django: ID={doc.id} | Status={doc.status} | Size={doc.content_size}")
        print(f"     Accession: {doc.accession_number}")
        
        if found_in_cognee:
            info = cognee_info
            content_status = "✅" if info['has_full_content'] else "❌"
            summary_status = "✅" if info['has_summary'] else "❌"
            print(f"     Cognee: [{info['fingerprint']}] | Content={content_status} | Summary={summary_status}")
            print(f"     Cognee Size: {info['content_length']:,} chars | Stored: {info['stored_at'][:10]}")
        else:
            print(f"     Cognee: ❌ Not found in registry")
            
            # Try to identify why it's missing
            reasons = []
            if doc.status != 'STORED':
                reasons.append(f"Django status is {doc.status} (not STORED)")
            if not doc.content_size:
                reasons.append("No content size recorded")
            if not doc.stored_at:
                reasons.append("No stored_at timestamp")
            
            if reasons:
                print(f"     Possible reasons: {', '.join(reasons)}")
        
        print()
    
    # Check for documents only in Cognee (orphaned)
    print(f"🔍 Checking for orphaned Cognee documents...")
    django_accessions = {doc.accession_number for doc in django_docs}
    
    for fingerprint, cognee_doc in cognee_docs.items():
        cognee_metadata = cognee_doc.get('metadata', {})
        accession = cognee_metadata.get('accession_number')
        
        if accession not in django_accessions:
            only_in_cognee += 1
            print(f"   🔄 Orphaned: {cognee_metadata.get('company_name')} {cognee_metadata.get('form_type')}")
            print(f"      Accession: {accession} | Not in Django database")
    
    # Summary statistics
    print(f"\n" + "="*60)
    print(f"📊 INCONSISTENCY ANALYSIS")
    print(f"="*60)
    print(f"✅ Documents in both systems: {in_both}")
    print(f"⚠️  Only in Django (missing from Cognee): {only_in_django}")
    print(f"🔄 Only in Cognee (orphaned): {only_in_cognee}")
    
    # Impact analysis
    print(f"\n💡 IMPACT ANALYSIS:")
    print(f"-" * 30)
    
    if only_in_django > 0:
        print(f"⚠️  IMPACT: {only_in_django} documents visible in frontend but NOT available for RAG queries")
        print(f"   - Users see these documents but can't query their content")
        print(f"   - Agents can't access these documents for analysis")
        print(f"   - Summary generation will fail for these documents")
    
    if only_in_cognee > 0:
        print(f"🔄 IMPACT: {only_in_cognee} documents in RAG but NOT visible in frontend")
        print(f"   - These documents can be queried but users don't see them")
        print(f"   - Potential data inconsistency")
    
    if in_both == len(django_docs) and only_in_cognee == 0:
        print(f"✅ GOOD: All systems are consistent!")
    
    # Recommendations
    print(f"\n🔧 RECOMMENDATIONS:")
    print(f"-" * 20)
    
    if only_in_django > 0:
        print(f"1. Run: python simple_add_summaries.py")
        print(f"   - This will process the {only_in_django} missing documents")
        print(f"   - Adds them to Cognee registry with summaries")
        
        print(f"2. Check processing pipeline:")
        print(f"   - Some documents may have failed during processing")
        print(f"   - Check Django logs for processing errors")
    
    if only_in_cognee > 0:
        print(f"3. Clean up orphaned Cognee documents:")
        print(f"   - {only_in_cognee} documents exist in Cognee but not Django")
        print(f"   - Consider removing these or adding them to Django")
    
    # Processing pipeline health check
    print(f"\n🏥 PROCESSING PIPELINE HEALTH:")
    print(f"-" * 35)
    
    stored_docs = [doc for doc in django_docs if doc.status == 'STORED']
    stored_in_cognee = 0
    
    for doc in stored_docs:
        for cognee_doc in cognee_docs.values():
            if cognee_doc.get('metadata', {}).get('accession_number') == doc.accession_number:
                stored_in_cognee += 1
                break
    
    if len(stored_docs) > 0:
        success_rate = (stored_in_cognee / len(stored_docs)) * 100
        print(f"📈 Pipeline Success Rate: {success_rate:.1f}%")
        print(f"   - {stored_in_cognee}/{len(stored_docs)} STORED documents are in Cognee")
        
        if success_rate < 100:
            print(f"   ⚠️  {len(stored_docs) - stored_in_cognee} STORED documents are missing from Cognee")
            print(f"   🔧 This indicates processing pipeline issues")
    
    return {
        'django_count': len(django_docs),
        'cognee_count': len(cognee_docs),
        'in_both': in_both,
        'only_in_django': only_in_django,
        'only_in_cognee': only_in_cognee,
        'status_counts': status_counts
    }

if __name__ == "__main__":
    diagnose_document_inconsistency()
