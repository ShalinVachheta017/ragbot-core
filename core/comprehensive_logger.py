import logging
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import time
import psutil
import os

class ComprehensiveRAGLogger:
    """Complete logging system for the entire RAG pipeline"""
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs_root = Path("logs/fresh_pipeline") / f"session_{self.session_id}"
        
        # Create directory structure
        self._setup_directories()
        self._setup_loggers()
        
        # Performance tracking
        self.start_time = time.time()
        self.stage_times = {}
        self.system_stats = []
        
        print(f"🚀 Initialized comprehensive logging: {self.logs_root}")
    
    def _setup_directories(self):
        """Create organized logging structure"""
        subdirs = [
            "ingestion", "embedding", "ocr", "evaluation", 
            "system", "performance", "errors", "exports"
        ]
        
        for subdir in subdirs:
            (self.logs_root / subdir).mkdir(parents=True, exist_ok=True)
    
    def _setup_loggers(self):
        """Configure specialized loggers"""
        # Main system logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(self.logs_root / 'system' / 'main.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('RAGPipeline')
        self.logger.info(f"🎯 Starting fresh RAG pipeline - Session {self.session_id}")
    
    def log_stage_start(self, stage: str):
        """Log start of pipeline stage"""
        self.stage_times[stage] = time.time()
        self.logger.info(f"🔄 STAGE START: {stage.upper()}")
        
        # Log system state
        self._log_system_performance(f"{stage}_start")
    
    def log_stage_complete(self, stage: str, details: Dict = None):
        """Log completion of pipeline stage"""
        duration = time.time() - self.stage_times.get(stage, time.time())
        self.logger.info(f"✅ STAGE COMPLETE: {stage.upper()} ({duration:.2f}s)")
        
        if details:
            self.logger.info(f"📊 {stage.upper()} DETAILS: {details}")
        
        self._log_system_performance(f"{stage}_complete")
    
    def log_file_processed(self, stage: str, file_path: str, success: bool, details: Dict = None):
        """Log individual file processing"""
        status = "✅" if success else "❌"
        self.logger.info(f"{status} {stage.upper()}: {Path(file_path).name}")
        
        # Write to CSV
        csv_file = self.logs_root / stage / f"{stage}_files.csv"
        if not csv_file.exists():
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'file', 'success', 'details'])
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                file_path,
                success,
                json.dumps(details or {})
            ])
    
    def log_batch_processing(self, stage: str, batch_id: int, items_count: int, 
                           processing_time: float, success_rate: float, details: Dict = None):
        """Log batch processing results"""
        self.logger.info(
            f"📦 {stage.upper()} Batch {batch_id}: "
            f"{items_count} items, {processing_time:.2f}s, {success_rate:.1%} success"
        )
        
        # Write to batch CSV
        csv_file = self.logs_root / stage / f"{stage}_batches.csv"
        if not csv_file.exists():
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'batch_id', 'items_count', 'processing_time', 
                    'success_rate', 'details'
                ])
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(), batch_id, items_count, 
                processing_time, success_rate, json.dumps(details or {})
            ])
    
    def log_evaluation_query(self, query: str, response: str, metrics: Dict):
        """Log evaluation query and results"""
        self.logger.info(f"🎯 EVAL: '{query[:50]}...' | Metrics: {metrics}")
        
        # Write to evaluation CSV
        csv_file = self.logs_root / 'evaluation' / 'evaluation_results.csv'
        if not csv_file.exists():
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'query', 'response_preview', 'hit_rate', 
                    'relevance_score', 'response_time', 'language', 'hits_count'
                ])
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                query,
                response[:100] + "..." if len(response) > 100 else response,
                metrics.get('hit_rate', 0),
                metrics.get('relevance_score', 0),
                metrics.get('response_time', 0),
                metrics.get('language', 'unknown'),
                metrics.get('hits_count', 0)
            ])
    
    def _log_system_performance(self, checkpoint: str):
        """Log system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'checkpoint': checkpoint,
                'cpu_percent': cpu_percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_available_gb': memory.available / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'session_duration': time.time() - self.start_time
            }
            
            self.system_stats.append(stats)
            
            # Write to performance CSV
            csv_file = self.logs_root / 'performance' / 'system_performance.csv'
            if not csv_file.exists():
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(list(stats.keys()))
            
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(list(stats.values()))
                
        except Exception as e:
            self.logger.warning(f"Could not log performance: {e}")
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        total_duration = time.time() - self.start_time
        
        report = {
            'session_id': self.session_id,
            'total_duration': total_duration,
            'logs_location': str(self.logs_root),
            'stages_completed': list(self.stage_times.keys()),
            'system_summary': self._generate_system_summary()
        }
        
        # Save JSON report
        with open(self.logs_root / 'final_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Generate markdown report
        self._generate_markdown_report(report)
        
        self.logger.info(f"📋 Final report generated: {self.logs_root}/final_report.json")
        return report
    
    def _generate_system_summary(self):
        """Generate system performance summary"""
        if not self.system_stats:
            return {}
        
        df = pd.DataFrame(self.system_stats)
        return {
            'avg_cpu_percent': df['cpu_percent'].mean(),
            'max_memory_used_gb': df['memory_used_gb'].max(),
            'min_disk_free_gb': df['disk_free_gb'].min(),
            'performance_checkpoints': len(df)
        }
    
    def _generate_markdown_report(self, report: Dict):
        """Generate beautiful markdown report"""
        markdown = f"""
# 🚀 RAG Pipeline Execution Report

**Session ID:** {report['session_id']}  
**Total Duration:** {report['total_duration']:.2f} seconds  
**Completion Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Logs Location:** `{report['logs_location']}`

## 📊 Pipeline Stages Completed

{chr(10).join(f"- ✅ **{stage.title()}**" for stage in report['stages_completed'])}

## 🔧 System Performance Summary

- **Average CPU Usage:** {report['system_summary'].get('avg_cpu_percent', 0):.1f}%
- **Peak Memory Usage:** {report['system_summary'].get('max_memory_used_gb', 0):.2f} GB
- **Minimum Disk Space:** {report['system_summary'].get('min_disk_free_gb', 0):.2f} GB
- **Performance Checkpoints:** {report['system_summary'].get('performance_checkpoints', 0)}

## 📁 Generated Logs

### Core Logs
- `system/main.log` - Main pipeline log
- `ingestion/ingestion_files.csv` - File processing details
- `embedding/embedding_batches.csv` - Embedding batch results
- `ocr/ocr_files.csv` - OCR processing results
- `evaluation/evaluation_results.csv` - System evaluation metrics
- `performance/system_performance.csv` - System resource usage

### Summary Files
- `final_report.json` - Machine-readable summary
- `pipeline_report.md` - This human-readable report

---
*Generated by Multilingual Tender Bot Pipeline*
        """
        
        with open(self.logs_root / 'pipeline_report.md', 'w', encoding='utf-8') as f:
            f.write(markdown)

# Global logger instance
pipeline_logger = None

def get_pipeline_logger() -> ComprehensiveRAGLogger:
    """Get or create global pipeline logger"""
    global pipeline_logger
    if pipeline_logger is None:
        pipeline_logger = ComprehensiveRAGLogger()
    return pipeline_logger
