#!/usr/bin/env python3
"""
Comprehensive Test Runner for NuestrasRecetas.club
Orchestrates all test suites and generates a unified report.
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import os


class TestRunner:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.tests_dir = Path(__file__).parent
        self.project_root = self.tests_dir.parent
    
    def check_server_availability(self) -> bool:
        """Check if the Flask server is running"""
        import requests
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed"""
        dependencies = {
            'requests': False,
            'playwright': False
        }
        
        try:
            import requests
            dependencies['requests'] = True
        except ImportError:
            pass
        
        try:
            import playwright
            dependencies['playwright'] = True
        except ImportError:
            pass
        
        return dependencies
    
    def install_dependencies(self):
        """Install required dependencies"""
        print("📦 Installing required dependencies...")
        
        # Install basic requirements
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests'], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'playwright'], check=True)
        
        # Install Playwright browsers
        subprocess.run([sys.executable, '-m', 'playwright', 'install'], check=True)
        
        print("✅ Dependencies installed successfully")
    
    def create_screenshots_dir(self):
        """Create screenshots directory if it doesn't exist"""
        screenshots_dir = self.project_root / 'screenshots'
        screenshots_dir.mkdir(exist_ok=True)
        return screenshots_dir
    
    async def run_api_tests(self) -> Dict[str, Any]:
        """Run API endpoint tests"""
        print("\n🚀 Running API Endpoint Tests...")
        print("-" * 40)
        
        try:
            # Import and run API tests
            sys.path.insert(0, str(self.tests_dir))
            from test_api_endpoints import NuestrasRecetasAPITester
            
            tester = NuestrasRecetasAPITester(self.base_url)
            tester.run_all_tests()
            
            # Get results
            total_tests = len(tester.test_results)
            passed_tests = len([r for r in tester.test_results if r.success])
            
            return {
                "success": True,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
                "results": tester.test_results,
                "duration": sum(r.response_time for r in tester.test_results) / 1000  # Convert to seconds
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0
            }
    
    async def run_frontend_tests(self) -> Dict[str, Any]:
        """Run frontend functionality tests"""
        print("\n🖥️ Running Frontend Functionality Tests...")
        print("-" * 40)
        
        try:
            # Import and run frontend tests
            sys.path.insert(0, str(self.tests_dir))
            from test_frontend_functionality import NuestrasRecetasFrontendTester
            
            tester = NuestrasRecetasFrontendTester(self.base_url)
            await tester.run_all_tests()
            
            # Get results
            total_tests = len(tester.test_results)
            passed_tests = len([r for r in tester.test_results if r.success])
            
            return {
                "success": True,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
                "results": tester.test_results,
                "duration": sum(r.duration for r in tester.test_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0
            }
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        print("\n🔗 Running Integration Tests...")
        print("-" * 40)
        
        try:
            # Import and run integration tests
            sys.path.insert(0, str(self.tests_dir))
            from test_integration import NuestrasRecetasIntegrationTester
            
            tester = NuestrasRecetasIntegrationTester(self.base_url)
            await tester.run_all_tests()
            
            # Get results
            total_tests = len(tester.test_results)
            passed_tests = len([r for r in tester.test_results if r.success])
            
            return {
                "success": True,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
                "results": tester.test_results,
                "duration": sum(r.duration for r in tester.test_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0
            }
    
    async def run_all_tests(self):
        """Run all test suites"""
        self.start_time = datetime.now()
        
        print("🧪 NUESTRASRECETAS.CLUB - COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        print(f"🎯 Target Server: {self.base_url}")
        print(f"⏰ Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Pre-flight checks
        print("\n🔍 Pre-flight Checks...")
        
        # Check server availability
        if not self.check_server_availability():
            print(f"❌ Server not available at {self.base_url}")
            print("   Make sure the Flask server is running:")
            print("   python app.py")
            return
        else:
            print(f"✅ Server is available at {self.base_url}")
        
        # Check dependencies
        deps = self.check_dependencies()
        missing_deps = [dep for dep, installed in deps.items() if not installed]
        
        if missing_deps:
            print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
            try:
                self.install_dependencies()
            except Exception as e:
                print(f"❌ Failed to install dependencies: {e}")
                return
        else:
            print("✅ All dependencies are installed")
        
        # Create directories
        self.create_screenshots_dir()
        
        # Run test suites
        print("\n🚀 Running Test Suites...")
        
        # Run API tests
        self.test_results['api'] = await self.run_api_tests()
        
        # Run frontend tests
        self.test_results['frontend'] = await self.run_frontend_tests()
        
        # Run integration tests
        self.test_results['integration'] = await self.run_integration_tests()
        
        self.end_time = datetime.now()
        
        # Generate comprehensive report
        self.generate_comprehensive_report()
    
    def generate_comprehensive_report(self):
        """Generate and display comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        # Summary statistics
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for suite_name, results in self.test_results.items():
            if results.get('success', False):
                total_tests += results.get('total_tests', 0)
                total_passed += results.get('passed_tests', 0)
                total_failed += results.get('failed_tests', 0)
        
        overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"⏰ Total Duration: {total_duration:.1f} seconds")
        print(f"🧪 Total Tests: {total_tests}")
        print(f"✅ Passed: {total_passed}")
        print(f"❌ Failed: {total_failed}")
        print(f"📈 Overall Success Rate: {overall_success_rate:.1f}%")
        
        # Detailed results by suite
        print(f"\n📋 RESULTS BY TEST SUITE:")
        for suite_name, results in self.test_results.items():
            suite_display_name = suite_name.title().replace('_', ' ')
            if results.get('success', False):
                success_rate = results.get('success_rate', 0)
                duration = results.get('duration', 0)
                print(f"  {suite_display_name}:")
                print(f"    Tests: {results.get('total_tests', 0)} | "
                      f"Passed: {results.get('passed_tests', 0)} | "
                      f"Failed: {results.get('failed_tests', 0)} | "
                      f"Success: {success_rate:.1f}% | "
                      f"Duration: {duration:.1f}s")
            else:
                print(f"  {suite_display_name}: ❌ FAILED - {results.get('error', 'Unknown error')}")
        
        # Status assessment
        print(f"\n🎯 APPLICATION STATUS ASSESSMENT:")
        
        if overall_success_rate >= 90:
            print("🟢 EXCELLENT - Application is working very well")
        elif overall_success_rate >= 75:
            print("🟡 GOOD - Application is mostly working with minor issues")
        elif overall_success_rate >= 50:
            print("🟠 NEEDS ATTENTION - Several issues need to be addressed")
        else:
            print("🔴 CRITICAL - Major issues require immediate attention")
        
        # Key findings
        print(f"\n🔍 KEY FINDINGS:")
        
        # Check API health
        api_results = self.test_results.get('api', {})
        if api_results.get('success') and api_results.get('success_rate', 0) >= 80:
            print("  ✅ API endpoints are functioning well")
        else:
            print("  ❌ API endpoints have issues")
        
        # Check frontend health
        frontend_results = self.test_results.get('frontend', {})
        if frontend_results.get('success') and frontend_results.get('success_rate', 0) >= 80:
            print("  ✅ Frontend functionality is working well")
        else:
            print("  ❌ Frontend has functionality issues")
        
        # Check integration health
        integration_results = self.test_results.get('integration', {})
        if integration_results.get('success') and integration_results.get('success_rate', 0) >= 80:
            print("  ✅ Frontend and API are well integrated")
        else:
            print("  ❌ Integration issues between frontend and API")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if total_failed > 0:
            print("  1. Review failed tests and fix underlying issues")
            print("  2. Check server logs for additional error details")
            print("  3. Verify all mock data is properly loaded")
        
        if overall_success_rate < 100:
            print("  4. Run individual test suites for detailed debugging")
            print("  5. Check browser console for JavaScript errors")
        
        if overall_success_rate >= 90:
            print("  • Application is ready for production deployment")
            print("  • Consider adding more edge case tests")
        
        # File outputs
        print(f"\n📁 TEST ARTIFACTS:")
        print("  • API Test Results: api_test_results.json")
        print("  • Frontend Test Results: frontend_test_results.json")
        print("  • Integration Test Results: integration_test_results.json")
        if Path('screenshots').exists():
            print("  • Screenshots: screenshots/ directory")
        
        print(f"\n⏰ Test run completed at: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Save comprehensive results
        self.save_comprehensive_results()
    
    def save_comprehensive_results(self):
        """Save comprehensive test results to JSON"""
        comprehensive_results = {
            "test_run_metadata": {
                "timestamp": self.start_time.isoformat(),
                "duration_seconds": (self.end_time - self.start_time).total_seconds(),
                "base_url": self.base_url,
                "total_tests": sum(r.get('total_tests', 0) for r in self.test_results.values() if r.get('success')),
                "total_passed": sum(r.get('passed_tests', 0) for r in self.test_results.values() if r.get('success')),
                "total_failed": sum(r.get('failed_tests', 0) for r in self.test_results.values() if r.get('success')),
            },
            "test_suites": self.test_results
        }
        
        with open('comprehensive_test_results.json', 'w') as f:
            json.dump(comprehensive_results, f, indent=2, default=str)
        
        print("\n💾 Comprehensive results saved to: comprehensive_test_results.json")


async def main():
    """Main entry point"""
    # Allow custom base URL via command line argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    
    runner = TestRunner(base_url)
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())