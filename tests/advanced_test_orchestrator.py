#!/usr/bin/env python3
"""
Advanced Test Orchestrator for NuestrasRecetas.club
Comprehensive automated testing system with:
- Server lifecycle management
- Environment orchestration
- Automated fix generation
- Detailed reporting with actionable recommendations
- Performance monitoring and benchmarking
"""

import asyncio
import json
import subprocess
import sys
import time
import signal
import os
import shutil
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TestEnvironment:
    """Test environment configuration"""
    name: str
    base_url: str
    server_process: Optional[subprocess.Popen] = None
    credentials: Dict[str, str] = None
    startup_time: float = 0
    is_external: bool = False


@dataclass
class FixRecommendation:
    """Automated fix recommendation"""
    issue_type: str
    severity: str  # critical, high, medium, low
    description: str
    fix_code: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    priority: int = 0


@dataclass
class TestSuiteResult:
    """Comprehensive test suite results"""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration: float
    success_rate: float
    error_patterns: List[str]
    performance_metrics: Dict[str, float]
    fix_recommendations: List[FixRecommendation]
    detailed_results: List[Any]


class AdvancedTestOrchestrator:
    """Advanced test orchestrator with comprehensive automation capabilities"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.tests_dir = self.project_root / 'tests'
        self.reports_dir = self.tests_dir / 'reports'
        self.screenshots_dir = self.tests_dir / 'screenshots'
        self.logs_dir = self.tests_dir / 'logs'
        
        # Ensure directories exist
        for directory in [self.reports_dir, self.screenshots_dir, self.logs_dir]:
            directory.mkdir(exist_ok=True)
        
        # Test environments
        self.environments = {
            'dev': TestEnvironment(
                name='dev',
                base_url='http://127.0.0.1:8000',
                credentials={'email': 'dev@test.com', 'password': 'dev123'}
            ),
            'external': TestEnvironment(
                name='external',
                base_url='http://127.0.0.1:8000',
                credentials={'email': 'dev@test.com', 'password': 'dev123'},
                is_external=True
            )
        }
        
        # Test results storage
        self.test_results: Dict[str, TestSuiteResult] = {}
        self.start_time = None
        self.end_time = None
        self.overall_fix_recommendations: List[FixRecommendation] = []
        
        # Performance baselines
        self.performance_baselines = {
            'api_response_time_ms': 500,
            'page_load_time_ms': 2000,
            'total_test_duration_minutes': 10,
            'memory_usage_mb': 500
        }
        
        # Error pattern recognition
        self.error_patterns = {
            'auth_failure': [r'401', r'unauthorized', r'authentication failed'],
            'server_error': [r'500', r'internal server error', r'exception'],
            'timeout': [r'timeout', r'connection timed out', r'request timeout'],
            'missing_endpoint': [r'404', r'not found', r'no route'],
            'validation_error': [r'400', r'bad request', r'validation'],
            'database_error': [r'database', r'sql', r'connection refused'],
            'javascript_error': [r'javascript', r'uncaught', r'reference error'],
            'css_error': [r'stylesheet', r'css', r'style'],
            'network_error': [r'network', r'connection', r'fetch']
        }

    async def setup_test_environment(self, env_name: str) -> bool:
        """Setup and start test environment"""
        env = self.environments.get(env_name)
        if not env:
            logger.error(f"Unknown environment: {env_name}")
            return False
        
        if env.is_external:
            logger.info(f"Using external environment: {env.base_url}")
            return await self._check_server_health(env.base_url)
        else:
            return await self._start_dev_server(env)

    async def _start_dev_server(self, env: TestEnvironment) -> bool:
        """Start development server"""
        logger.info("Starting Flask development server...")
        
        # Kill any existing server processes
        await self._kill_existing_servers()
        
        # Start server
        app_path = self.project_root / 'app.py'
        if not app_path.exists():
            logger.error(f"Flask app not found at {app_path}")
            return False
        
        # Set environment variables
        env_vars = os.environ.copy()
        env_vars.update({
            'FLASK_ENV': 'development',
            'FLASK_DEBUG': '1',
            'PORT': '8000'
        })
        
        start_time = time.time()
        try:
            env.server_process = subprocess.Popen(
                [sys.executable, str(app_path)],
                cwd=str(self.project_root),
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Wait for server to start
            max_wait = 30  # seconds
            while time.time() - start_time < max_wait:
                if await self._check_server_health(env.base_url):
                    env.startup_time = time.time() - start_time
                    logger.info(f"Server started successfully in {env.startup_time:.1f}s")
                    return True
                await asyncio.sleep(1)
            
            logger.error("Server failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False

    async def _check_server_health(self, base_url: str) -> bool:
        """Check if server is healthy"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/health", timeout=5) as response:
                    return response.status == 200
        except:
            # Fallback to requests if aiohttp not available
            try:
                import requests
                response = requests.get(f"{base_url}/health", timeout=5)
                return response.status_code == 200
            except:
                return False

    async def _kill_existing_servers(self):
        """Kill any existing server processes"""
        try:
            # Kill processes on port 8000
            subprocess.run(['pkill', '-f', 'app.py'], capture_output=True)
            subprocess.run(['lsof', '-ti:8000'], capture_output=True, check=False)
            await asyncio.sleep(2)
        except:
            pass

    def cleanup_environment(self, env_name: str):
        """Cleanup test environment"""
        env = self.environments.get(env_name)
        if env and env.server_process:
            try:
                # Graceful shutdown
                env.server_process.terminate()
                env.server_process.wait(timeout=5)
            except:
                # Force kill
                try:
                    os.killpg(os.getpgid(env.server_process.pid), signal.SIGTERM)
                except:
                    pass
            env.server_process = None

    async def install_dependencies(self) -> bool:
        """Install and verify all required dependencies"""
        logger.info("📦 Installing and verifying dependencies...")
        
        dependencies = [
            'requests',
            'aiohttp', 
            'playwright',
            'pytest',
            'pytest-asyncio',
            'beautifulsoup4',
            'psutil',
            'memory-profiler'
        ]
        
        try:
            # Install dependencies
            for dep in dependencies:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', dep
                ], check=True, capture_output=True)
            
            # Install Playwright browsers
            subprocess.run([
                sys.executable, '-m', 'playwright', 'install'
            ], check=True, capture_output=True)
            
            # Verify installations
            import requests
            import aiohttp
            from playwright.async_api import async_playwright
            
            logger.info("✅ All dependencies installed and verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to install dependencies: {e}")
            return False

    async def run_comprehensive_tests(self, env_name: str = 'dev') -> Dict[str, Any]:
        """Run all test suites comprehensively"""
        self.start_time = datetime.now()
        
        logger.info("🧪 STARTING COMPREHENSIVE TEST SUITE")
        logger.info("=" * 60)
        logger.info(f"🎯 Environment: {env_name}")
        logger.info(f"⏰ Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Setup environment
        if not await self.setup_test_environment(env_name):
            logger.error("❌ Failed to setup test environment")
            return self._generate_failure_report("Environment setup failed")
        
        env = self.environments[env_name]
        
        try:
            # Install dependencies
            if not await self.install_dependencies():
                return self._generate_failure_report("Dependency installation failed")
            
            # Run test suites in parallel where possible
            test_tasks = [
                self._run_api_tests(env),
                self._run_frontend_tests(env),
            ]
            
            # Run API and Frontend tests in parallel
            api_results, frontend_results = await asyncio.gather(*test_tasks, return_exceptions=True)
            
            # Handle exceptions
            if isinstance(api_results, Exception):
                api_results = self._create_error_result("api", str(api_results))
            if isinstance(frontend_results, Exception):
                frontend_results = self._create_error_result("frontend", str(frontend_results))
            
            self.test_results['api'] = api_results
            self.test_results['frontend'] = frontend_results
            
            # Run integration tests (needs both API and Frontend to be tested first)
            integration_results = await self._run_integration_tests(env)
            self.test_results['integration'] = integration_results
            
            # Run performance tests
            performance_results = await self._run_performance_tests(env)
            self.test_results['performance'] = performance_results
            
            # Generate automated fixes
            await self._generate_automated_fixes()
            
            # Generate comprehensive report
            self.end_time = datetime.now()
            return await self._generate_comprehensive_report()
            
        finally:
            # Cleanup
            self.cleanup_environment(env_name)

    async def _run_api_tests(self, env: TestEnvironment) -> TestSuiteResult:
        """Run comprehensive API tests"""
        logger.info("🚀 Running API Tests...")
        
        start_time = time.time()
        try:
            # Import and run enhanced API tests
            sys.path.insert(0, str(self.tests_dir))
            from enhanced_api_tester import EnhancedAPITester
            
            tester = EnhancedAPITester(env.base_url, env.credentials)
            results = await tester.run_all_tests()
            
            duration = time.time() - start_time
            
            return TestSuiteResult(
                suite_name='api',
                total_tests=results.get('total_tests', 0),
                passed_tests=results.get('passed_tests', 0),
                failed_tests=results.get('failed_tests', 0),
                skipped_tests=results.get('skipped_tests', 0),
                duration=duration,
                success_rate=results.get('success_rate', 0),
                error_patterns=self._extract_error_patterns(results.get('detailed_results', [])),
                performance_metrics=results.get('performance_metrics', {}),
                fix_recommendations=results.get('fix_recommendations', []),
                detailed_results=results.get('detailed_results', [])
            )
            
        except Exception as e:
            logger.error(f"API tests failed: {e}")
            return self._create_error_result("api", str(e))

    async def _run_frontend_tests(self, env: TestEnvironment) -> TestSuiteResult:
        """Run comprehensive frontend tests"""
        logger.info("🖥️ Running Frontend Tests...")
        
        start_time = time.time()
        try:
            # Import and run enhanced frontend tests
            sys.path.insert(0, str(self.tests_dir))
            from enhanced_frontend_tester import EnhancedFrontendTester
            
            tester = EnhancedFrontendTester(env.base_url, self.screenshots_dir)
            results = await tester.run_all_tests()
            
            duration = time.time() - start_time
            
            return TestSuiteResult(
                suite_name='frontend',
                total_tests=results.get('total_tests', 0),
                passed_tests=results.get('passed_tests', 0),
                failed_tests=results.get('failed_tests', 0),
                skipped_tests=results.get('skipped_tests', 0),
                duration=duration,
                success_rate=results.get('success_rate', 0),
                error_patterns=self._extract_error_patterns(results.get('detailed_results', [])),
                performance_metrics=results.get('performance_metrics', {}),
                fix_recommendations=results.get('fix_recommendations', []),
                detailed_results=results.get('detailed_results', [])
            )
            
        except Exception as e:
            logger.error(f"Frontend tests failed: {e}")
            return self._create_error_result("frontend", str(e))

    async def _run_integration_tests(self, env: TestEnvironment) -> TestSuiteResult:
        """Run comprehensive integration tests"""
        logger.info("🔗 Running Integration Tests...")
        
        start_time = time.time()
        try:
            # Import and run enhanced integration tests
            sys.path.insert(0, str(self.tests_dir))
            from enhanced_integration_tester import EnhancedIntegrationTester
            
            tester = EnhancedIntegrationTester(env.base_url, env.credentials)
            results = await tester.run_all_tests()
            
            duration = time.time() - start_time
            
            return TestSuiteResult(
                suite_name='integration',
                total_tests=results.get('total_tests', 0),
                passed_tests=results.get('passed_tests', 0),
                failed_tests=results.get('failed_tests', 0),
                skipped_tests=results.get('skipped_tests', 0),
                duration=duration,
                success_rate=results.get('success_rate', 0),
                error_patterns=self._extract_error_patterns(results.get('detailed_results', [])),
                performance_metrics=results.get('performance_metrics', {}),
                fix_recommendations=results.get('fix_recommendations', []),
                detailed_results=results.get('detailed_results', [])
            )
            
        except Exception as e:
            logger.error(f"Integration tests failed: {e}")
            return self._create_error_result("integration", str(e))

    async def _run_performance_tests(self, env: TestEnvironment) -> TestSuiteResult:
        """Run performance and load tests"""
        logger.info("⚡ Running Performance Tests...")
        
        start_time = time.time()
        try:
            # Import and run performance tests
            sys.path.insert(0, str(self.tests_dir))
            from performance_tester import PerformanceTester
            
            tester = PerformanceTester(env.base_url, self.performance_baselines)
            results = await tester.run_all_tests()
            
            duration = time.time() - start_time
            
            return TestSuiteResult(
                suite_name='performance',
                total_tests=results.get('total_tests', 0),
                passed_tests=results.get('passed_tests', 0),
                failed_tests=results.get('failed_tests', 0),
                skipped_tests=results.get('skipped_tests', 0),
                duration=duration,
                success_rate=results.get('success_rate', 0),
                error_patterns=self._extract_error_patterns(results.get('detailed_results', [])),
                performance_metrics=results.get('performance_metrics', {}),
                fix_recommendations=results.get('fix_recommendations', []),
                detailed_results=results.get('detailed_results', [])
            )
            
        except Exception as e:
            logger.error(f"Performance tests failed: {e}")
            return self._create_error_result("performance", str(e))

    def _extract_error_patterns(self, detailed_results: List[Any]) -> List[str]:
        """Extract and categorize error patterns from test results"""
        found_patterns = []
        
        for result in detailed_results:
            error_text = str(result.get('error_message', '') + ' ' + str(result.get('response_data', ''))).lower()
            
            for pattern_name, regexes in self.error_patterns.items():
                for regex in regexes:
                    if re.search(regex, error_text):
                        if pattern_name not in found_patterns:
                            found_patterns.append(pattern_name)
        
        return found_patterns

    async def _generate_automated_fixes(self):
        """Generate automated fix recommendations based on test results"""
        logger.info("🔧 Generating automated fixes...")
        
        for suite_name, suite_result in self.test_results.items():
            if hasattr(suite_result, 'error_patterns'):
                for pattern in suite_result.error_patterns:
                    fix = self._generate_fix_for_pattern(pattern, suite_name, suite_result)
                    if fix:
                        self.overall_fix_recommendations.append(fix)

    def _generate_fix_for_pattern(self, pattern: str, suite_name: str, suite_result: TestSuiteResult) -> Optional[FixRecommendation]:
        """Generate specific fix recommendation for error pattern"""
        
        fix_templates = {
            'auth_failure': FixRecommendation(
                issue_type='Authentication Failure',
                severity='high',
                description='Authentication endpoints are failing. Check credentials and session management.',
                fix_code='''
# Check session configuration in app.py
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# Verify authentication decorator
@login_required
def protected_route():
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
''',
                priority=1
            ),
            
            'server_error': FixRecommendation(
                issue_type='Server Internal Error',
                severity='critical',
                description='Server is throwing 500 errors. Check application logs and exception handling.',
                fix_code='''
# Add comprehensive error handling
try:
    # Your application logic here
    pass
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return jsonify({'error': 'Internal server error'}), 500
''',
                priority=1
            ),
            
            'database_error': FixRecommendation(
                issue_type='Database Connection Error',
                severity='critical',
                description='Database connection issues detected. Check Supabase configuration.',
                fix_code='''
# Verify Supabase configuration
from supabase import create_client, Client

try:
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    # Test connection
    result = supabase.table('users').select('id').limit(1).execute()
except Exception as e:
    logger.error(f"Database connection failed: {e}")
''',
                priority=1
            ),
            
            'javascript_error': FixRecommendation(
                issue_type='JavaScript Runtime Error',
                severity='medium',
                description='JavaScript errors detected in frontend. Check console logs and fix syntax.',
                fix_code='''
// Add error boundary and proper error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    // Send to error reporting service
});

// Wrap risky operations in try-catch
try {
    // Your JavaScript code here
} catch (error) {
    console.error('Error in operation:', error);
}
''',
                priority=2
            )
        }
        
        return fix_templates.get(pattern)

    def _create_error_result(self, suite_name: str, error_message: str) -> TestSuiteResult:
        """Create error result for failed test suite"""
        return TestSuiteResult(
            suite_name=suite_name,
            total_tests=0,
            passed_tests=0,
            failed_tests=1,
            skipped_tests=0,
            duration=0,
            success_rate=0,
            error_patterns=['suite_failure'],
            performance_metrics={},
            fix_recommendations=[
                FixRecommendation(
                    issue_type=f'{suite_name.title()} Suite Failure',
                    severity='critical',
                    description=f'The {suite_name} test suite failed to run: {error_message}',
                    priority=1
                )
            ],
            detailed_results=[]
        )

    def _generate_failure_report(self, reason: str) -> Dict[str, Any]:
        """Generate failure report when tests cannot run"""
        return {
            'success': False,
            'error': reason,
            'timestamp': datetime.now().isoformat(),
            'fix_recommendations': [
                FixRecommendation(
                    issue_type='Test Environment Setup',
                    severity='critical',
                    description=f'Failed to setup test environment: {reason}',
                    priority=1
                )
            ]
        }

    async def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report with executive summary"""
        logger.info("📊 Generating comprehensive report...")
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        # Calculate overall statistics
        total_tests = sum(r.total_tests for r in self.test_results.values())
        total_passed = sum(r.passed_tests for r in self.test_results.values())
        total_failed = sum(r.failed_tests for r in self.test_results.values())
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            total_tests, total_passed, total_failed, overall_success_rate, total_duration
        )
        
        # Compile all fix recommendations
        all_fixes = self.overall_fix_recommendations.copy()
        for result in self.test_results.values():
            all_fixes.extend(result.fix_recommendations)
        
        # Sort fixes by priority and severity
        all_fixes.sort(key=lambda x: (x.priority, {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.severity, 3)))
        
        # Generate performance analysis
        performance_analysis = self._generate_performance_analysis()
        
        # Create comprehensive report
        report = {
            'test_run_metadata': {
                'timestamp': self.start_time.isoformat(),
                'duration_seconds': total_duration,
                'environment': 'dev',  # TODO: Make dynamic
                'total_tests': total_tests,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'overall_success_rate': overall_success_rate
            },
            'executive_summary': executive_summary,
            'test_suites': {name: asdict(result) for name, result in self.test_results.items()},
            'fix_recommendations': [asdict(fix) for fix in all_fixes[:20]],  # Top 20 fixes
            'performance_analysis': performance_analysis,
            'detailed_findings': self._generate_detailed_findings()
        }
        
        # Save report
        report_path = self.reports_dir / f'comprehensive_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print executive summary
        self._print_executive_summary(report)
        
        logger.info(f"📁 Comprehensive report saved to: {report_path}")
        return report

    def _generate_executive_summary(self, total_tests: int, total_passed: int, total_failed: int, success_rate: float, duration: float) -> Dict[str, Any]:
        """Generate executive summary"""
        
        # Application health assessment
        if success_rate >= 95:
            health_status = "EXCELLENT"
            health_color = "🟢"
            health_description = "Application is performing exceptionally well with minimal issues."
        elif success_rate >= 85:
            health_status = "GOOD"
            health_color = "🟡"
            health_description = "Application is performing well with some minor issues to address."
        elif success_rate >= 70:
            health_status = "NEEDS ATTENTION"
            health_color = "🟠"
            health_description = "Application has several issues that require attention."
        else:
            health_status = "CRITICAL"
            health_color = "🔴"
            health_description = "Application has critical issues requiring immediate attention."
        
        # Risk assessment
        critical_issues = len([f for f in self.overall_fix_recommendations if f.severity == 'critical'])
        risk_level = "HIGH" if critical_issues > 5 else "MEDIUM" if critical_issues > 2 else "LOW"
        
        return {
            'health_status': health_status,
            'health_color': health_color,
            'health_description': health_description,
            'success_rate': success_rate,
            'total_tests': total_tests,
            'passed_tests': total_passed,
            'failed_tests': total_failed,
            'duration_minutes': duration / 60,
            'risk_level': risk_level,
            'critical_issues_count': critical_issues,
            'recommendations_count': len(self.overall_fix_recommendations)
        }

    def _generate_performance_analysis(self) -> Dict[str, Any]:
        """Generate performance analysis"""
        performance_data = {}
        
        if 'performance' in self.test_results:
            perf_result = self.test_results['performance']
            performance_data = perf_result.performance_metrics
        
        # Compare against baselines
        analysis = {
            'baseline_comparison': {},
            'bottlenecks': [],
            'recommendations': []
        }
        
        for metric, baseline in self.performance_baselines.items():
            actual = performance_data.get(metric, 0)
            if actual > baseline * 1.2:  # 20% over baseline is concerning
                analysis['bottlenecks'].append({
                    'metric': metric,
                    'actual': actual,
                    'baseline': baseline,
                    'deviation_percent': ((actual - baseline) / baseline) * 100
                })
        
        return analysis

    def _generate_detailed_findings(self) -> List[Dict[str, Any]]:
        """Generate detailed findings from all test suites"""
        findings = []
        
        for suite_name, result in self.test_results.items():
            if result.failed_tests > 0:
                findings.append({
                    'suite': suite_name,
                    'issue': f'{result.failed_tests} tests failed',
                    'impact': 'high' if result.success_rate < 80 else 'medium',
                    'error_patterns': result.error_patterns
                })
        
        return findings

    def _print_executive_summary(self, report: Dict[str, Any]):
        """Print executive summary to console"""
        summary = report['executive_summary']
        
        print("\n" + "=" * 80)
        print("📊 EXECUTIVE SUMMARY - NUESTRASRECETAS.CLUB TEST RESULTS")
        print("=" * 80)
        
        print(f"{summary['health_color']} APPLICATION STATUS: {summary['health_status']}")
        print(f"📝 {summary['health_description']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"🧪 Tests: {summary['total_tests']} total, {summary['passed_tests']} passed, {summary['failed_tests']} failed")
        print(f"⏱️  Duration: {summary['duration_minutes']:.1f} minutes")
        print(f"⚠️  Risk Level: {summary['risk_level']}")
        print(f"🔧 Critical Issues: {summary['critical_issues_count']}")
        print(f"💡 Fix Recommendations: {summary['recommendations_count']}")
        
        # Top 5 recommendations
        if report['fix_recommendations']:
            print(f"\n🔧 TOP PRIORITY FIXES:")
            for i, fix in enumerate(report['fix_recommendations'][:5], 1):
                print(f"  {i}. [{fix['severity'].upper()}] {fix['issue_type']}")
                print(f"     {fix['description']}")
        
        print("\n" + "=" * 80)


async def main():
    """Main entry point for advanced test orchestrator"""
    orchestrator = AdvancedTestOrchestrator()
    
    # Parse command line arguments
    env_name = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    
    try:
        results = await orchestrator.run_comprehensive_tests(env_name)
        return results
    except KeyboardInterrupt:
        logger.info("Test run interrupted by user")
        orchestrator.cleanup_environment(env_name)
    except Exception as e:
        logger.error(f"Test run failed: {e}")
        orchestrator.cleanup_environment(env_name)
        raise


if __name__ == "__main__":
    asyncio.run(main())