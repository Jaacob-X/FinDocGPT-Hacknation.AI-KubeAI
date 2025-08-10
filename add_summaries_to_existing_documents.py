#!/usr/bin/env python3
"""
Script to add summaries to existing documents in the FinDocGPT system.

This script:
1. Loads existing documents from the registry
2. Identifies documents without summaries
3. Generates summaries for those documents using the complete document content
4. Updates the registry with the new summaries
5. Provides progress tracking and error handling

Usage:
    python add_summaries_to_existing_documents.py [--dry-run] [--force-regenerate]
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime
from typing import Dict, List, Any

# Add the backend directory to the path so we can import services
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import the CogneeService
from services.cognee_service import CogneeService

class SummaryBackfillService:
    """Service to add summaries to existing documents"""
    
    def __init__(self):
        """Initialize the service"""
        self.cognee_service = CogneeService()
        self.processed_count = 0
        self.error_count = 0
        self.skipped_count = 0
        
    def analyze_existing_documents(self) -> Dict[str, Any]:
        """Analyze existing documents to see which need summaries"""
        try:
            registry_stats = self.cognee_service.get_registry_stats()
            
            # Get all documents from registry
            documents_needing_summaries = []
            documents_with_summaries = []
            
            for fingerprint, doc_info in self.cognee_service._document_registry.items():
                metadata = doc_info.get('metadata', {})
                has_summary = 'summary' in doc_info and doc_info['summary']
                
                doc_summary = {
                    'fingerprint': fingerprint[:8],
                    'company_name': metadata.get('company_name', 'Unknown'),
                    'form_type': metadata.get('form_type', 'Unknown'),
                    'filing_date': metadata.get('filing_date', 'Unknown'),
                    'content_length': doc_info.get('content_length', 0),
                    'stored_at': doc_info.get('stored_at', 'Unknown'),
                    'has_summary': has_summary,
                    'has_full_content': 'full_content' in doc_info
                }
                
                if has_summary:
                    documents_with_summaries.append(doc_summary)
                else:
                    documents_needing_summaries.append(doc_summary)
            
            analysis = {
                'total_documents': len(self.cognee_service._document_registry),
                'documents_with_summaries': len(documents_with_summaries),
                'documents_needing_summaries': len(documents_needing_summaries),
                'documents_needing_summaries_list': documents_needing_summaries,
                'documents_with_summaries_list': documents_with_summaries,
                'registry_stats': registry_stats
            }
            
            return analysis
            
        except Exception as e:
            return {
                'error': str(e),
                'total_documents': 0
            }
    
    async def generate_summary_for_document(self, fingerprint: str, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary for a single document"""
        try:
            # Get the full content and metadata
            full_content = doc_info.get('full_content')
            metadata = doc_info.get('metadata', {})
            
            if not full_content:
                return {
                    'success': False,
                    'error': 'No full content available for this document'
                }
            
            print(f"  📄 Generating summary for {metadata.get('company_name', 'Unknown')} {metadata.get('form_type', 'Unknown')}")
            print(f"      Document size: {len(full_content):,} characters")
            
            # Generate summary using the complete document
            summary = await self.cognee_service._generate_document_summary(full_content, metadata)
            
            if summary:
                print(f"      ✅ Summary generated successfully")
                return {
                    'success': True,
                    'summary': summary,
                    'content_length': len(full_content)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to generate summary'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def backfill_summaries(self, dry_run: bool = False, force_regenerate: bool = False) -> Dict[str, Any]:
        """Backfill summaries for existing documents"""
        try:
            print("🔍 Analyzing existing documents...")
            analysis = self.analyze_existing_documents()
            
            if analysis.get('error'):
                return analysis
            
            print(f"\n📊 Analysis Results:")
            print(f"   Total documents: {analysis['total_documents']}")
            print(f"   Documents with summaries: {analysis['documents_with_summaries']}")
            print(f"   Documents needing summaries: {analysis['documents_needing_summaries']}")
            
            if analysis['documents_needing_summaries'] == 0 and not force_regenerate:
                print(f"\n✅ All documents already have summaries!")
                return analysis
            
            # Determine which documents to process
            documents_to_process = []
            
            if force_regenerate:
                # Process all documents
                for fingerprint, doc_info in self.cognee_service._document_registry.items():
                    if 'full_content' in doc_info:
                        documents_to_process.append((fingerprint, doc_info))
                print(f"\n🔄 Force regenerate mode: Processing all {len(documents_to_process)} documents")
            else:
                # Only process documents without summaries
                for fingerprint, doc_info in self.cognee_service._document_registry.items():
                    if 'summary' not in doc_info or not doc_info['summary']:
                        if 'full_content' in doc_info:
                            documents_to_process.append((fingerprint, doc_info))
                print(f"\n🔄 Processing {len(documents_to_process)} documents without summaries")
            
            if dry_run:
                print(f"\n🧪 DRY RUN MODE - No changes will be made")
                for fingerprint, doc_info in documents_to_process:
                    metadata = doc_info.get('metadata', {})
                    print(f"   Would process: {metadata.get('company_name', 'Unknown')} {metadata.get('form_type', 'Unknown')}")
                return analysis
            
            # Process documents
            print(f"\n🚀 Starting summary generation...")
            results = []
            
            for i, (fingerprint, doc_info) in enumerate(documents_to_process, 1):
                metadata = doc_info.get('metadata', {})
                print(f"\n📄 Processing {i}/{len(documents_to_process)}: {fingerprint[:8]}")
                
                # Generate summary
                result = await self.generate_summary_for_document(fingerprint, doc_info)
                
                if result['success']:
                    # Update the document registry with the new summary
                    doc_info['summary'] = result['summary']
                    doc_info['summary_generated_at'] = datetime.now().isoformat()
                    
                    self.processed_count += 1
                    print(f"      ✅ Summary added and registry updated")
                else:
                    self.error_count += 1
                    print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
                
                results.append({
                    'fingerprint': fingerprint[:8],
                    'company': metadata.get('company_name', 'Unknown'),
                    'form_type': metadata.get('form_type', 'Unknown'),
                    'success': result['success'],
                    'error': result.get('error')
                })
            
            # Save the updated registry
            if self.processed_count > 0:
                print(f"\n💾 Saving updated document registry...")
                self.cognee_service._save_document_registry()
                print(f"   ✅ Registry saved with {self.processed_count} new summaries")
            
            # Final summary
            final_summary = {
                'operation': 'backfill_summaries',
                'dry_run': dry_run,
                'force_regenerate': force_regenerate,
                'processed_successfully': self.processed_count,
                'errors': self.error_count,
                'skipped': self.skipped_count,
                'total_attempted': len(documents_to_process),
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            
            return final_summary
            
        except Exception as e:
            return {
                'error': str(e),
                'operation': 'backfill_summaries_failed'
            }
    
    def print_final_report(self, results: Dict[str, Any]):
        """Print a final report of the operation"""
        print(f"\n" + "="*60)
        print(f"📋 SUMMARY BACKFILL REPORT")
        print(f"="*60)
        
        if results.get('error'):
            print(f"❌ Operation failed: {results['error']}")
            return
        
        print(f"🕐 Timestamp: {results.get('timestamp', 'Unknown')}")
        print(f"🔧 Mode: {'DRY RUN' if results.get('dry_run') else 'LIVE'}")
        print(f"🔄 Force Regenerate: {results.get('force_regenerate', False)}")
        print(f"\n📊 Results:")
        print(f"   ✅ Successfully processed: {results.get('processed_successfully', 0)}")
        print(f"   ❌ Errors: {results.get('errors', 0)}")
        print(f"   ⏭️  Skipped: {results.get('skipped', 0)}")
        print(f"   📄 Total attempted: {results.get('total_attempted', 0)}")
        
        if results.get('results'):
            print(f"\n📋 Detailed Results:")
            for result in results['results']:
                status = "✅" if result['success'] else "❌"
                error_msg = f" ({result['error']})" if result.get('error') else ""
                print(f"   {status} {result['company']} {result['form_type']} [{result['fingerprint']}]{error_msg}")
        
        print(f"\n" + "="*60)

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Add summaries to existing documents')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without making changes')
    parser.add_argument('--force-regenerate', action='store_true', help='Regenerate summaries for all documents, even those that already have them')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze existing documents without processing')
    
    args = parser.parse_args()
    
    print("🚀 FinDocGPT Summary Backfill Tool")
    print("="*50)
    
    service = SummaryBackfillService()
    
    # Check if Cognee service is configured
    if not service.cognee_service.is_configured:
        print("❌ CogneeService is not properly configured!")
        print("   Please ensure your environment variables are set correctly.")
        return 1
    
    # Check if OpenAI client is available for summary generation
    if not service.cognee_service._openai_client:
        print("⚠️  Warning: OpenAI client not configured - will use basic summaries only")
    else:
        print("✅ OpenAI client configured - will generate AI summaries")
    
    if args.analyze_only:
        print(f"\n🔍 Analyzing existing documents only...")
        analysis = service.analyze_existing_documents()
        
        print(f"\n📊 Analysis Results:")
        print(f"   Total documents: {analysis.get('total_documents', 0)}")
        print(f"   Documents with summaries: {analysis.get('documents_with_summaries', 0)}")
        print(f"   Documents needing summaries: {analysis.get('documents_needing_summaries', 0)}")
        
        if analysis.get('documents_needing_summaries_list'):
            print(f"\n📋 Documents needing summaries:")
            for doc in analysis['documents_needing_summaries_list']:
                print(f"   • {doc['company_name']} {doc['form_type']} [{doc['fingerprint']}] ({doc['content_length']:,} chars)")
        
        return 0
    
    # Run the backfill operation
    results = await service.backfill_summaries(
        dry_run=args.dry_run,
        force_regenerate=args.force_regenerate
    )
    
    # Print final report
    service.print_final_report(results)
    
    # Return appropriate exit code
    if results.get('error'):
        return 1
    elif results.get('errors', 0) > 0:
        return 2  # Some documents failed
    else:
        return 0  # All successful

if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
