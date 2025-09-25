# core/logger.py
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import torch  # optional; used for GPU flag in summary
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

from .config import CFG


class ComprehensiveRAGLogger:
    """Structured logging for all RAG pipeline stages."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.logs_root = Path(CFG.logs_dir) / f"session_{self.session_id}"
        self._ensure_dirs()
        self._setup_loggers()
        self._init_stats()

    # ---------- setup ----------

    def _ensure_dirs(self):
        for d in (
            "ingestion", "embedding", "ocr", "evaluation",
            "system", "performance", "errors", "data_exports"
        ):
            (self.logs_root / d).mkdir(parents=True, exist_ok=True)

    def _setup_loggers(self):
        # Root/system logger once
        root = logging.getLogger()
        if not root.handlers:
            root.setLevel(logging.INFO)
            root_handler = logging.FileHandler(self.logs_root / "system" / "main.log", encoding="utf-8")
            root_handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))
            root.addHandler(root_handler)
            root.addHandler(logging.StreamHandler())

        # Component loggers (idempotent)
        self.ingestion_logger   = self._component_logger("ingestion")
        self.embedding_logger   = self._component_logger("embedding")
        self.ocr_logger         = self._component_logger("ocr")
        self.evaluation_logger  = self._component_logger("evaluation")
        self.performance_logger = self._component_logger("performance")
        self.errors_logger      = self._component_logger("errors")

    def _component_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith(f"{name}.log") for h in logger.handlers):
            fh = logging.FileHandler(self.logs_root / name / f"{name}.log", encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            logger.addHandler(fh)
            logger.setLevel(logging.INFO)
        return logger

    def _init_stats(self):
        self.stats: Dict[str, Dict[str, Any]] = {
            "ingestion": {"files_processed": 0, "files_failed": 0, "total_size_mb": 0.0},
            "embedding": {"chunks_embedded": 0, "gpu_batches": 0, "total_time": 0.0},
            "ocr":       {"pages_attempted": 0, "pages_successful": 0, "text_extracted_chars": 0},
            "evaluation":{"queries_tested": 0, "avg_retrieval_score": 0.0, "avg_generation_score": 0.0},
        }

    # ---------- utilities ----------

    def log_error(self, component: str, message: str, exc: Optional[BaseException] = None):
        """Centralized error logging."""
        msg = f"{component.upper()}: {message}"
        if exc:
            msg += f" | EXC: {exc}"
        self.errors_logger.error(msg)

    # ---------- ingestion ----------

    def log_ingestion_start(self, zip_count: int, total_size_mb: float):
        self.ingestion_logger.info(f"🚀 INGESTION STARTED - {zip_count} ZIP files, {total_size_mb:.1f}MB total")
        path = self.logs_root / "ingestion" / "ingestion_summary.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp", "zip_file", "files_extracted", "size_mb", "status", "error"])

    def log_pdf_processed(self, pdf_path: Path, pages_count: int, text_length: int, processing_time: float):
        self.ingestion_logger.info(
            f"✅ PDF: {pdf_path.name} | Pages:{pages_count} | Text:{text_length} chars | Time:{processing_time:.2f}s"
        )
        path = self.logs_root / "ingestion" / "pdf_details.csv"
        new_file = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["timestamp", "pdf_file", "pages", "text_chars", "time_s", "status"])
            w.writerow([datetime.now().isoformat(), pdf_path.name, pages_count, text_length, processing_time, "success"])
        self.stats["ingestion"]["files_processed"] += 1

    # ---------- embedding ----------

    def log_embedding_start(self, total_chunks: int, batch_size: int, gpu_enabled: bool):
        device = "GPU" if gpu_enabled else "CPU"
        self.embedding_logger.info(f"🚀 EMBEDDING STARTED - {total_chunks} chunks, batch_size={batch_size}, device={device}")
        path = self.logs_root / "embedding" / "embedding_batches.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp", "batch_id", "chunk_count", "processing_time", "gpu_memory_mb", "avg_embedding_norm"])

    def log_embedding_batch(self, batch_id: int, chunk_count: int, processing_time: float, gpu_memory_mb: float, avg_norm: float):
        self.embedding_logger.info(
            f"📤 Batch {batch_id}: {chunk_count} chunks | Time:{processing_time:.2f}s | GPU Mem:{gpu_memory_mb:.1f}MB | Norm:{avg_norm:.3f}"
        )
        path = self.logs_root / "embedding" / "embedding_batches.csv"
        with path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().isoformat(), batch_id, chunk_count, processing_time, gpu_memory_mb, avg_norm])
        self.stats["embedding"]["chunks_embedded"] += chunk_count
        self.stats["embedding"]["gpu_batches"] += 1

    # ---------- ocr ----------

    def log_ocr_start(self, files_for_ocr: int):
        self.ocr_logger.info(f"🔍 OCR STARTED - {files_for_ocr} files require OCR processing")
        path = self.logs_root / "ocr" / "ocr_results.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp", "file_name", "page_number", "ocr_confidence", "text_length", "processing_time", "success"])

    def log_ocr_page(self, file_name: str, page_num: int, text_length: int, confidence: float, processing_time: float, success: bool):
        status = "✅" if success else "❌"
        self.ocr_logger.info(
            f"{status} OCR: {file_name} p{page_num} | Chars:{text_length} | Conf:{confidence:.2f} | Time:{processing_time:.2f}s"
        )
        path = self.logs_root / "ocr" / "ocr_results.csv"
        new_file = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["timestamp", "file_name", "page_number", "ocr_confidence", "text_length", "processing_time", "success"])
            w.writerow([datetime.now().isoformat(), file_name, page_num, confidence, text_length, processing_time, success])
        self.stats["ocr"]["pages_attempted"] += 1
        if success:
            self.stats["ocr"]["pages_successful"] += 1
            self.stats["ocr"]["text_extracted_chars"] += text_length

    # ---------- evaluation ----------

    def log_evaluation_start(self, test_queries: int, metrics_used: List[str]):
        self.evaluation_logger.info(f"📊 EVALUATION STARTED - {test_queries} queries, metrics: {', '.join(metrics_used)}")
        path = self.logs_root / "evaluation" / "evaluation_results.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "timestamp", "query", "query_language", "hit_rate", "mrr",
                "context_precision", "faithfulness", "answer_relevancy",
                "response_time", "retrieved_docs_count"
            ])

    def log_evaluation_query(self, query: str, metrics: Dict[str, float]):
        self.evaluation_logger.info(
            f"🎯 Query: '{query[:50]}…' | Hit Rate:{metrics.get('hit_rate',0):.3f} | Faithfulness:{metrics.get('faithfulness',0):.3f}"
        )
        path = self.logs_root / "evaluation" / "evaluation_results.csv"
        new_file = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow([
                    "timestamp", "query", "query_language", "hit_rate", "mrr",
                    "context_precision", "faithfulness", "answer_relevancy",
                    "response_time", "retrieved_docs_count"
                ])
            w.writerow([
                datetime.now().isoformat(),
                query,
                metrics.get("query_language", "unknown"),
                metrics.get("hit_rate", 0.0),
                metrics.get("mrr", 0.0),
                metrics.get("context_precision", 0.0),
                metrics.get("faithfulness", 0.0),
                metrics.get("answer_relevancy", 0.0),
                metrics.get("response_time", 0.0),
                metrics.get("retrieved_docs_count", 0),
            ])
        self.stats["evaluation"]["queries_tested"] += 1

    # ---------- perf ----------

    def log_performance_snapshot(self, stage: str, cpu_percent: float, memory_mb: float, gpu_memory_mb: float = 0.0):
        self.performance_logger.info(
            f"📈 {stage} | CPU:{cpu_percent:.1f}% | RAM:{memory_mb:.1f}MB | GPU:{gpu_memory_mb:.1f}MB"
        )
        path = self.logs_root / "performance" / "system_performance.csv"
        new_file = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["timestamp", "stage", "cpu_percent", "memory_mb", "gpu_memory_mb"])
            w.writerow([datetime.now().isoformat(), stage, cpu_percent, memory_mb, gpu_memory_mb])

    # ---------- summary ----------

    def generate_session_summary(self) -> Dict[str, Any]:
        gpu_ok = TORCH_AVAILABLE and bool(getattr(torch, "cuda", None)) and torch.cuda.is_available()  # type: ignore
        summary = {
            "session_id": self.session_id,
            "start_time": self.session_id,
            "end_time": datetime.now().isoformat(),
            "statistics": self.stats,
            "logs_location": str(self.logs_root),
            "system_info": {
                "gpu_available": gpu_ok,
                "total_documents_processed": self.stats["ingestion"]["files_processed"],
                "total_chunks_embedded": self.stats["embedding"]["chunks_embedded"],
                "ocr_success_rate": (
                    self.stats["ocr"]["pages_successful"] / max(1, self.stats["ocr"]["pages_attempted"])
                ),
                "evaluation_queries": self.stats["evaluation"]["queries_tested"],
            },
        }

        with (self.logs_root / "session_summary.json").open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self._write_markdown_report(summary)
        return summary

    def _write_markdown_report(self, summary: Dict[str, Any]):
        report = f"""# 🚀 RAG Pipeline Execution Report

**Session ID:** {summary['session_id']}  
**Execution Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Logs Location:** `{summary['logs_location']}`

## 📊 Pipeline Statistics

### 📄 Document Ingestion
- Files Processed: {summary['statistics']['ingestion']['files_processed']:,}
- Files Failed: {summary['statistics']['ingestion']['files_failed']:,}
- Total Data Size: {summary['statistics']['ingestion']['total_size_mb']:.1f} MB

### 🧠 Embedding Generation
- Chunks Embedded: {summary['statistics']['embedding']['chunks_embedded']:,}
- GPU Batches: {summary['statistics']['embedding']['gpu_batches']:,}
- Total Processing Time: {summary['statistics']['embedding']['total_time']:.1f}s

### 🔍 OCR Processing
- Pages Attempted: {summary['statistics']['ocr']['pages_attempted']:,}
- Pages Successful: {summary['statistics']['ocr']['pages_successful']:,}
- Success Rate: {(summary['statistics']['ocr']['pages_successful'] / max(1, summary['statistics']['ocr']['pages_attempted']) * 100):.1f}%
- Text Extracted: {summary['statistics']['ocr']['text_extracted_chars']:,} characters

### 📊 System Evaluation
- Queries Tested: {summary['statistics']['evaluation']['queries_tested']:,}
- Average Retrieval Score: {summary['statistics']['evaluation']['avg_retrieval_score']:.3f}
- Average Generation Score: {summary['statistics']['evaluation']['avg_generation_score']:.3f}

## 📁 Generated Log Files
- system/main.log
- ingestion/ingestion_summary.csv, ingestion/pdf_details.csv
- embedding/embedding_batches.csv
- ocr/ocr_results.csv
- evaluation/evaluation_results.csv
- performance/system_performance.csv
- session_summary.json
- pipeline_report.md
"""
        with (self.logs_root / "pipeline_report.md").open("w", encoding="utf-8") as f:
            f.write(report)


# Singleton accessor
_rag_logger_singleton: Optional[ComprehensiveRAGLogger] = None

def get_rag_logger() -> ComprehensiveRAGLogger:
    global _rag_logger_singleton
    if _rag_logger_singleton is None:
        _rag_logger_singleton = ComprehensiveRAGLogger()
    return _rag_logger_singleton
