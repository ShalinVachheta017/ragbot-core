import logging
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
from .config import CFG

class ComprehensiveRAGLogger:
    """Complete logging system for all RAG pipeline stages"""
    
    def __init__(self):
        # Create timestamped logging session
        self.session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.logs_root = CFG.logs_dir / f"session_{self.session_id}"
        
        # Create organized directory structure
        self.setup_logging_directories()
        self.setup_loggers()
        
        # Statistics tracking
        self.stats = {
            "ingestion": {"files_processed": 0, "files_failed": 0, "total_size_mb": 0},
            "embedding": {"chunks_embedded": 0, "gpu_batches": 0, "total_time": 0},
            "ocr": {"pages_attempted": 0, "pages_successful": 0, "text_extracted_chars": 0},
            "evaluation": {"queries_tested": 0, "avg_retrieval_score": 0, "avg_generation_score": 0}
        }
    
    def setup_logging_directories(self):
        """Create organized logging structure"""
        directories = [
            "ingestion",
            "embedding", 
            "ocr",
            "evaluation",
            "system",
            "performance",
            "errors",
            "data_exports"
        ]
        
        for directory in directories:
            (self.logs_root / directory).mkdir(parents=True, exist_ok=True)
    
    def setup_loggers(self):
        """Configure specialized loggers for each component"""
        # Main system logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(self.logs_root / 'system' / 'main.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        # Create component-specific loggers
        self.ingestion_logger = self._create_component_logger("ingestion")
        self.embedding_logger = self._create_component_logger("embedding") 
        self.ocr_logger = self._create_component_logger("ocr")
        self.evaluation_logger = self._create_component_logger("evaluation")
        self.performance_logger = self._create_component_logger("performance")
        
    def _create_component_logger(self, component: str):
        """Create specialized logger for component"""
        logger = logging.getLogger(component)
        handler = logging.FileHandler(
            self.logs_root / component / f"{component}.log", 
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    # ========== INGESTION LOGGING ==========
    def log_ingestion_start(self, zip_count: int, total_size_mb: float):
        """Log start of ingestion process"""
        msg = f"🚀 INGESTION STARTED - {zip_count} ZIP files, {total_size_mb:.1f}MB total"
        self.ingestion_logger.info(msg)
        
        # Create detailed CSV log
        with open(self.logs_root / 'ingestion' / 'ingestion_summary.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'zip_file', 'files_extracted', 'size_mb', 'status', 'error'])
    
    def log_pdf_processed(self, pdf_path: Path, pages_count: int, text_length: int, processing_time: float):
        """Log individual PDF processing"""
        msg = f"✅ PDF: {pdf_path.name} | Pages: {pages_count} | Text: {text_length} chars | Time: {processing_time:.2f}s"
        self.ingestion_logger.info(msg)
        
        # Add to CSV
        with open(self.logs_root / 'ingestion' / 'pdf_details.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                pdf_path.name,
                pages_count,
                text_length,
                processing_time,
                "success"
            ])
        
        self.stats["ingestion"]["files_processed"] += 1

    # ========== EMBEDDING LOGGING ==========
    def log_embedding_start(self, total_chunks: int, batch_size: int, gpu_enabled: bool):
        """Log embedding process start"""
        device = "GPU" if gpu_enabled else "CPU"
        msg = f"🚀 EMBEDDING STARTED - {total_chunks} chunks, batch_size={batch_size}, device={device}"
        self.embedding_logger.info(msg)
        
        # Create embedding details CSV
        with open(self.logs_root / 'embedding' / 'embedding_batches.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'batch_id', 'chunk_count', 'processing_time', 'gpu_memory_used', 'avg_embedding_norm'])

    def log_embedding_batch(self, batch_id: int, chunk_count: int, processing_time: float, gpu_memory: float, avg_norm: float):
        """Log individual embedding batch"""
        msg = f"📤 Batch {batch_id}: {chunk_count} chunks | Time: {processing_time:.2f}s | GPU Mem: {gpu_memory:.1f}MB | Norm: {avg_norm:.3f}"
        self.embedding_logger.info(msg)
        
        # Add to CSV
        with open(self.logs_root / 'embedding' / 'embedding_batches.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                batch_id,
                chunk_count,
                processing_time,
                gpu_memory,
                avg_norm
            ])
        
        self.stats["embedding"]["chunks_embedded"] += chunk_count
        self.stats["embedding"]["gpu_batches"] += 1

    # ========== OCR LOGGING ==========
    def log_ocr_start(self, files_for_ocr: int):
        """Log OCR process start"""
        msg = f"🔍 OCR STARTED - {files_for_ocr} files require OCR processing"
        self.ocr_logger.info(msg)
        
        # Create OCR details CSV
        with open(self.logs_root / 'ocr' / 'ocr_results.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'file_name', 'page_number', 'ocr_confidence', 'text_length', 'processing_time', 'success'])

    def log_ocr_page(self, file_name: str, page_num: int, text_length: int, confidence: float, processing_time: float, success: bool):
        """Log individual OCR page processing"""
        status = "✅" if success else "❌"
        msg = f"{status} OCR: {file_name} p{page_num} | Chars: {text_length} | Confidence: {confidence:.2f} | Time: {processing_time:.2f}s"
        self.ocr_logger.info(msg)
        
        # Add to CSV
        with open(self.logs_root / 'ocr' / 'ocr_results.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                file_name,
                page_num,
                confidence,
                text_length,
                processing_time,
                success
            ])
        
        self.stats["ocr"]["pages_attempted"] += 1
        if success:
            self.stats["ocr"]["pages_successful"] += 1
            self.stats["ocr"]["text_extracted_chars"] += text_length

    # ========== EVALUATION LOGGING ==========
    def log_evaluation_start(self, test_queries: int, metrics_used: List[str]):
        """Log evaluation process start"""
        msg = f"📊 EVALUATION STARTED - {test_queries} queries, metrics: {', '.join(metrics_used)}"
        self.evaluation_logger.info(msg)
        
        # Create evaluation results CSV
        with open(self.logs_root / 'evaluation' / 'evaluation_results.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'query', 'query_language', 'hit_rate', 'mrr', 'context_precision', 
                'faithfulness', 'answer_relevancy', 'response_time', 'retrieved_docs_count'
            ])

    def log_evaluation_query(self, query: str, metrics: Dict[str, float]):
        """Log individual query evaluation"""
        msg = f"🎯 Query: '{query[:50]}...' | Hit Rate: {metrics['hit_rate']:.3f} | Faithfulness: {metrics['faithfulness']:.3f}"
        self.evaluation_logger.info(msg)
        
        # Add to CSV
        with open(self.logs_root / 'evaluation' / 'evaluation_results.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                query,
                metrics.get('query_language', 'unknown'),
                metrics.get('hit_rate', 0),
                metrics.get('mrr', 0),
                metrics.get('context_precision', 0),
                metrics.get('faithfulness', 0),
                metrics.get('answer_relevancy', 0),
                metrics.get('response_time', 0),
                metrics.get('retrieved_docs_count', 0)
            ])
        
        self.stats["evaluation"]["queries_tested"] += 1

    # ========== PERFORMANCE LOGGING ==========
    def log_performance_snapshot(self, stage: str, cpu_percent: float, memory_mb: float, gpu_memory_mb: float = 0):
        """Log system performance at any stage"""
        msg = f"📈 {stage} | CPU: {cpu_percent:.1f}% | RAM: {memory_mb:.1f}MB | GPU: {gpu_memory_mb:.1f}MB"
        self.performance_logger.info(msg)
        
        # Add to performance CSV
        perf_file = self.logs_root / 'performance' / 'system_performance.csv'
        if not perf_file.exists():
            with open(perf_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'stage', 'cpu_percent', 'memory_mb', 'gpu_memory_mb'])
        
        with open(perf_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), stage, cpu_percent, memory_mb, gpu_memory_mb])

    # ========== SESSION SUMMARY ==========
    def generate_session_summary(self):
        """Generate comprehensive session summary"""
        summary = {
            "session_id": self.session_id,
            "start_time": self.session_id,
            "end_time": datetime.now().isoformat(),
            "statistics": self.stats,
            "logs_location": str(self.logs_root),
            "system_info": {
                "gpu_available": torch.cuda.is_available() if 'torch' in globals() else False,
                "total_documents_processed": self.stats["ingestion"]["files_processed"],
                "total_chunks_embedded": self.stats["embedding"]["chunks_embedded"],
                "ocr_success_rate": self.stats["ocr"]["pages_successful"] / max(1, self.stats["ocr"]["pages_attempted"]),
                "evaluation_queries": self.stats["evaluation"]["queries_tested"]
            }
        }
        
        # Save JSON summary
        with open(self.logs_root / 'session_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Generate markdown report
        self._generate_markdown_report(summary)
        
        return summary

    def _generate_markdown_report(self, summary: Dict):
        """Generate beautiful markdown report"""
        report = f"""
# 🚀 RAG System Pipeline Execution Report

**Session ID:** {summary['session_id']}  
**Execution Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Logs Location:** `{summary['logs_location']}`  

## 📊 Pipeline Statistics

### 📄 Document Ingestion
- **Files Processed:** {summary['statistics']['ingestion']['files_processed']:,}
- **Files Failed:** {summary['statistics']['ingestion']['files_failed']:,}
- **Total Data Size:** {summary['statistics']['ingestion']['total_size_mb']:.1f} MB

### 🧠 Embedding Generation  
- **Chunks Embedded:** {summary['statistics']['embedding']['chunks_embedded']:,}
- **GPU Batches:** {summary['statistics']['embedding']['gpu_batches']:,}
- **Total Processing Time:** {summary['statistics']['embedding']['total_time']:.1f}s

### 🔍 OCR Processing
- **Pages Attempted:** {summary['statistics']['ocr']['pages_attempted']:,}
- **Pages Successful:** {summary['statistics']['ocr']['pages_successful']:,}
- **Success Rate:** {(summary['statistics']['ocr']['pages_successful']/max(1,summary['statistics']['ocr']['pages_attempted'])*100):.1f}%
- **Text Extracted:** {summary['statistics']['ocr']['text_extracted_chars']:,} characters

### 📊 System Evaluation
- **Queries Tested:** {summary['statistics']['evaluation']['queries_tested']:,}
- **Average Retrieval Score:** {summary['statistics']['evaluation']['avg_retrieval_score']:.3f}
- **Average Generation Score:** {summary['statistics']['evaluation']['avg_generation_score']:.3f}

## 📁 Generated Log Files

### Core Logs
- `system/main.log` - Main system log
- `ingestion/ingestion.log` - Document processing
- `embedding/embedding.log` - Vector embedding generation  
- `ocr/ocr.log` - OCR processing details
- `evaluation/evaluation.log` - System evaluation results

### Data Exports (CSV)
- `ingestion/pdf_details.csv` - Detailed PDF processing results
- `embedding/embedding_batches.csv` - Batch processing metrics
- `ocr/ocr_results.csv` - OCR page-by-page results  
- `evaluation/evaluation_results.csv` - Query evaluation metrics
- `performance/system_performance.csv` - System resource usage

### Summary Files
- `session_summary.json` - Machine-readable session summary
- `pipeline_report.md` - This human-readable report

---
*Generated by Krishna RAG System Comprehensive Logger*
        """
        
        with open(self.logs_root / 'pipeline_report.md', 'w', encoding='utf-8') as f:
            f.write(report)

# Global logger instance
rag_logger = None

def get_rag_logger() -> ComprehensiveRAGLogger:
    """Get or create global RAG logger instance"""
    global rag_logger
    if rag_logger is None:
        rag_logger = ComprehensiveRAGLogger()
    return rag_logger
