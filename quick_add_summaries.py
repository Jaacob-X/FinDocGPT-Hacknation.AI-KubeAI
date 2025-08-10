#!/usr/bin/env python3
"""
Quick script to add summaries to existing documents in FinDocGPT.
This is a simplified version for immediate use.

Usage:
    python quick_add_summaries.py
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.cognee_service import CogneeService

async def add_summaries_to_existing_docs():
    """Add summaries to existing documents"""
    
    print("🚀 Adding summaries to existing documents...")
    print("="*50)
    
    # Initialize service
    cognee_service = CogneeService()
    
    if not cognee_service.is_configured:
        print("❌ CogneeService not configured! Check your environment variables.")
        return
    
    # Check existing documents
    total_docs = len(cognee_service._document_registry)
    print(f"📄 Found {total_docs} documents in registry")
    
    if total_docs == 0:
        print("ℹ️  No documents found in registry. Make sure you have processed documents first.")
        return
    
    # Find documents without summaries
    docs_needing_summaries = []
    docs_with_summaries = 0
    
    for fingerprint, doc_info in cognee_service._document_registry.items():
        if 'summary' in doc_info and doc_info['summary']:
            docs_with_summaries += 1
        else:
            if 'full_content' in doc_info:
                docs_needing_summaries.append((fingerprint, doc_info))
            else:
                print(f"⚠️  Document {fingerprint[:8]} has no full_content - skipping")
    
    print(f"✅ Documents with summaries: {docs_with_summaries}")
    print(f"🔄 Documents needing summaries: {len(docs_needing_summaries)}")
    
    if len(docs_needing_summaries) == 0:
        print("🎉 All documents already have summaries!")
        return
    
    # Process each document
    successful = 0
    failed = 0
    
    for i, (fingerprint, doc_info) in enumerate(docs_needing_summaries, 1):
        metadata = doc_info.get('metadata', {})
        company = metadata.get('company_name', 'Unknown')
        form_type = metadata.get('form_type', 'Unknown')
        content_length = doc_info.get('content_length', 0)
        
        print(f"\n📄 Processing {i}/{len(docs_needing_summaries)}: {company} {form_type}")
        print(f"    ID: {fingerprint[:8]}")
        print(f"    Size: {content_length:,} characters")
        
        try:
            # Generate summary
            full_content = doc_info['full_content']
            summary = await cognee_service._generate_document_summary(full_content, metadata)
            
            if summary:
                # Add summary to document info
                doc_info['summary'] = summary
                doc_info['summary_generated_at'] = datetime.now().isoformat()
                
                print(f"    ✅ Summary generated successfully")
                successful += 1
                
                # Show a preview of the summary
                exec_summary = summary.get('executive_summary', '')
                if exec_summary:
                    preview = exec_summary[:100] + "..." if len(exec_summary) > 100 else exec_summary
                    print(f"    📝 Preview: {preview}")
            else:
                print(f"    ❌ Failed to generate summary")
                failed += 1
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            failed += 1
    
    # Save updated registry
    if successful > 0:
        print(f"\n💾 Saving updated registry...")
        cognee_service._save_document_registry()
        print(f"✅ Registry saved with {successful} new summaries")
    
    # Final report
    print(f"\n" + "="*50)
    print(f"📋 SUMMARY GENERATION COMPLETE")
    print(f"="*50)
    print(f"✅ Successfully processed: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📄 Total documents: {total_docs}")
    print(f"📊 Documents with summaries: {docs_with_summaries + successful}")
    
    # Verify the results
    if successful > 0:
        print(f"\n🔍 Verifying results...")
        updated_stats = cognee_service.get_registry_stats()
        print(f"✅ Registry now contains {updated_stats.get('documents_with_summaries', 0)} documents with summaries")

if __name__ == "__main__":
    asyncio.run(add_summaries_to_existing_docs())
