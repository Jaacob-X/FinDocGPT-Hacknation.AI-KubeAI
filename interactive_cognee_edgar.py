#!/usr/bin/env python3
"""
Interactive FinDocGPT Script
Fetch SEC documents via Edgar, store in Cognee RAG, and query for insights

Usage: python interactive_cognee_edgar.py
"""

import os
import sys
import django
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add the backend directory to Python path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finDocGPT.settings')
django.setup()

# Import services
from services.edgar_service import EdgarService
from services.cognee_service import CogneeService

class InteractiveFinDocGPT:
    """Interactive command-line interface for FinDocGPT"""
    
    def __init__(self):
        self.edgar_service = EdgarService()
        self.cognee_service = CogneeService()
        self.stored_documents = []
        self.session_stats = {
            'documents_fetched': 0,
            'documents_stored': 0,
            'queries_made': 0,
            'session_start': datetime.now()
        }
        # Check for existing persistent documents
        self._load_existing_documents()
    
    def _load_existing_documents(self):
        """Load existing documents from Cognee persistent storage"""
        try:
            # Test if Cognee has any existing data by doing a simple search
            test_results = self.cognee_service.search_context("documents", "chunks")
            if test_results:
                print(f"🔄 Found existing data in Cognee storage...")
                
                # Instead of creating fake documents from chunks, just indicate data exists
                # The chunks represent parts of documents, not separate documents
                print(f"📊 Found {len(test_results)} document chunks in storage")
                print("💡 Previous documents are available for querying via RAG")
                print("💡 Use 'View Stored Documents' to see current session documents only")
                print("💡 Use 'Complete Reset' if you want to clear all previous data")
                
                # Don't create fake document entries - this was causing confusion
                # Users can still query the existing data through RAG
                    
        except Exception as e:
            # Silently handle errors - this is just a convenience feature
            pass
    
    def print_banner(self):
        """Display welcome banner"""
        print("\n" + "="*70)
        print("🚀 FinDocGPT Interactive Console")
        print("📊 SEC Document Analysis with Cognee RAG")
        print("="*70)
        print("\nFeatures:")
        print("• Fetch real SEC filings via EdgarTools")
        print("• Store documents in Cognee knowledge graph")
        print("• Query documents using natural language")
        print("• Interactive document exploration")
        print("\n" + "-"*70)
    
    def print_menu(self):
        """Display main menu options"""
        print("\n📋 Main Menu:")
        print("1. 🔍 Search & Fetch SEC Documents")
        print("2. 📄 View Stored Documents")
        print("3. 💬 Query Documents (RAG)")
        print("4. 📊 Session Statistics")
        print("5. 🔧 Service Status")
        print("6. 🧹 Clear Cognee Data")
        print("7. 🔄 Complete Reset (Fix Issues)")
        print("8. 🔍 Debug RAG Results")
        print("9. 🔬 Diagnose RAG Accuracy Issues")
        print("10. 📋 Document Registry")
        print("11. 🔬 Diagnose Validation Content Issues")
        print("12. ❓ Help")
        print("13. 🚪 Exit")
        print("-"*50)
    
    def get_user_input(self, prompt: str, options: List[str] = None) -> str:
        """Get user input with optional validation"""
        while True:
            try:
                user_input = input(f"\n{prompt}: ").strip()
                if not user_input:
                    print("❌ Please enter a value.")
                    continue
                
                if options and user_input not in options:
                    print(f"❌ Please choose from: {', '.join(options)}")
                    continue
                
                return user_input
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                sys.exit(0)
    
    def search_and_fetch_documents(self):
        """Search for and fetch SEC documents"""
        print("\n" + "="*50)
        print("🔍 SEC Document Search & Fetch")
        print("="*50)
        
        # Get search parameters
        query = self.get_user_input("Enter company name or ticker (e.g., 'Apple Inc' or 'AAPL')")
        
        print("\nForm Types:")
        print("• 10-K: Annual Report")
        print("• 10-Q: Quarterly Report") 
        print("• 8-K: Current Report")
        print("• ALL: All form types")
        
        form_input = self.get_user_input("Select form types (10-K, 10-Q, 8-K, or ALL)", 
                                       ["10-K", "10-Q", "8-K", "ALL"])
        
        if form_input == "ALL":
            form_types = ["10-K", "10-Q", "8-K"]
        else:
            form_types = [form_input]
        
        try:
            limit = int(self.get_user_input("Number of documents to fetch (1-10)", 
                                          [str(i) for i in range(1, 11)]))
        except ValueError:
            limit = 3
        
        print(f"\n🔄 Searching for {query} documents...")
        
        try:
            # Search for filings
            filings = self.edgar_service.search_filings_by_query(query, limit=limit)
            
            if not filings:
                print("❌ No documents found for your search criteria.")
                return
            
            print(f"\n✅ Found {len(filings)} documents:")
            for i, filing in enumerate(filings, 1):
                print(f"  {i}. {filing['form']} - {filing['company_name']} ({filing['filing_date']})")
            
            # Confirm processing
            confirm = self.get_user_input("Process and store these documents in Cognee? (y/n)", 
                                        ["y", "n", "yes", "no"])
            
            if confirm.lower() not in ["y", "yes"]:
                print("❌ Operation cancelled.")
                return
            
            # Process each document
            print(f"\n🔄 Processing {len(filings)} documents...")
            successful_stores = 0
            
            for i, filing in enumerate(filings, 1):
                print(f"\n📄 Processing document {i}/{len(filings)}: {filing['form']} - {filing['company_name']}")
                
                # Fetch document content
                print("  🔄 Fetching content...")
                content_data = self.edgar_service.get_filing_content(
                    filing['accession_number'], 
                    filing['cik']
                )
                
                if not content_data:
                    print("  ❌ Failed to fetch content")
                    continue
                
                print(f"  ✅ Content fetched ({content_data['size']} characters)")
                
                # Prepare metadata
                metadata = {
                    'company_name': filing['company_name'],
                    'form_type': filing['form'],
                    'ticker': filing.get('ticker', ''),
                    'filing_date': str(filing['filing_date']),
                    'accession_number': filing['accession_number'],
                    'cik': filing['cik']
                }
                
                # Store in Cognee with duplicate checking
                print("  🔄 Storing in Cognee RAG...")
                result = self.cognee_service.add_document(content_data['content'], metadata)
                
                if result['success']:
                    print("  ✅ Successfully stored in Cognee")
                    if result.get('fingerprint'):
                        print(f"  🔐 Document fingerprint: {result['fingerprint'][:8]}...")
                    
                    self.stored_documents.append({
                        'metadata': metadata,
                        'content_size': content_data['size'],
                        'raw_content': content_data['content'],  # Store raw content for validation
                        'stored_at': datetime.now(),
                        'fingerprint': result.get('fingerprint', '')
                    })
                    successful_stores += 1
                    
                elif result.get('duplicate'):
                    print(f"  ⚠️  Duplicate document detected: {result['reason']}")
                    existing = result.get('existing_document', {})
                    print(f"      📄 Existing: {existing.get('company')} {existing.get('form_type')} from {existing.get('stored_at', 'unknown date')}")
                    print(f"      🔐 Fingerprint: {existing.get('fingerprint', 'unknown')}")
                    print("  ⏭️  Skipping duplicate - no storage needed")
                    
                    # Ask user if they want to proceed with duplicate
                    force_store = input("      🤔 Force store duplicate anyway? (y/n): ").strip().lower()
                    if force_store in ['y', 'yes']:
                        # Modify metadata to make it unique
                        modified_metadata = metadata.copy()
                        modified_metadata['accession_number'] = f"{metadata.get('accession_number', 'unknown')}_forced_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        print("      🔄 Force storing with modified metadata...")
                        force_result = self.cognee_service.add_document(content_data['content'], modified_metadata)
                        
                        if force_result['success']:
                            print("      ✅ Force stored successfully")
                            self.stored_documents.append({
                                'metadata': modified_metadata,
                                'content_size': content_data['size'],
                                'raw_content': content_data['content'],
                                'stored_at': datetime.now(),
                                'fingerprint': force_result.get('fingerprint', ''),
                                'forced_duplicate': True
                            })
                            successful_stores += 1
                        else:
                            print("      ❌ Force storage also failed")
                    
                else:
                    print(f"  ❌ Failed to store in Cognee: {result.get('error', 'Unknown error')}")
            
            # Update stats
            self.session_stats['documents_fetched'] += len(filings)
            self.session_stats['documents_stored'] += successful_stores
            
            print(f"\n🎉 Processing complete!")
            print(f"✅ Successfully stored {successful_stores}/{len(filings)} documents in Cognee")
            
        except Exception as e:
            print(f"❌ Error during document processing: {str(e)}")
    
    def view_stored_documents(self):
        """Display stored documents from current session and registry"""
        print("\n" + "="*50)
        print("📄 Stored Documents")
        print("="*50)
        
        # Show current session documents
        current_session_docs = [d for d in self.stored_documents if not d.get('is_from_previous_session')]
        
        if current_session_docs:
            print(f"📋 Current Session Documents ({len(current_session_docs)}):")
            for i, doc in enumerate(current_session_docs, 1):
                meta = doc['metadata']
                print(f"\n{i}. {meta['form_type']} - {meta['company_name']}")
                print(f"   📅 Filing Date: {meta['filing_date']}")
                print(f"   🏢 Ticker: {meta['ticker']}")
                print(f"   📊 Size: {doc['content_size']:,} characters")
                print(f"   🕒 Stored: {doc['stored_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                if doc.get('fingerprint'):
                    print(f"   🔐 Fingerprint: {doc['fingerprint'][:8]}...")
        else:
            print("📭 No documents stored in current session.")
        
        # Show documents from previous sessions (registry)
        try:
            registry_stats = self.cognee_service.get_registry_stats()
            
            if registry_stats.get('total_documents', 0) > 0:
                print(f"\n📚 Previous Session Documents ({registry_stats['total_documents']} total):")
                print("   💡 These documents are available for querying but not shown in detail")
                print("   💡 Use 'Document Registry' (option 10) for detailed view")
                
                # Show summary by company and form type
                companies = registry_stats.get('companies', [])
                form_types = registry_stats.get('form_types', [])
                
                if companies:
                    print(f"\n   🏢 Companies Available ({len(companies)}):")
                    for company in sorted(companies)[:5]:  # Show first 5
                        print(f"      • {company}")
                    if len(companies) > 5:
                        print(f"      ... and {len(companies) - 5} more")
                
                if form_types:
                    print(f"\n   📋 Form Types Available:")
                    for form_type in sorted(form_types):
                        print(f"      • {form_type}")
                
                # Show date range if available
                date_range = registry_stats.get('date_range', {})
                if date_range.get('earliest'):
                    print(f"\n   📅 Date Range: {date_range['earliest']} to {date_range['latest']}")
                
                print(f"\n   💬 Use option 3 to query these documents")
                print(f"   📋 Use option 10 for detailed registry view")
                
            elif not current_session_docs:
                print("\n💡 No documents found in current session or previous sessions.")
                print("💡 Use option 1 to search and fetch documents first.")
            else:
                print("\n💡 No documents from previous sessions found.")
                
        except Exception as e:
            print(f"\n⚠️  Error checking previous session documents: {str(e)}")
            if not current_session_docs:
                print("💡 Use option 1 to search and fetch documents first.")
    
    def query_documents(self):
        """Query stored documents using RAG"""
        print("\n" + "="*50)
        print("💬 Query Documents (RAG)")
        print("="*50)
        
        # Check if we have any documents (session or persistent)
        has_documents = bool(self.stored_documents)
        
        if not has_documents:
            # Try to detect if Cognee has any data by doing a test search
            print("🔍 Checking for existing documents in Cognee storage...")
            test_search = self.cognee_service.search_context("document", "chunks")
            if test_search:
                print("✅ Found existing documents in Cognee storage!")
                print("💡 You can query them even though they're from previous sessions.")
                has_documents = True
            else:
                print("📭 No documents found in Cognee storage.")
                print("💡 Use option 1 to search and fetch documents first.")
                return
        
        if self.stored_documents:
            print(f"📊 Available documents: {len(self.stored_documents)} (including {sum(1 for d in self.stored_documents if d.get('is_from_previous_session'))} from previous sessions)")
        else:
            print("📊 Querying persistent documents from Cognee storage")
        
        print("🤖 Ask questions about your stored documents!")
        print("Examples:")
        print("• 'What is the revenue growth for Apple?'")
        print("• 'What are the main risk factors?'")
        print("• 'Summarize the financial performance'")
        print("• 'What business segments does the company have?'")
        
        while True:
            query = input("\n💬 Your question (or 'back' to return): ").strip()
            
            if query.lower() in ['back', 'exit', 'quit']:
                break
            
            if not query:
                print("❌ Please enter a question.")
                continue
            
            print(f"\n🔍 Searching for: '{query}'")
            print("🔄 Processing...")
            
            # Detect if query is about a specific company
            detected_company = self.cognee_service.detect_company_from_query(query)
            if detected_company:
                print(f"🏢 Detected company: {detected_company}")
                print(f"📋 Filtering results to {detected_company} documents only")
                use_company_filter = True
            else:
                print("🌐 No specific company detected - searching all documents")
                use_company_filter = False
                
                # Ask user if they want to specify a company
                specify_company = input("🏢 Specify a company to filter results? (y/n): ").strip().lower()
                if specify_company in ['y', 'yes']:
                    company_input = input("Enter company name or ticker (e.g., 'Apple' or 'AAPL'): ").strip()
                    if company_input:
                        detected_company = company_input
                        use_company_filter = True
                        print(f"🎯 Filtering results to {detected_company} documents")
            
            try:
                # Use natural language search first
                print("\n💬 Natural Language Response:")
                print("-" * 40)
                
                # Choose search method based on company filtering
                if use_company_filter and detected_company:
                    natural_response = self.cognee_service.search_context_by_company(query, detected_company, "natural")
                    print(f"🔍 Searched {detected_company} documents only")
                else:
                    natural_response = self.cognee_service.search_context(query, "natural")
                    print("🔍 Searched all documents")
                
                if natural_response:
                    print(f"🤖 AI Response:")
                    for i, response in enumerate(natural_response[:2], 1):
                        # Clean up the response for better display
                        response_text = str(response)
                        if len(response_text) > 500:
                            response_text = response_text[:500] + "..."
                        print(f"\n{i}. {response_text}")
                else:
                    print("❌ No natural language response generated")
                
                # Get additional document chunks for detailed analysis
                print("\n📄 Document Analysis:")
                print("-" * 40)
                
                if use_company_filter and detected_company:
                    chunks = self.cognee_service.search_context_by_company(query, detected_company, "chunks")
                    print(f"🔍 Searched {detected_company} documents only")
                else:
                    chunks = self.cognee_service.search_context(query, "chunks")
                    print("🔍 Searched all documents")
                
                if chunks:
                    print(f"✅ Found {len(chunks)} relevant document sections")
                else:
                    print("❌ No additional document sections found")
                
                # Show raw chunks if user wants detailed information
                show_details = input("\n🔍 Show detailed document chunks? (y/n): ").strip().lower()
                if show_details in ['y', 'yes']:
                    if chunks:
                        print(f"\n📄 Found {len(chunks)} detailed document sections:")
                        for i, chunk in enumerate(chunks[:5], 1):  # Show up to 5 chunks
                            chunk_text = str(chunk).strip()
                            
                            # Skip empty or very short chunks
                            if len(chunk_text) < 50:
                                continue
                            
                            # Better formatting for display
                            if len(chunk_text) > 800:
                                # Show beginning and end of longer chunks
                                display_text = chunk_text[:400] + "\n\n[... content continues ...]\n\n" + chunk_text[-200:]
                            elif len(chunk_text) > 400:
                                display_text = chunk_text[:400] + "\n[... truncated]"
                            else:
                                display_text = chunk_text
                            
                            print(f"\n{i}. " + "="*60)
                            print(display_text)
                            print("="*60)
                    else:
                        print("❌ No detailed chunks available")
                
                self.session_stats['queries_made'] += 1
                
            except Exception as e:
                print(f"❌ Error during search: {str(e)}")
            
            print("\n" + "-" * 50)
    
    def _validate_insights_with_documents(self, query: str, insights: List[str]):
        """Validate insights against raw document content using LLM"""
        print("\n" + "="*60)
        print("🔬 LLM Insight Validation")
        print("="*60)
        
        # Get all available documents from registry + current session
        all_documents = self._get_all_available_documents_for_validation()
        
        if not all_documents:
            print("❌ No stored documents available for validation")
            print("💡 Use option 1 to fetch and store documents first")
            return
        
        # Check if validation is available
        service_info = self.cognee_service.get_service_info()
        if not service_info.get('openai_validation_enabled'):
            print("❌ OpenAI validation not available - check your API key configuration")
            return
        
        # Detect company from query for targeted validation
        detected_company = self.cognee_service.detect_company_from_query(query)
        if detected_company:
            print(f"🏢 Detected company: {detected_company}")
            print("📋 Will validate using documents from this company only")
            validation_documents = self._get_company_documents_for_validation(detected_company)
        else:
            print("🌐 No specific company detected - using all available documents")
            validation_documents = all_documents
        
        if not validation_documents:
            print("❌ No documents available for the detected company")
            return
        
        print(f"📊 Validating {len(insights)} insights against {len(validation_documents)} documents...")
        print("⚠️  This will use OpenAI API calls with FULL document content (no truncation)")
        print("⚠️  Processing may take 60-120 seconds per insight due to large document size")
        print("⚠️  Cost will be higher due to processing complete SEC filings")
        
        # Show document sources
        current_docs = sum(1 for d in validation_documents if d['source'] == 'current_session')
        registry_docs = sum(1 for d in validation_documents if d['source'] == 'registry')
        print(f"📋 Using {current_docs} current session documents + {registry_docs} registry documents")
        
        # Confirm validation
        confirm = input("\n🤖 Proceed with LLM validation? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Validation cancelled")
            return
        
        validation_results = []
        
        for i, insight in enumerate(insights[:2], 1):  # Limit to first 2 insights to save costs
            print(f"\n🔍 Validating insight {i}/{min(len(insights), 2)}...")
            print(f"💡 Insight: {str(insight)[:100]}...")
            
            # Use ALL available documents for the company - no token limits or truncation
            combined_content = ""
            relevant_docs = []
            
            for doc in validation_documents:
                doc_header = f"\n--- {doc['metadata']['form_type']} - {doc['metadata']['company_name']} ({doc['metadata']['filing_date']}) ---\n"
                
                # Use the COMPLETE raw document content - no truncation
                full_doc_content = str(doc['raw_content'])
                
                combined_content += doc_header + full_doc_content + "\n\n"
                relevant_docs.append(doc['metadata'])
                
                # Log the full size for transparency
                source_indicator = "📄" if doc['source'] == 'current_session' else "📚"
                has_full = "✅" if doc.get('has_full_content', True) else "⚠️ "
                print(f"  {source_indicator} {has_full} Added complete document: {len(full_doc_content):,} characters ({doc['source']})")
            
            print(f"📄 Using content from {len(relevant_docs)} documents ({len(combined_content):,} characters)")
            
            # Optional: Show preview of content being sent for validation
            show_content_preview = input("🔍 Show preview of content being sent for validation? (y/n): ").strip().lower()
            if show_content_preview in ['y', 'yes']:
                print(f"\n📋 Content Preview (first 800 characters):")
                print("-" * 60)
                print(combined_content[:800] + "..." if len(combined_content) > 800 else combined_content)
                print("-" * 60)
                input("Press Enter to continue with validation...")
            
            try:
                # Perform validation
                validation = self.cognee_service.validate_insight_with_llm(
                    insight=str(insight),
                    query=query,
                    raw_document_content=combined_content,
                    document_metadata={'documents': relevant_docs}
                )
                
                if validation.get('validation_available'):
                    print(f"✅ Validation completed!")
                    
                    # Display validation results
                    accuracy = validation.get('accuracy_score', 'N/A')
                    correctness = validation.get('correctness', 'Unknown')
                    completeness = validation.get('completeness', 'Unknown')
                    
                    print(f"\n📊 Validation Results:")
                    print(f"   🎯 Accuracy Score: {accuracy}/10")
                    print(f"   ✅ Correctness: {correctness}")
                    print(f"   📋 Completeness: {completeness}")
                    
                    # Show ALL issues without truncation
                    issues = validation.get('issues', [])
                    if issues:
                        print(f"\n⚠️  Issues Identified ({len(issues)}):")
                        for issue in issues:  # Show ALL issues
                            print(f"   • {issue}")
                    
                    # Show ALL supporting evidence without truncation
                    evidence = validation.get('supporting_evidence', [])
                    if evidence:
                        print(f"\n📝 Supporting Evidence:")
                        for ev in evidence:  # Show ALL evidence
                            print(f"   • {ev}")
                    
                    # Show FULL improved insight if available
                    improved = validation.get('improved_insight')
                    if improved and improved != str(insight):
                        print(f"\n💡 Improved Insight (FULL):")
                        print(f"   {improved}")  # Show complete improved insight
                    
                    # Show FULL explanation
                    explanation = validation.get('explanation', '')
                    if explanation:
                        print(f"\n📖 Explanation (FULL): {explanation}")
                    
                    validation_results.append(validation)
                    
                else:
                    print(f"❌ Validation failed: {validation.get('error', 'Unknown error')}")
            
            except Exception as e:
                print(f"❌ Error during validation: {str(e)}")
            
            # Pause between validations
            if i < min(len(insights), 2):
                print("\n" + "-" * 40)
        
        # Summary
        if validation_results:
            print(f"\n🏁 Validation Summary:")
            avg_accuracy = sum(v.get('accuracy_score', 0) for v in validation_results) / len(validation_results)
            print(f"   📊 Average Accuracy: {avg_accuracy:.1f}/10")
            
            correct_count = sum(1 for v in validation_results if v.get('correctness') == 'Yes')
            print(f"   ✅ Fully Correct: {correct_count}/{len(validation_results)} insights")
            
            print(f"\n💰 Estimated API Cost: ~${len(validation_results) * 0.10:.2f} (approximate - higher due to full document processing)")
        
        print("\n" + "="*60)
    
    def _get_all_available_documents_for_validation(self) -> List[Dict[str, Any]]:
        """Get all available documents from current session + registry for validation"""
        all_documents = []
        
        # Add current session documents (these should have full content)
        current_session_docs = [d for d in self.stored_documents if not d.get('is_from_previous_session')]
        for doc in current_session_docs:
            raw_content = doc.get('raw_content', '')
            print(f"📄 Current session doc: {doc['metadata'].get('company_name')} - {len(raw_content):,} chars")
            all_documents.append({
                'metadata': doc['metadata'],
                'raw_content': raw_content,
                'source': 'current_session',
                'content_size': doc.get('content_size', len(raw_content)),
                'has_full_content': True
            })
        
        # Add documents from registry
        try:
            registry = self.cognee_service._document_registry
            
            for fingerprint, doc_info in registry.items():
                # Skip if we already have this document from current session
                accession = doc_info['metadata'].get('accession_number', '')
                already_have = any(
                    d['metadata'].get('accession_number') == accession 
                    for d in current_session_docs 
                    if accession
                )
                
                if not already_have:
                    # Check what content is available in registry
                    has_full_content = 'full_content' in doc_info
                    full_content = doc_info.get('full_content', '')
                    content_preview = doc_info.get('content_preview', '')
                    
                    # Debug logging
                    company = doc_info['metadata'].get('company_name', 'Unknown')
                    print(f"📚 Registry doc: {company}")
                    print(f"    Has full_content: {has_full_content}")
                    print(f"    Full content length: {len(full_content):,} chars")
                    print(f"    Preview length: {len(content_preview):,} chars")
                    
                    # Use full content if available, otherwise warn and use preview
                    if has_full_content and len(full_content) > len(content_preview):
                        raw_content = full_content
                        print(f"    ✅ Using full content ({len(raw_content):,} chars)")
                    else:
                        raw_content = content_preview
                        print(f"    ⚠️  WARNING: Using content preview only ({len(raw_content):,} chars)")
                        print(f"    ⚠️  Full document content not available - validation may be incomplete")
                    
                    all_documents.append({
                        'metadata': doc_info['metadata'],
                        'raw_content': raw_content,
                        'source': 'registry',
                        'content_size': doc_info.get('content_length', 0),
                        'has_full_content': has_full_content and len(full_content) > len(content_preview)
                    })
        
        except Exception as e:
            print(f"⚠️  Error accessing registry for validation: {str(e)}")
        
        return all_documents
    
    def _get_company_documents_for_validation(self, company_name: str) -> List[Dict[str, Any]]:
        """Get all documents for a specific company for validation"""
        all_documents = self._get_all_available_documents_for_validation()
        
        if not company_name:
            return all_documents
        
        # Filter documents for the specific company
        company_documents = []
        company_lower = company_name.lower()
        
        for doc in all_documents:
            doc_company = doc['metadata'].get('company_name', '').lower()
            if company_lower in doc_company or doc_company in company_lower:
                company_documents.append(doc)
        
        return company_documents if company_documents else all_documents
    
    def _extract_financial_sections(self, document_content: str, query: str, insight: str) -> str:
        """Extract relevant financial sections from SEC document for validation"""
        try:
            # Convert to string and get reasonable length
            content = str(document_content)
            max_content_length = 12000  # Conservative limit for validation
            
            # Keywords to look for based on common financial queries
            financial_keywords = [
                'revenue', 'net sales', 'total revenues', 'net revenues',
                'income', 'earnings', 'profit', 'loss',
                'cash', 'assets', 'liabilities', 'equity',
                'operating', 'gross margin', 'operating margin',
                'quarter', 'fiscal year', 'year ended',
                'consolidated statements', 'financial statements',
                'results of operations', 'financial position'
            ]
            
            # Extract keywords from query and insight to focus search
            query_words = query.lower().split() if query else []
            insight_words = str(insight).lower().split() if insight else []
            search_terms = set(query_words + insight_words + financial_keywords)
            
            # Try to find financial statement sections
            sections_to_find = [
                'CONSOLIDATED STATEMENTS OF OPERATIONS',
                'CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME',
                'CONSOLIDATED BALANCE SHEETS',
                'CONSOLIDATED STATEMENTS OF CASH FLOWS',
                'RESULTS OF OPERATIONS',
                'FINANCIAL CONDITION',
                'LIQUIDITY AND CAPITAL RESOURCES'
            ]
            
            extracted_sections = []
            content_lower = content.lower()
            
            # Look for specific financial sections
            for section in sections_to_find:
                section_lower = section.lower()
                start_pos = content_lower.find(section_lower)
                
                if start_pos != -1:
                    # Extract section content (up to next major section or reasonable limit)
                    section_start = max(0, start_pos - 100)  # Include some context before
                    section_end = min(len(content), start_pos + 3000)  # Get substantial content
                    
                    # Try to find natural end of section
                    section_content = content[section_start:section_end]
                    
                    # Look for next major section as natural boundary
                    next_section_patterns = [
                        r'\n[A-Z][A-Z\s]+\n',  # All caps section headers
                        r'\nITEM \d+',  # SEC item headers
                        r'\nPART [IVX]+',  # SEC part headers
                    ]
                    
                    import re
                    for pattern in next_section_patterns:
                        match = re.search(pattern, section_content[500:])  # Skip first 500 chars
                        if match:
                            natural_end = 500 + match.start()
                            section_content = section_content[:natural_end]
                            break
                    
                    extracted_sections.append(f"\n=== {section} ===\n{section_content}")
            
            # If we found financial sections, use them
            if extracted_sections:
                combined_sections = '\n'.join(extracted_sections)
                if len(combined_sections) <= max_content_length:
                    return combined_sections
                else:
                    # Truncate but try to keep complete sections
                    return combined_sections[:max_content_length] + "\n\n[Additional sections truncated for length]"
            
            # Fallback: Look for content with high concentration of financial terms
            chunks = [content[i:i+2000] for i in range(0, len(content), 1500)]  # Overlapping chunks
            scored_chunks = []
            
            for i, chunk in enumerate(chunks):
                chunk_lower = chunk.lower()
                score = sum(1 for term in search_terms if term in chunk_lower)
                
                # Bonus for chunks with numbers (likely financial data)
                import re
                number_matches = len(re.findall(r'\$[\d,]+|\d+\.\d+%|\d{4}', chunk))
                score += number_matches * 2
                
                scored_chunks.append((score, i, chunk))
            
            # Sort by score and take the best chunks
            scored_chunks.sort(reverse=True, key=lambda x: x[0])
            
            best_content = ""
            for score, _, chunk in scored_chunks[:3]:  # Take top 3 chunks
                if len(best_content) + len(chunk) <= max_content_length:
                    best_content += chunk + "\n\n"
                else:
                    remaining_space = max_content_length - len(best_content)
                    if remaining_space > 500:  # Only add if substantial space remains
                        best_content += chunk[:remaining_space] + "\n[Truncated]"
                    break
            
            return best_content if best_content else content[:max_content_length]
            
        except Exception as e:
            print(f"⚠️  Error extracting financial sections: {str(e)}")
            # Fallback to middle section of document (often contains financial data)
            content_length = len(str(document_content))
            if content_length > 16000:
                # Skip first 8000 chars (cover page) and take middle section
                start = 8000
                end = min(content_length, start + 12000)
                return str(document_content)[start:end]
            else:
                return str(document_content)[:12000]
    
    def diagnose_rag_accuracy(self):
        """Comprehensive diagnosis of RAG accuracy issues"""
        print("\n" + "="*60)
        print("🔬 RAG Accuracy Diagnosis")
        print("="*60)
        
        if not self.stored_documents:
            print("❌ No documents available for diagnosis")
            print("💡 Use option 1 to fetch documents first")
            return
        
        print("This tool helps identify why RAG is producing inaccurate results.")
        print("We'll test the same query against different approaches.\n")
        
        # Get a test query
        test_queries = [
            "What is the revenue growth for Apple?",
            "What was Apple's total net sales in Q3 2025?",
            "How much did iPhone sales increase?",
            "What are the main business segments?"
        ]
        
        print("📋 Suggested test queries:")
        for i, query in enumerate(test_queries, 1):
            print(f"  {i}. {query}")
        
        query = input("\n💬 Enter test query (or number 1-4 for suggestions): ").strip()
        
        # Handle numbered selection
        if query.isdigit() and 1 <= int(query) <= 4:
            query = test_queries[int(query) - 1]
        
        print(f"\n🔍 Testing query: '{query}'")
        print("="*60)
        
        # Test 1: Raw document search
        print("\n1️⃣ MANUAL SEARCH IN RAW DOCUMENT")
        print("-" * 40)
        self._manual_document_search(query)
        
        # Test 2: Different RAG search types
        print("\n2️⃣ COGNEE RAG SEARCH TYPES")
        print("-" * 40)
        self._test_cognee_search_types(query)
        
        # Test 3: Document processing quality
        print("\n3️⃣ DOCUMENT PROCESSING QUALITY")
        print("-" * 40)
        self._analyze_document_processing()
        
        # Test 4: Recommendations
        print("\n4️⃣ RECOMMENDATIONS")
        print("-" * 40)
        self._provide_accuracy_recommendations()
    
    def _manual_document_search(self, query: str):
        """Manually search raw documents to find the correct answer"""
        try:
            query_lower = query.lower()
            search_terms = ['revenue', 'sales', 'growth', 'increase', 'billion', 'million']
            
            for doc in self.stored_documents[:1]:  # Test first document
                content = str(doc['raw_content'])
                
                # Find relevant sections manually
                lines = content.split('\n')
                relevant_lines = []
                
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if any(term in line_lower for term in search_terms):
                        # Include context lines
                        start_idx = max(0, i-2)
                        end_idx = min(len(lines), i+3)
                        context = lines[start_idx:end_idx]
                        relevant_lines.extend(context)
                
                if relevant_lines:
                    print(f"✅ Found {len(relevant_lines)} potentially relevant lines in raw document:")
                    
                    # Show most relevant excerpts
                    unique_lines = list(dict.fromkeys(relevant_lines))  # Remove duplicates
                    for line in unique_lines[:10]:  # Show first 10 unique lines
                        if line.strip() and any(term in line.lower() for term in search_terms):
                            print(f"   📄 {line.strip()}")
                    
                    if len(unique_lines) > 10:
                        print(f"   ... and {len(unique_lines) - 10} more lines")
                else:
                    print("❌ No relevant lines found with manual search")
                    print("💡 The query terms might not match the document content")
                    
        except Exception as e:
            print(f"❌ Error in manual search: {str(e)}")
    
    def _test_cognee_search_types(self, query: str):
        """Test different Cognee search types to see which works best"""
        search_types = [
            ("natural", "Natural Language"),
            ("chunks", "Document Chunks"), 
            ("insights", "Insights"),
            ("summaries", "Summaries")
        ]
        
        # Test company detection
        detected_company = self.cognee_service.detect_company_from_query(query)
        if detected_company:
            print(f"🏢 Detected company: {detected_company}")
            print("Testing both general and company-specific searches...")
        else:
            print("🌐 No company detected - testing general search only")
        
        best_results = []
        
        for search_type, description in search_types:
            try:
                print(f"\n🔍 Testing {description} ({search_type}):")
                
                # Test general search
                print(f"   📋 General Search:")
                results = self.cognee_service.search_context(query, search_type)
                self._analyze_search_results(results, "general", best_results, search_type)
                
                # Test company-specific search if company detected
                if detected_company:
                    print(f"   🏢 Company-Specific Search ({detected_company}):")
                    company_results = self.cognee_service.search_context_by_company(query, detected_company, search_type)
                    self._analyze_search_results(company_results, "company-specific", best_results, f"{search_type}_company")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
    
    def _analyze_search_results(self, results, search_label, best_results, search_type):
        """Analyze and display search results quality"""
        if results:
            print(f"      ✅ Found {len(results)} {search_label} results")
            
            # Analyze result quality
            for i, result in enumerate(results[:2], 1):
                result_str = str(result)
                
                # Check for financial data patterns
                import re
                dollar_amounts = re.findall(r'\$[\d,]+(?:\.\d+)?', result_str)
                percentages = re.findall(r'\d+(?:\.\d+)?%', result_str)
                
                quality_score = len(dollar_amounts) + len(percentages)
                
                print(f"      📊 Result {i}: {len(result_str)} chars, "
                      f"{len(dollar_amounts)} dollar amounts, "
                      f"{len(percentages)} percentages")
                
                if dollar_amounts or percentages:
                    print(f"         💰 Financial data: {dollar_amounts[:3]} {percentages[:3]}")
                    best_results.append((search_type, quality_score, result_str[:200]))
                
                # Show preview
                preview = result_str[:150] + "..." if len(result_str) > 150 else result_str
                print(f"         📄 Preview: {preview}")
        
        else:
            print(f"      ❌ No {search_label} results returned")
        
        # Recommend best search type
        if best_results:
            best_results.sort(key=lambda x: x[1], reverse=True)
            best_type = best_results[0][0]
            print(f"\n🏆 Best performing search type: {best_type}")
            print(f"   💡 Consider using this search type for better accuracy")
    
    def _analyze_document_processing(self):
        """Analyze how well documents were processed by Cognee"""
        if not self.stored_documents:
            print("❌ No documents to analyze")
            return
        
        doc = self.stored_documents[0]  # Analyze first document
        content = str(doc['raw_content'])
        
        print(f"📊 Document Analysis:")
        print(f"   📄 Original size: {len(content):,} characters")
        print(f"   🏢 Company: {doc['metadata']['company_name']}")
        print(f"   📋 Form: {doc['metadata']['form_type']}")
        
        # Check for financial statement sections
        financial_sections = [
            'CONSOLIDATED STATEMENTS OF OPERATIONS',
            'CONSOLIDATED BALANCE SHEETS', 
            'RESULTS OF OPERATIONS',
            'REVENUE',
            'NET SALES'
        ]
        
        found_sections = []
        for section in financial_sections:
            if section.lower() in content.lower():
                found_sections.append(section)
        
        print(f"   💼 Financial sections found: {len(found_sections)}")
        for section in found_sections:
            print(f"      ✅ {section}")
        
        if len(found_sections) < 3:
            print("   ⚠️  WARNING: Few financial sections detected")
            print("   💡 Document may not have been processed completely")
        
        # Check for data quality
        import re
        dollar_amounts = re.findall(r'\$[\d,]+', content)
        percentages = re.findall(r'\d+\.\d+%', content)
        
        print(f"   💰 Dollar amounts found: {len(dollar_amounts)}")
        print(f"   📈 Percentages found: {len(percentages)}")
        
        if len(dollar_amounts) < 10:
            print("   ⚠️  WARNING: Very few financial figures detected")
            print("   💡 Document content may be incomplete or poorly formatted")
    
    def _provide_accuracy_recommendations(self):
        """Provide specific recommendations to improve RAG accuracy"""
        print("💡 RECOMMENDATIONS TO IMPROVE RAG ACCURACY:")
        print()
        
        print("🔧 Immediate Actions:")
        print("   1. Try 'Complete Reset' (option 7) to clear corrupted data")
        print("   2. Re-fetch documents with option 1")
        print("   3. Use specific financial terms in queries")
        print("   4. Test different search types (chunks vs natural)")
        print()
        
        print("📊 Query Optimization:")
        print("   • Instead of: 'What is revenue growth?'")
        print("   • Try: 'What was the total net sales for Q3 2025 compared to Q3 2024?'")
        print("   • Be specific about time periods and metrics")
        print()
        
        print("🔍 Document Quality:")
        print("   • Ensure documents contain actual financial statements")
        print("   • 10-Q and 10-K forms should have numerical data")
        print("   • If accuracy remains low, the document processing may be flawed")
        print()
        
        print("🚨 When to be Concerned:")
        print("   • Accuracy consistently below 7/10")
        print("   • RAG returns qualitative descriptions instead of numbers")
        print("   • Manual document search finds data that RAG misses")
        print("   • Mathematical calculations are incorrect (like growth rates)")
    
    def view_document_registry(self):
        """View the document registry with duplicate tracking"""
        print("\n" + "="*50)
        print("📋 Document Registry")
        print("="*50)
        
        try:
            stats = self.cognee_service.get_registry_stats()
            
            if 'error' in stats:
                print(f"❌ Error accessing registry: {stats['error']}")
                return
            
            if stats['total_documents'] == 0:
                print("📭 No documents in registry")
                print("💡 Documents will be registered when you store them")
                return
            
            print(f"📊 Registry Statistics:")
            print(f"   📄 Total Documents: {stats['total_documents']}")
            print(f"   🏢 Companies: {len(stats['companies'])}")
            print(f"   📋 Form Types: {len(stats['form_types'])}")
            
            if stats['date_range']['earliest']:
                print(f"   📅 Date Range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
            
            print(f"\n🏢 Companies in Registry:")
            for company in sorted(stats['companies'])[:10]:  # Show first 10
                print(f"   • {company}")
            if len(stats['companies']) > 10:
                print(f"   ... and {len(stats['companies']) - 10} more")
            
            print(f"\n📋 Form Types:")
            for form_type in sorted(stats['form_types']):
                print(f"   • {form_type}")
            
            # Show recent storage activity
            if stats['storage_dates']:
                recent_dates = sorted(stats['storage_dates'])[-5:]  # Last 5
                print(f"\n🕒 Recent Storage Activity:")
                for date in recent_dates:
                    print(f"   • {date}")
            
            # Offer detailed view
            show_details = input("\n🔍 Show detailed document list? (y/n): ").strip().lower()
            if show_details in ['y', 'yes']:
                self._show_detailed_registry()
                
        except Exception as e:
            print(f"❌ Error viewing registry: {str(e)}")
    
    def _show_detailed_registry(self):
        """Show detailed document registry information"""
        try:
            # Access registry directly for detailed info
            registry = self.cognee_service._document_registry
            
            print(f"\n📄 Detailed Document Registry ({len(registry)} documents):")
            print("="*80)
            
            # Sort by storage date
            sorted_docs = sorted(
                registry.items(), 
                key=lambda x: x[1].get('stored_at', ''), 
                reverse=True
            )
            
            for i, (fingerprint, doc_info) in enumerate(sorted_docs[:20], 1):  # Show first 20
                metadata = doc_info['metadata']
                print(f"\n{i}. {metadata.get('company_name', 'Unknown')} - {metadata.get('form_type', 'Unknown')}")
                print(f"   📅 Filing Date: {metadata.get('filing_date', 'Unknown')}")
                print(f"   🏢 Ticker: {metadata.get('ticker', 'N/A')}")
                print(f"   📊 Content: {doc_info.get('content_length', 0):,} characters")
                print(f"   🔐 Fingerprint: {fingerprint[:16]}...")
                print(f"   🕒 Stored: {doc_info.get('stored_at', 'Unknown')}")
                
                if metadata.get('accession_number'):
                    print(f"   📋 Accession: {metadata['accession_number']}")
            
            if len(sorted_docs) > 20:
                print(f"\n... and {len(sorted_docs) - 20} more documents")
                
        except Exception as e:
            print(f"❌ Error showing detailed registry: {str(e)}")
    
    def debug_rag_results(self):
        """Debug RAG results to understand what's being returned"""
        print("\n" + "="*50)
        print("🔍 Debug RAG Results")
        print("="*50)
        
        print("This tool helps diagnose issues with RAG search results.")
        print("It will show you exactly what Cognee returns for different search types.")
        
        query = input("\n💬 Enter a test query (or press Enter for default): ").strip()
        if not query:
            query = "revenue growth"
        
        print(f"\n🔍 Testing query: '{query}'")
        print("🔄 Running different search types...")
        
        search_types = [
            ("natural", "Natural Language (GRAPH_COMPLETION)"),
            ("chunks", "Document Chunks"),
            ("insights", "Insights"),
            ("summaries", "Summaries")
        ]
        
        for search_type, description in search_types:
            print(f"\n{'='*40}")
            print(f"🔍 {description}")
            print(f"Search Type: {search_type}")
            print('='*40)
            
            try:
                results = self.cognee_service.search_context(query, search_type)
                
                if results:
                    print(f"✅ Found {len(results)} results")
                    
                    for i, result in enumerate(results[:2], 1):  # Show first 2 results
                        result_str = str(result)
                        print(f"\n📄 Result {i}:")
                        print(f"   Type: {type(result).__name__}")
                        print(f"   Length: {len(result_str)} characters")
                        
                        # Show raw result structure
                        if len(result_str) < 100:
                            print(f"   Raw: {result_str}")
                        else:
                            print(f"   Preview: {result_str[:200]}...")
                        
                        # Check if it looks like meaningful content
                        if len(result_str) > 50 and not result_str.startswith('<') and not result_str.startswith('{'):
                            print("   ✅ Looks like meaningful content")
                        else:
                            print("   ⚠️  May be object representation, not content")
                        
                        # Try to show attributes if it's an object
                        if hasattr(result, '__dict__'):
                            attrs = [attr for attr in dir(result) if not attr.startswith('_')][:5]
                            if attrs:
                                print(f"   Attributes: {', '.join(attrs)}")
                
                else:
                    print("❌ No results returned")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        print(f"\n🔧 Debugging Tips:")
        print("• If chunks show object representations instead of text, the content extraction needs improvement")
        print("• If natural language results are empty, check if documents were processed correctly")
        print("• If all searches fail, try clearing and re-adding documents")
        
        # Offer to test with a known working example
        test_simple = input("\n🧪 Test with a simple document? (y/n): ").strip().lower()
        if test_simple in ['y', 'yes']:
            self._test_simple_document()
    
    def _test_simple_document(self):
        """Test with a simple document to verify RAG functionality"""
        print("\n🧪 Testing with simple document...")
        
        test_content = """
        Apple Inc. reported strong financial results for Q3 2024.
        Revenue increased by 15% year-over-year to $85.8 billion.
        The company's iPhone sales grew by 12% driven by strong demand.
        Services revenue reached a new record of $24.2 billion.
        The company has $162.1 billion in cash and marketable securities.
        """
        
        test_metadata = {
            'company_name': 'Apple Inc',
            'form_type': 'Test Document',
            'filing_date': '2024-01-01',
            'ticker': 'AAPL',
            'accession_number': 'test_001'
        }
        
        print("📝 Adding test document to Cognee...")
        success = self.cognee_service.add_document(test_content, test_metadata)
        
        if success:
            print("✅ Test document added successfully")
            
            # Test search
            print("\n🔍 Testing search: 'What was Apple's revenue?'")
            results = self.cognee_service.search_context("What was Apple's revenue?", "chunks")
            
            if results:
                print(f"✅ Found {len(results)} results:")
                for i, result in enumerate(results[:2], 1):
                    print(f"\n{i}. {str(result)[:300]}...")
            else:
                print("❌ No results found - there may be an issue with document processing")
        else:
            print("❌ Failed to add test document")
    
    def diagnose_validation_content_issues(self):
        """Diagnose content availability issues for LLM validation"""
        print("\n" + "="*60)
        print("🔬 Validation Content Diagnosis")
        print("="*60)
        
        print("This tool helps diagnose why validation is only receiving truncated content.")
        print("We'll check what content is available from different sources.\n")
        
        # Get all available documents
        all_documents = self._get_all_available_documents_for_validation()
        
        if not all_documents:
            print("❌ No documents available for validation")
            print("💡 Use option 1 to fetch documents first")
            return
        
        print(f"📊 Found {len(all_documents)} documents for validation:\n")
        
        issues_found = []
        
        for i, doc in enumerate(all_documents, 1):
            metadata = doc['metadata']
            raw_content = doc.get('raw_content', '')
            source = doc.get('source', 'unknown')
            has_full = doc.get('has_full_content', False)
            
            print(f"{i}. {metadata.get('company_name')} - {metadata.get('form_type')}")
            print(f"   📅 Filing Date: {metadata.get('filing_date')}")
            print(f"   🔗 Source: {source}")
            print(f"   📊 Content Size: {len(raw_content):,} characters")
            print(f"   ✅ Has Full Content: {has_full}")
            
            # Check for issues
            if len(raw_content) < 10000:  # Less than 10KB is suspicious for SEC filings
                issues_found.append(f"Document {i}: Very small content ({len(raw_content):,} chars)")
                print(f"   ⚠️  WARNING: Content unusually small for SEC filing")
            
            if source == 'registry' and not has_full:
                issues_found.append(f"Document {i}: Registry missing full content")
                print(f"   ⚠️  WARNING: Registry doesn't have full content")
            
            # Show content preview
            if raw_content:
                preview = raw_content[:200].replace('\n', ' ').strip()
                print(f"   📄 Preview: {preview}...")
            else:
                issues_found.append(f"Document {i}: No content available")
                print(f"   ❌ No content available")
            
            print()
        
        # Summary and recommendations
        print("="*60)
        print("📋 DIAGNOSIS SUMMARY")
        print("="*60)
        
        if issues_found:
            print(f"⚠️  Found {len(issues_found)} issues:")
            for issue in issues_found:
                print(f"   • {issue}")
            
            print(f"\n💡 RECOMMENDATIONS:")
            
            registry_issues = [i for i in issues_found if 'registry' in i.lower()]
            if registry_issues:
                print("   🔄 Registry Issues:")
                print("      • Try 'Complete Reset' (option 7) to clear corrupted registry")
                print("      • Re-fetch documents using option 1")
                print("      • Registry may have size limits causing content truncation")
            
            small_content_issues = [i for i in issues_found if 'small' in i.lower()]
            if small_content_issues:
                print("   📄 Content Size Issues:")
                print("      • Documents may not have been fetched completely")
                print("      • Check internet connection and Edgar service status")
                print("      • Re-fetch specific documents")
            
            print(f"\n🔧 IMMEDIATE ACTIONS:")
            print("   1. Use current session documents for validation (these should have full content)")
            print("   2. If using registry documents, consider re-fetching them")
            print("   3. Check the CogneeService registry file size limits")
            
        else:
            print("✅ No content issues detected!")
            print("💡 All documents appear to have adequate content for validation")
            
            # Check if validation is still failing
            total_chars = sum(len(doc.get('raw_content', '')) for doc in all_documents)
            print(f"\n📊 Total content available: {total_chars:,} characters")
            
            if total_chars > 50000:  # Should be plenty for validation
                print("✅ Sufficient content available for LLM validation")
            else:
                print("⚠️  Total content may be insufficient for comprehensive validation")
        
        print(f"\n🔬 Technical Details:")
        print(f"   • Current session docs: {sum(1 for d in all_documents if d.get('source') == 'current_session')}")
        print(f"   • Registry docs: {sum(1 for d in all_documents if d.get('source') == 'registry')}")
        print(f"   • Docs with full content: {sum(1 for d in all_documents if d.get('has_full_content'))}")
        
        # Offer to test validation with current content
        test_validation = input("\n🧪 Test validation with current content? (y/n): ").strip().lower()
        if test_validation in ['y', 'yes']:
            self._test_validation_content(all_documents)
    
    def _test_validation_content(self, documents):
        """Test what content would actually be sent to LLM validation"""
        print("\n🧪 Testing Validation Content...")
        
        if not documents:
            print("❌ No documents to test")
            return
        
        # Simulate the validation content preparation
        combined_content = ""
        for doc in documents[:2]:  # Test first 2 documents
            doc_header = f"\n--- {doc['metadata']['form_type']} - {doc['metadata']['company_name']} ({doc['metadata']['filing_date']}) ---\n"
            full_doc_content = str(doc['raw_content'])
            combined_content += doc_header + full_doc_content + "\n\n"
        
        print(f"📊 Combined content length: {len(combined_content):,} characters")
        print(f"📄 Content preview (first 500 characters):")
        print("-" * 60)
        print(combined_content[:500] + "..." if len(combined_content) > 500 else combined_content)
        print("-" * 60)
        
        if len(combined_content) < 5000:
            print("⚠️  WARNING: Content seems too short for meaningful validation")
        else:
            print("✅ Content length appears adequate for validation")
    
    def show_session_stats(self):
        """Display session statistics"""
        print("\n" + "="*50)
        print("📊 Session Statistics")
        print("="*50)
        
        duration = datetime.now() - self.session_stats['session_start']
        
        print(f"⏰ Session Duration: {str(duration).split('.')[0]}")
        print(f"📄 Documents Fetched: {self.session_stats['documents_fetched']}")
        print(f"💾 Documents Stored: {self.session_stats['documents_stored']}")
        print(f"💬 Queries Made: {self.session_stats['queries_made']}")
        
        if self.stored_documents:
            print(f"\n📋 Current Session Documents:")
            for doc in self.stored_documents:
                meta = doc['metadata']
                print(f"  • {meta['form_type']} - {meta['company_name']} ({meta['ticker']})")
    
    def show_service_status(self):
        """Display service status"""
        print("\n" + "="*50)
        print("🔧 Service Status")
        print("="*50)
        
        # Check Edgar service
        print("🔍 Edgar Service: ✅ Ready")
        
        # Check Cognee service
        try:
            service_info = self.cognee_service.get_service_info()
            health = self.cognee_service.health_check()
            
            print(f"🧠 Cognee Service: {'✅ Healthy' if health['status'] == 'healthy' else '❌ Unhealthy'}")
            print(f"   Configuration: {'✅' if service_info['configured'] else '❌'}")
            print(f"   Cache Size: {service_info['cache_size']} items")
            
            print(f"\n🗂️ Database Providers:")
            for db_type, provider in service_info['providers'].items():
                print(f"   {db_type}: {provider}")
                
        except Exception as e:
            print(f"🧠 Cognee Service: ❌ Error - {str(e)}")
    
    def clear_cognee_data(self):
        """Clear Cognee data"""
        print("\n" + "="*50)
        print("🧹 Clear Cognee Data")
        print("="*50)
        
        print("⚠️  This will delete all stored documents and knowledge graphs from Cognee.")
        confirm = self.get_user_input("Are you sure? This cannot be undone (y/n)", 
                                    ["y", "n", "yes", "no"])
        
        if confirm.lower() not in ["y", "yes"]:
            print("❌ Operation cancelled.")
            return
        
        try:
            success = self.cognee_service.prune_data()
            if success:
                print("✅ Cognee data cleared successfully")
                self.stored_documents = []
                # Reset relevant stats
                self.session_stats['documents_stored'] = 0
            else:
                print("❌ Failed to clear Cognee data")
        except Exception as e:
            print(f"❌ Error clearing data: {str(e)}")
    
    def complete_reset(self):
        """Perform complete reset of Cognee system"""
        print("\n" + "="*50)
        print("🔄 Complete Cognee Reset")
        print("="*50)
        
        print("⚠️  This will completely remove all Cognee data and databases.")
        print("⚠️  This fixes file reference issues and database corruption.")
        print("⚠️  All stored documents will be permanently deleted.")
        confirm = self.get_user_input("Are you sure? This cannot be undone (y/n)", 
                                    ["y", "n", "yes", "no"])
        
        if confirm.lower() not in ["y", "yes"]:
            print("❌ Operation cancelled.")
            return
        
        try:
            success = self.cognee_service.complete_reset()
            if success:
                print("✅ Complete reset successful!")
                print("✅ Cognee is now ready for fresh documents")
                self.stored_documents = []
                # Reset relevant stats
                self.session_stats['documents_stored'] = 0
            else:
                print("❌ Reset failed - check the error messages above")
        except Exception as e:
            print(f"❌ Error during reset: {str(e)}")
    
    def show_help(self):
        """Display help information"""
        print("\n" + "="*50)
        print("❓ Help & Usage Guide")
        print("="*50)
        
        print("\n🚀 Quick Start:")
        print("1. Use option 1 to search and fetch SEC documents")
        print("2. Wait for documents to be processed and stored")
        print("3. Use option 3 to query your documents")
        
        print("\n💡 Tips:")
        print("• Be specific with company names (e.g., 'Apple Inc' vs 'Apple')")
        print("• 10-K reports contain the most comprehensive information")
        print("• 10-Q reports are good for quarterly updates")
        print("• Use natural language for queries")
        
        print("\n🔍 Example Queries:")
        print("• 'What was the revenue last quarter?'")
        print("• 'What are the main business segments?'")
        print("• 'List the key risk factors'")
        print("• 'How much cash does the company have?'")
        
        print("\n🔬 Validation Feature:")
        print("• Validate RAG insights against raw documents using LLM")
        print("• Get accuracy scores, correctness assessments, and improvements")
        print("• Identify potential errors or omissions in AI-generated insights")
        print("• Cost: ~$0.02 per insight validation")
        
        print("\n⚡ Performance:")
        print("• First document processing: 15-45 seconds")
        print("• Subsequent queries: 1-10 seconds (cached)")
        print("• Insight validation: 30-60 seconds per insight")
        print("• Larger documents take longer to process")
        
        print("\n🆘 Troubleshooting:")
        print("• If processing fails, try with fewer documents")
        print("• Check your internet connection for Edgar fetching")
        print("• Ensure your OpenAI API key is set in .env")
    
    def run(self):
        """Main interactive loop"""
        self.print_banner()
        
        # Quick service check
        if not self.cognee_service.is_configured:
            print("❌ Cognee service not properly configured!")
            print("💡 Please check your .env file and ensure LLM_API_KEY is set.")
            return
        
        print("✅ Services initialized successfully!")
        
        # Show existing document status
        if self.stored_documents:
            previous_count = sum(1 for d in self.stored_documents if d.get('is_from_previous_session'))
            if previous_count > 0:
                print(f"📚 Found {previous_count} documents from previous sessions - ready to query!")
        
        while True:
            try:
                self.print_menu()
                choice = self.get_user_input("Select an option (1-13)", 
                                           ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"])
                
                if choice == "1":
                    self.search_and_fetch_documents()
                elif choice == "2":
                    self.view_stored_documents()
                elif choice == "3":
                    self.query_documents()
                elif choice == "4":
                    self.show_session_stats()
                elif choice == "5":
                    self.show_service_status()
                elif choice == "6":
                    self.clear_cognee_data()
                elif choice == "7":
                    self.complete_reset()
                elif choice == "8":
                    self.debug_rag_results()
                elif choice == "9":
                    self.diagnose_rag_accuracy()
                elif choice == "10":
                    self.view_document_registry()
                elif choice == "11":
                    self.diagnose_validation_content_issues()
                elif choice == "12":
                    self.show_help()
                elif choice == "13":
                    print("\n👋 Thank you for using FinDocGPT!")
                    print("📊 Final Session Stats:")
                    self.show_session_stats()
                    break
                
                # Pause before showing menu again
                input("\n⏸️  Press Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {str(e)}")
                input("⏸️  Press Enter to continue...")

def main():
    """Main entry point"""
    try:
        app = InteractiveFinDocGPT()
        app.run()
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
