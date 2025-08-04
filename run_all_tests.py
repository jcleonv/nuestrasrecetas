#!/usr/bin/env python3
"""
Single Command Test Launcher
Run all tests with one command: python run_all_tests.py
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))

# Import all test modules
from advanced_test_orchestrator import AdvancedTestOrchestrator as TestOrchestrator
from enhanced_api_tester import EnhancedAPITester as APITestSuite
from enhanced_frontend_tester import EnhancedFrontendTester as FrontendTestSuite
from enhanced_integration_tester import EnhancedIntegrationTester as IntegrationTestSuite
from performance_tester import PerformanceTester as PerformanceTestSuite
from test_automated_fixes import AutomatedFixGenerator
from test_reporting import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestLauncher:
    """Launch and coordinate all tests"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.orchestrator = TestOrchestrator()
        self.fix_generator = AutomatedFixGenerator()
        self.report_generator = ReportGenerator()
        self.results = {}
    
    def _load_config(self, config_file: str) -> dict:
        """Load configuration"""
        default_config = {
            "parallel_execution": True,
            "max_workers": 4,
            "timeout": 300,
            "retry_failed": True,
            "generate_fixes": True,
            "auto_fix": False,
            "report_format": ["html", "markdown", "json"],
            "test_suites": {
                "api": True,
                "frontend": True,
                "integration": True,
                "performance": True,
                "security": True
            },
            "thresholds": {
                "min_success_rate": 0.8,
                "min_coverage": 0.7,
                "max_response_time": 1000
            }
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def run_all_tests(self) -> dict:
        """Run all test suites"""
        print("\n" + "="*80)
        print("🚀 LAUNCHING COMPREHENSIVE TEST SUITE")
        print("="*80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Configuration: {json.dumps(self.config, indent=2)}")
        print("="*80 + "\n")
        
        try:
            # Start services
            logger.info("Starting required services...")
            self.orchestrator.start_all_services()
            
            # Run tests
            logger.info("Running test suites...")
            self.results = self.orchestrator.run_all_tests()
            
            # Generate fixes if enabled
            if self.config["generate_fixes"]:
                logger.info("Generating automated fixes...")
                fixes = self.fix_generator.generate_fixes(self.results)
                
                if fixes and self.config["auto_fix"]:
                    logger.info("Applying automated fixes...")
                    fix_results = self.fix_generator.apply_fixes(fixes, dry_run=False)
                    self.results["fixes"] = fix_results
                else:
                    self.results["fixes"] = self.fix_generator.generate_fix_report(fixes)
            
            # Generate reports
            logger.info("Generating reports...")
            self._generate_reports()
            
            # Display summary
            self._display_summary()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            raise
        finally:
            # Always stop services
            logger.info("Stopping services...")
            self.orchestrator.stop_all_services()
    
    def _generate_reports(self):
        """Generate all report formats"""
        # Generate executive summary
        executive_summary = self.report_generator.generate_executive_summary(self.results)
        
        # Generate recommendations
        recommendations = self.report_generator.generate_recommendations(self.results, executive_summary)
        
        # Generate visualizations
        charts = self.report_generator.generate_visualizations(self.results, executive_summary)
        
        reports = {}
        
        # Generate HTML report
        if "html" in self.config["report_format"]:
            html_report = self.report_generator.generate_html_report(
                self.results, executive_summary, recommendations, charts
            )
            reports["html"] = html_report
        
        # Generate Markdown report
        if "markdown" in self.config["report_format"]:
            md_report = self.report_generator.generate_markdown_report(
                self.results, executive_summary, recommendations
            )
            reports["markdown"] = md_report
        
        # Generate JSON report
        if "json" in self.config["report_format"]:
            json_report = self._generate_json_report(executive_summary, recommendations)
            reports["json"] = json_report
        
        self.results["reports"] = reports
    
    def _generate_json_report(self, executive_summary: dict, recommendations: list) -> str:
        """Generate JSON report"""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "executive_summary": executive_summary,
            "test_results": self.results,
            "recommendations": [
                {
                    "priority": rec.priority,
                    "category": rec.category,
                    "title": rec.title,
                    "description": rec.description,
                    "steps": rec.steps
                }
                for rec in recommendations
            ]
        }
        
        report_path = Path("test_reports") / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return str(report_path)
    
    def _display_summary(self):
        """Display test execution summary"""
        print("\n" + "="*80)
        print("📊 TEST EXECUTION SUMMARY")
        print("="*80)
        
        # Calculate totals
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for suite, results in self.results.items():
            if isinstance(results, dict) and "summary" in results:
                summary = results["summary"]
                total_tests += summary.get("total", 0)
                total_passed += summary.get("passed", 0)
                total_failed += summary.get("failed", 0)
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Display metrics
        print(f"\n📈 Overall Metrics:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed} ✅")
        print(f"   Failed: {total_failed} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Display by suite
        print(f"\n📋 Results by Test Suite:")
        for suite, results in self.results.items():
            if isinstance(results, dict) and "summary" in results:
                summary = results["summary"]
                suite_success = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
                status = "✅" if suite_success >= 80 else "⚠️" if suite_success >= 60 else "❌"
                print(f"   {suite.upper()}: {suite_success:.1f}% {status}")
        
        # Display critical issues
        if "executive_summary" in self.results:
            critical_issues = self.results["executive_summary"].get("critical_issues", [])
            if critical_issues:
                print(f"\n🚨 Critical Issues Found: {len(critical_issues)}")
                for issue in critical_issues[:3]:  # Show top 3
                    print(f"   - {issue['title']}")
        
        # Display reports
        if "reports" in self.results:
            print(f"\n📄 Generated Reports:")
            for format_type, path in self.results["reports"].items():
                print(f"   {format_type.upper()}: {path}")
        
        # Display recommendations
        print(f"\n💡 Top Recommendations:")
        if "recommendations" in self.results:
            for i, rec in enumerate(self.results["recommendations"][:3], 1):
                print(f"   {i}. {rec['title']} (Priority: {rec['priority']})")
        
        # Final status
        print("\n" + "="*80)
        if success_rate >= self.config["thresholds"]["min_success_rate"] * 100:
            print("✅ TEST SUITE PASSED")
        else:
            print("❌ TEST SUITE FAILED")
        print("="*80 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run comprehensive test suite")
    parser.add_argument("--config", help="Configuration file path", default=None)
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--no-fix", action="store_true", help="Disable automated fixes")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically apply fixes")
    parser.add_argument("--suite", choices=["api", "frontend", "integration", "performance", "security", "all"],
                       default="all", help="Run specific test suite")
    parser.add_argument("--report", choices=["html", "markdown", "json", "all"],
                       default="all", help="Report format")
    parser.add_argument("--quick", action="store_true", help="Quick mode - skip slow tests")
    
    args = parser.parse_args()
    
    # Build config from args
    config = {}
    if args.config:
        config["config_file"] = args.config
    
    if args.parallel:
        config["parallel_execution"] = True
    
    if args.no_fix:
        config["generate_fixes"] = False
    
    if args.auto_fix:
        config["auto_fix"] = True
    
    if args.suite != "all":
        config["test_suites"] = {suite: suite == args.suite for suite in 
                                ["api", "frontend", "integration", "performance", "security"]}
    
    if args.report != "all":
        config["report_format"] = [args.report]
    
    if args.quick:
        config["timeout"] = 60
        if "test_suites" not in config:
            config["test_suites"] = {}
        config["test_suites"]["performance"] = False
    
    # Create launcher
    launcher = TestLauncher(config.get("config_file"))
    
    # Update config
    for key, value in config.items():
        if key != "config_file":
            launcher.config[key] = value
    
    # Run tests
    try:
        results = launcher.run_all_tests()
        
        # Exit with appropriate code
        total_tests = sum(r.get("summary", {}).get("total", 0) for r in results.values() if isinstance(r, dict))
        total_passed = sum(r.get("summary", {}).get("passed", 0) for r in results.values() if isinstance(r, dict))
        
        success_rate = (total_passed / total_tests) if total_tests > 0 else 0
        
        if success_rate >= launcher.config["thresholds"]["min_success_rate"]:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()