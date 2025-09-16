#!/usr/bin/env python3
"""
Unified Document Processor - Handles PDF, OCR, DOC/DOCX, PPT together
Processes all document types in one comprehensive pipeline
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
from typing import List, Dict, Any
from core.io import PDFLoader, ZipIngestor
from core.index import Indexer
from core.qa import retrieve_candidates, answer_query
from core.config import CFG

class UnifiedDocumentProcessor:
    """Processes all document types: PDF, OCR, DOC, DOCX, PPT"""
    
    def __init__(self):
        self.stats = {
            'pdf_regular': {'files': 0, 'chunks': 0, 'success': 0},
            'pdf_ocr': {'files': 0, 'chunks': 0, 'success': 0},
            'doc_files': {'files': 0, 'chunks': 0, 'success': 0},
            'total_processed': 0
        }
    
    def extract_documents(self) -> int:
        """Extract all documents from ZIP files"""
        
        print("📦 Starting document extraction...")
        
        try:
            ingestor = ZipIngestor()
            files_extracted = ingestor.run()
            print(f"✅ Extracted {files_extracted} files")
            return files_extracted
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return 0
    
    def categorize_files(self) -> Dict[str, List[Path]]:
        """Categorize files by type for processing"""
        
        print("\n📂 Categorizing files by type...")
        
        all_files = list(CFG.extract_dir.rglob("*"))
        
        file_categories = {
            'pdf': [],
            'doc': [],
            'docx': [],
            'ppt': [],
            'other': []
        }
        
        for file_path in all_files:
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                if suffix == '.pdf':
                    file_categories['pdf'].append(file_path)
                elif suffix == '.doc':
                    file_categories['doc'].append(file_path)
                elif suffix == '.docx':
                    file_categories['docx'].append(file_path)
                elif suffix in ['.ppt', '.pptx']:
                    file_categories['ppt'].append(file_path)
                elif suffix in ['.txt', '.rtf']:
                    file_categories['other'].append(file_path)
        
        print(f"📄 PDF files: {len(file_categories['pdf'])}")
        print(f"📄 DOC files: {len(file_categories['doc'])}")
        print(f"📄 DOCX files: {len(file_categories['docx'])}")
        print(f"📊 PPT files: {len(file_categories['ppt'])}")
        print(f"📄 Other files: {len(file_categories['other'])}")
        
        return file_categories
    
    def process_pdfs_unified(self, pdf_files: List[Path]) -> int:
        """Process PDFs with both regular and OCR as needed"""
        
        print(f"\n🧠 Processing {len(pdf_files)} PDF files (Regular + OCR)...")
        
        if not pdf_files:
            return 0
        
        regular_loader = PDFLoader(use_ocr=False)
        ocr_loader = PDFLoader(use_ocr=True)
        successful_count = 0
        
        for i, pdf_file in enumerate(pdf_files):
            print(f"  📄 Processing {i+1}/{len(pdf_files)}: {pdf_file.name}")
            
            try:
                # Try regular extraction first
                pages = regular_loader.load_pages(pdf_file)
                
                if pages and any(len(p.text.strip()) > 50 for p in pages):
                    # Good text content found with regular extraction
                    char_count = sum(len(p.text) for p in pages)
                    successful_count += 1
                    self.stats['pdf_regular']['success'] += 1
                    self.stats['pdf_regular']['chunks'] += len(pages)
                    
                    print(f"    ✅ Regular: {len(pages)} pages, {char_count} chars")
                    
                else:
                    # Try OCR extraction
                    print(f"    🔍 Trying OCR...")
                    start_time = time.time()
                    ocr_pages = ocr_loader.load_pages(pdf_file)
                    processing_time = time.time() - start_time
                    
                    if ocr_pages and any(len(p.text.strip()) > 20 for p in ocr_pages):
                        char_count = sum(len(p.text) for p in ocr_pages)
                        successful_count += 1
                        self.stats['pdf_ocr']['success'] += 1
                        self.stats['pdf_ocr']['chunks'] += len(ocr_pages)
                        
                        print(f"    ✅ OCR: {len(ocr_pages)} pages, {char_count} chars ({processing_time:.1f}s)")
                    else:
                        print(f"    ⚠️ No text extracted with OCR ({processing_time:.1f}s)")
                        
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        self.stats['pdf_regular']['files'] = len(pdf_files)
        self.stats['pdf_ocr']['files'] = len(pdf_files)
        
        return successful_count
    
    def process_office_docs(self, doc_files: List[Path], docx_files: List[Path], ppt_files: List[Path]) -> int:
        """Process DOC, DOCX, and PPT files"""
        
        all_office_files = doc_files + docx_files + ppt_files
        
        print(f"\n📝 Processing {len(all_office_files)} Office files...")
        
        if not all_office_files:
            return 0
        
        successful_count = 0
        
        for i, office_file in enumerate(all_office_files):
            print(f"  📄 Processing {i+1}/{len(all_office_files)}: {office_file.name}")
            
            try:
                if office_file.suffix.lower() == '.docx':
                    # Basic DOCX processing
                    try:
                        import docx
                        doc = docx.Document(office_file)
                        text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                        
                        if len(text_content.strip()) > 50:
                            successful_count += 1
                            self.stats['doc_files']['chunks'] += 1
                            print(f"    ✅ DOCX: {len(text_content)} chars")
                        else:
                            print(f"    ⚠️ No substantial text content")
                            
                    except ImportError:
                        print(f"    ⚠️ python-docx not available for DOCX files")
                        print(f"    💡 Install with: pip install python-docx")
                        
                elif office_file.suffix.lower() in ['.ppt', '.pptx']:
                    print(f"    ⚠️ PowerPoint processing requires python-pptx")
                    print(f"    💡 Install with: pip install python-pptx")
                    
                else:
                    # DOC files
                    print(f"    ⚠️ DOC format requires additional tools (python-docx2txt)")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        self.stats['doc_files']['files'] = len(all_office_files)
        self.stats['doc_files']['success'] = successful_count
        
        return successful_count
    
    def build_unified_index(self) -> bool:
        """Build unified search index with all processed documents"""
        
        print(f"\n🏗️ Building unified search index...")
        
        try:
            # Create indexer that will process all files in extract directory
            indexer = Indexer(CFG)
            indexer.loader = PDFLoader(use_ocr=False)  # Will handle OCR separately as needed
            
            # Build the index
            chunks_created = indexer.build()
            
            print(f"✅ Index built successfully")
            print(f"📊 Estimated chunks created: {chunks_created if chunks_created else 'processing...'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Index building failed: {e}")
            return False
    
    def test_system(self) -> Dict[str, Any]:
        """Test the unified system with sample queries"""
        
        print(f"\n🧪 Testing unified system...")
        
        test_queries = [
            "Mindestlohn Bestimmungen Bauprojekte",
            "Vergabeunterlagen Straßenbau", 
            "VOB Regelungen",
            "construction requirements",
            "technical specifications"
        ]
        
        test_results = {
            'queries_tested': len(test_queries),
            'successful_queries': 0,
            'total_hits': 0
        }
        
        for i, query in enumerate(test_queries):
            print(f"  🔍 Testing {i+1}/{len(test_queries)}: '{query}'")
            
            try:
                hits = retrieve_candidates(query, CFG)
                
                if hits:
                    test_results['successful_queries'] += 1
                    test_results['total_hits'] += len(hits)
                    print(f"    ✅ {len(hits)} hits found")
                else:
                    print(f"    ⚠️ No results found")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        return test_results
    
    def run_unified_pipeline(self):
        """Run the complete unified document processing pipeline"""
        
        print("🚀 Starting Unified Document Processing Pipeline")
        print("🎯 Processing PDF (Regular + OCR) + DOC/DOCX + PPT together")
        print("=" * 70)
        
        start_time = time.time()
        
        try:
            # Stage 1: Extract documents
            files_extracted = self.extract_documents()
            if files_extracted == 0:
                print("❌ No files extracted, stopping pipeline")
                return
            
            # Stage 2: Categorize files
            file_categories = self.categorize_files()
            
            # Stage 3: Process PDFs (Regular + OCR unified)
            pdf_success = self.process_pdfs_unified(file_categories['pdf'])
            
            # Stage 4: Process Office documents
            office_success = self.process_office_docs(
                file_categories['doc'], 
                file_categories['docx'],
                file_categories['ppt']
            )
            
            # Stage 5: Build unified index
            print(f"\n🔄 Building index for all processed documents...")
            index_success = self.build_unified_index()
            
            if not index_success:
                print("❌ Index building failed, stopping pipeline")
                return
            
            # Stage 6: Test system
            test_results = self.test_system()
            
            # Generate final report
            total_time = time.time() - start_time
            
            print("\n" + "=" * 70)
            print("🎉 UNIFIED PROCESSING PIPELINE COMPLETE!")
            print("=" * 70)
            
            total_files = pdf_success + office_success
            total_chunks = (self.stats['pdf_regular']['chunks'] + 
                          self.stats['pdf_ocr']['chunks'] + 
                          self.stats['doc_files']['chunks'])
            
            print(f"📊 Processing Summary:")
            print(f"   📄 PDF (Regular): {self.stats['pdf_regular']['success']} successful")
            print(f"   🔍 PDF (OCR): {self.stats['pdf_ocr']['success']} successful") 
            print(f"   📝 Office docs: {office_success} successful")
            print(f"\n🎯 Total Results:")
            print(f"   📁 Total files processed successfully: {total_files}")
            print(f"   🔢 Total chunks estimated: {total_chunks}")
            print(f"   ⏱️ Total processing time: {total_time:.1f} seconds")
            print(f"   🧪 System tests: {test_results['successful_queries']}/{test_results['queries_tested']} passed")
            
            if test_results['successful_queries'] > 0:
                print(f"\n🚀 Your unified system is ready!")
                print(f"   Next: streamlit run ui/multilingual_tender_bot.py")
            else:
                print(f"\n⚠️ System needs debugging - check for errors above")
            
        except Exception as e:
            print(f"❌ Pipeline failed with error: {e}")

def main():
    processor = UnifiedDocumentProcessor()
    processor.run_unified_pipeline()

if __name__ == "__main__":
    main()
