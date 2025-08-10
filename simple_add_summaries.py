#!/usr/bin/env python3
"""
Simple script to add summaries to documents from Django database.
Handles Django async issues properly.
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

def main():
    """Main function to add summaries"""
    
    print("🚀 Adding Summaries from Django Database")
    print("="*50)
    
    # Initialize services
    cognee_service = CogneeService()
    edgar_service = EdgarService()
    
    if not cognee_service.is_configured:
        print("❌ CogneeService not configured!")
        return
    
    # Get all STORED documents from Django
    try:
        django_docs = list(Document.objects.filter(status='STORED').order_by('-filing_date'))
        print(f"📄 Found {len(django_docs)} STORED documents in Django database")
    except Exception as e:
        print(f"❌ Error accessing Django database: {e}")
        return
    
    if len(django_docs) == 0:
        print("ℹ️  No STORED documents found.")
        return
    
    # Show all documents
    print(f"\n📋 All Django Documents:")
    for i, doc in enumerate(django_docs, 1):
        print(f"   {i}. {doc.company_name} {doc.form_type} ({doc.filing_date})")
        print(f"      Accession: {doc.accession_number}")
        print(f"      Status: {doc.status} | Size: {doc.content_size}")
    
    # Check which documents need summaries
    docs_needing_summaries = []
    docs_already_have_summaries = 0
    
    print(f"\n🔍 Checking which documents have summaries...")
    
    for doc in django_docs:
        # Check if this document is in Cognee registry with summary
        found_with_summary = False
        
        for fingerprint, cognee_doc in cognee_service._document_registry.items():
            cognee_metadata = cognee_doc.get('metadata', {})
            if cognee_metadata.get('accession_number') == doc.accession_number:
                if 'summary' in cognee_doc and cognee_doc['summary']:
                    found_with_summary = True
                    docs_already_have_summaries += 1
                    print(f"   ✅ {doc.company_name} {doc.form_type} - Has summary")
                else:
                    print(f"   ⚠️  {doc.company_name} {doc.form_type} - In registry but no summary")
                break
        
        if not found_with_summary:
            docs_needing_summaries.append(doc)
            print(f"   ❌ {doc.company_name} {doc.form_type} - Needs summary")
    
    print(f"\n📊 Summary Status:")
    print(f"   ✅ Documents with summaries: {docs_already_have_summaries}")
    print(f"   🔄 Documents needing summaries: {len(docs_needing_summaries)}")
    
    if len(docs_needing_summaries) == 0:
        print("🎉 All documents already have summaries!")
        return
    
    # Ask user if they want to proceed
    response = input(f"\nProcess {len(docs_needing_summaries)} documents? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Process each document that needs a summary
    successful = 0
    failed = 0
    
    for i, doc in enumerate(docs_needing_summaries, 1):
        print(f"\n📄 Processing {i}/{len(docs_needing_summaries)}: {doc.company_name} {doc.form_type}")
        print(f"    Accession: {doc.accession_number}")
        
        try:
            # Check if document is already in Cognee registry (but without summary)
            cognee_doc = None
            cognee_fingerprint = None
            
            for fingerprint, existing_doc in cognee_service._document_registry.items():
                existing_metadata = existing_doc.get('metadata', {})
                if existing_metadata.get('accession_number') == doc.accession_number:
                    cognee_doc = existing_doc
                    cognee_fingerprint = fingerprint
                    break
            
            # Get document content
            if cognee_doc and 'full_content' in cognee_doc:
                # Use content from Cognee registry
                content = cognee_doc['full_content']
                print(f"    📥 Using content from Cognee registry ({len(content):,} chars)")
            else:
                # Fetch content from Edgar
                print(f"    📥 Fetching content from Edgar...")
                content_data = edgar_service.get_filing_content(doc.accession_number, doc.cik)
                
                if not content_data:
                    print(f"    ❌ Failed to fetch content from Edgar")
                    failed += 1
                    continue
                
                content = content_data['content']
                print(f"    📥 Content fetched from Edgar ({len(content):,} chars)")
            
            # Prepare metadata
            metadata = {
                'company_name': doc.company_name,
                'form_type': doc.form_type,
                'ticker': doc.ticker,
                'filing_date': str(doc.filing_date),
                'accession_number': doc.accession_number,
                'cik': doc.cik
            }
            
            # Generate summary using the sync wrapper
            print(f"    🤖 Generating summary...")
            try:
                summary = cognee_service._run_async(
                    cognee_service._generate_document_summary(content, metadata)
                )
            except Exception as summary_error:
                print(f"    ❌ Summary generation failed: {summary_error}")
                failed += 1
                continue
            
            if summary:
                # Update or create Cognee registry entry
                if cognee_doc:
                    # Update existing entry with summary
                    cognee_doc['summary'] = summary
                    cognee_doc['summary_generated_at'] = datetime.now().isoformat()
                    print(f"    ✅ Summary added to existing Cognee entry [{cognee_fingerprint[:8]}]")
                else:
                    # Create new Cognee registry entry
                    fingerprint = cognee_service._create_document_fingerprint(content, metadata)
                    doc_info = {
                        'fingerprint': fingerprint,
                        'metadata': metadata,
                        'summary': summary,
                        'content_length': len(content),
                        'content_preview': content[:2000],
                        'full_content': content,
                        'stored_at': datetime.now().isoformat(),
                        'content_hash': cognee_service._create_document_fingerprint(content, metadata),
                        'summary_generated_at': datetime.now().isoformat()
                    }
                    cognee_service._document_registry[fingerprint] = doc_info
                    print(f"    ✅ New Cognee registry entry created [{fingerprint[:8]}]")
                
                successful += 1
                
                # Show summary preview
                exec_summary = summary.get('executive_summary', '')
                if exec_summary:
                    preview = exec_summary[:80] + "..." if len(exec_summary) > 80 else exec_summary
                    print(f"    📝 Preview: {preview}")
            else:
                print(f"    ❌ Failed to generate summary")
                failed += 1
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            failed += 1
    
    # Save updated registry
    if successful > 0:
        print(f"\n💾 Saving updated Cognee registry...")
        try:
            cognee_service._save_document_registry()
            print(f"✅ Registry saved with {successful} new summaries")
        except Exception as e:
            print(f"❌ Error saving registry: {e}")
    
    # Final report
    print(f"\n" + "="*50)
    print(f"📋 SUMMARY GENERATION COMPLETE")
    print(f"="*50)
    print(f"✅ Successfully processed: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📄 Total Django documents: {len(django_docs)}")
    print(f"📊 Documents with summaries: {docs_already_have_summaries + successful}")
    
    # Verify results
    if successful > 0:
        print(f"\n🔍 Verifying results...")
        try:
            updated_stats = cognee_service.get_registry_stats()
            print(f"✅ Cognee registry now has {updated_stats.get('documents_with_summaries', 0)} documents with summaries")
            print(f"✅ Total documents in registry: {updated_stats.get('total_documents', 0)}")
        except Exception as e:
            print(f"⚠️  Could not verify results: {e}")

if __name__ == "__main__":
    main()
