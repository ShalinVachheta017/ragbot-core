#!/usr/bin/env python3
"""
Production Deployment Script - Multilingual RAG Bot

This script performs a complete production deployment:
1. Validates all dependencies
2. Checks system resources
3. Rebuilds Qdrant collection
4. Runs health checks
5. Executes test suite
6. Generates deployment report

Usage:
    python deploy_production.py [--skip-tests] [--quick]
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
log_dir = Path("logs/deployment")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionDeployer:
    def __init__(self, skip_tests=False, quick=False):
        self.skip_tests = skip_tests
        self.quick = quick
        self.results = {
            "start_time": datetime.now(),
            "checks": {},
            "errors": []
        }
    
    def log_step(self, step: str, status: str = "START"):
        """Log deployment step"""
        emoji = {
            "START": "🔄",
            "SUCCESS": "✅",
            "FAILURE": "❌",
            "WARNING": "⚠️",
            "INFO": "ℹ️"
        }
        logger.info(f"{emoji.get(status, '•')} {step}")
    
    def run_command(self, cmd: list, check=True, timeout=300) -> tuple:
        """Run shell command and capture output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=check
            )
            return True, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr
        except Exception as e:
            return False, "", str(e)
    
    def check_dependencies(self) -> bool:
        """Validate all required dependencies"""
        self.log_step("Checking Dependencies")
        
        deps = {
            "python": ["python", "--version"],
            "qdrant": ["curl", "-s", "http://localhost:6333/collections"],
            "ollama": ["curl", "-s", "http://localhost:11434/api/tags"],
        }
        
        all_ok = True
        for name, cmd in deps.items():
            success, stdout, stderr = self.run_command(cmd, check=False)
            self.results["checks"][name] = success
            
            if success:
                self.log_step(f"  {name}: AVAILABLE", "SUCCESS")
            else:
                self.log_step(f"  {name}: MISSING", "FAILURE")
                self.results["errors"].append(f"{name} not available")
                all_ok = False
        
        return all_ok
    
    def check_python_packages(self) -> bool:
        """Verify Python packages"""
        self.log_step("Checking Python Packages")
        
        required = [
            "streamlit",
            "qdrant-client",
            "sentence-transformers",
            "pandas",
            "openpyxl"
        ]
        
        all_ok = True
        for pkg in required:
            try:
                __import__(pkg.replace("-", "_"))
                self.log_step(f"  {pkg}: INSTALLED", "SUCCESS")
            except ImportError:
                self.log_step(f"  {pkg}: MISSING", "FAILURE")
                self.results["errors"].append(f"Package {pkg} not installed")
                all_ok = False
        
        return all_ok
    
    def check_files(self) -> bool:
        """Verify required files exist"""
        self.log_step("Checking Required Files")
        
        required_files = [
            "ui/app_streamlit.py",
            "core/config.py",
            "core/qa.py",
            "core/search.py",
            "core/index.py",
            "data/metadata/cleaned_metadata.xlsx"
        ]
        
        all_ok = True
        for file_path in required_files:
            p = Path(file_path)
            if p.exists():
                self.log_step(f"  {file_path}: EXISTS", "SUCCESS")
            else:
                self.log_step(f"  {file_path}: MISSING", "FAILURE")
                self.results["errors"].append(f"File {file_path} not found")
                all_ok = False
        
        return all_ok
    
    def rebuild_collection(self) -> bool:
        """Rebuild Qdrant collection"""
        self.log_step("Rebuilding Qdrant Collection")
        
        if self.quick:
            self.log_step("  Skipping (quick mode)", "WARNING")
            return True
        
        # Run ingestion script
        success, stdout, stderr = self.run_command(
            ["python", "scripts/ingest.py", "--mode", "fresh"],
            timeout=900  # 15 minutes
        )
        
        if success:
            self.log_step("  Collection rebuilt successfully", "SUCCESS")
            # Log last 10 lines of output
            for line in stdout.splitlines()[-10:]:
                logger.info(f"    {line}")
        else:
            self.log_step("  Collection rebuild failed", "FAILURE")
            logger.error(f"Error: {stderr}")
            self.results["errors"].append("Collection rebuild failed")
        
        return success
    
    def run_health_check(self) -> bool:
        """Run system health check"""
        self.log_step("Running Health Check")
        
        try:
            # Check Qdrant collection
            from qdrant_client import QdrantClient
            from core.config import CFG
            
            client = QdrantClient(url=CFG.qdrant_url)
            
            # Check if collection exists
            collections = client.get_collections()
            has_collection = any(
                c.name == CFG.qdrant_collection 
                for c in collections.collections
            )
            
            if has_collection:
                info = client.get_collection(CFG.qdrant_collection)
                count = info.points_count
                self.log_step(f"  Collection: {count} points", "SUCCESS")
                self.results["checks"]["collection_points"] = count
            else:
                self.log_step("  Collection: NOT FOUND", "WARNING")
                self.results["checks"]["collection_points"] = 0
            
            # Check metadata
            import pandas as pd
            df = pd.read_excel("data/metadata/cleaned_metadata.xlsx")
            self.log_step(f"  Metadata: {len(df)} rows", "SUCCESS")
            self.results["checks"]["metadata_rows"] = len(df)
            
            return has_collection and len(df) > 0
            
        except Exception as e:
            self.log_step(f"  Health check failed: {e}", "FAILURE")
            self.results["errors"].append(f"Health check error: {e}")
            return False
    
    def run_tests(self) -> bool:
        """Run quick test queries"""
        self.log_step("Running Test Queries")
        
        if self.skip_tests:
            self.log_step("  Tests skipped", "WARNING")
            return True
        
        try:
            from core.qa import retrieve_candidates
            from core.config import CFG
            
            test_queries = [
                "VOB requirements",
                "20046891",  # DTAD-ID
                "construction in 2023"
            ]
            
            passed = 0
            failed = 0
            
            for query in test_queries:
                try:
                    hits = retrieve_candidates(query, CFG)
                    if hits:
                        self.log_step(f"  '{query[:30]}...': PASS ({len(hits)} hits)", "SUCCESS")
                        passed += 1
                    else:
                        self.log_step(f"  '{query[:30]}...': FAIL (no hits)", "FAILURE")
                        failed += 1
                except Exception as e:
                    self.log_step(f"  '{query[:30]}...': ERROR", "FAILURE")
                    logger.error(f"    {e}")
                    failed += 1
            
            self.results["checks"]["tests_passed"] = passed
            self.results["checks"]["tests_failed"] = failed
            
            return failed == 0
            
        except Exception as e:
            self.log_step(f"  Test execution failed: {e}", "FAILURE")
            self.results["errors"].append(f"Test error: {e}")
            return False
    
    def generate_report(self):
        """Generate deployment report"""
        self.log_step("Generating Deployment Report")
        
        self.results["end_time"] = datetime.now()
        self.results["duration"] = (
            self.results["end_time"] - self.results["start_time"]
        ).total_seconds()
        
        report_path = log_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, "w") as f:
            f.write("="*60 + "\n")
            f.write("PRODUCTION DEPLOYMENT REPORT\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Start Time: {self.results['start_time']}\n")
            f.write(f"End Time: {self.results['end_time']}\n")
            f.write(f"Duration: {self.results['duration']:.1f}s\n\n")
            
            f.write("CHECKS:\n")
            f.write("-"*60 + "\n")
            for check, result in self.results["checks"].items():
                status = "✅" if result else "❌"
                f.write(f"{status} {check}: {result}\n")
            
            if self.results["errors"]:
                f.write("\nERRORS:\n")
                f.write("-"*60 + "\n")
                for error in self.results["errors"]:
                    f.write(f"❌ {error}\n")
            
            f.write("\n" + "="*60 + "\n")
            
            if not self.results["errors"]:
                f.write("✅ DEPLOYMENT SUCCESSFUL\n")
            else:
                f.write("❌ DEPLOYMENT FAILED\n")
            
            f.write("="*60 + "\n")
        
        logger.info(f"Report saved to: {report_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("DEPLOYMENT SUMMARY")
        print("="*60)
        print(f"Duration: {self.results['duration']:.1f}s")
        print(f"Checks: {len([v for v in self.results['checks'].values() if v])}/{len(self.results['checks'])} passed")
        print(f"Errors: {len(self.results['errors'])}")
        
        if not self.results["errors"]:
            print("\n✅ DEPLOYMENT SUCCESSFUL")
            print("\nNext steps:")
            print("1. Access app: http://localhost:8501")
            print("2. Run full tests: See TEST_CHECKLIST.md")
            print("3. Monitor logs: tail -f logs/deployment/*.log")
        else:
            print("\n❌ DEPLOYMENT FAILED")
            print("\nErrors encountered:")
            for error in self.results["errors"]:
                print(f"  • {error}")
        
        print("="*60 + "\n")
    
    def deploy(self) -> bool:
        """Execute full deployment pipeline"""
        logger.info("="*60)
        logger.info("STARTING PRODUCTION DEPLOYMENT")
        logger.info("="*60)
        
        steps = [
            ("Dependencies", self.check_dependencies),
            ("Python Packages", self.check_python_packages),
            ("Required Files", self.check_files),
            ("Rebuild Collection", self.rebuild_collection),
            ("Health Check", self.run_health_check),
            ("Test Queries", self.run_tests),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\n{'='*60}")
            logger.info(f"STEP: {step_name}")
            logger.info(f"{'='*60}")
            
            success = step_func()
            
            if not success and step_name not in ["Test Queries"]:
                logger.error(f"CRITICAL: {step_name} failed!")
                if step_name not in ["Rebuild Collection"]:
                    # Stop deployment on critical failures
                    break
        
        self.generate_report()
        
        return len(self.results["errors"]) == 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy production RAG system")
    parser.add_argument("--skip-tests", action="store_true", help="Skip test queries")
    parser.add_argument("--quick", action="store_true", help="Skip collection rebuild")
    args = parser.parse_args()
    
    deployer = ProductionDeployer(
        skip_tests=args.skip_tests,
        quick=args.quick
    )
    
    success = deployer.deploy()
    sys.exit(0 if success else 1)
