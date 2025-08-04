#!/usr/bin/env python3
"""
Final Test Runner - Comprehensive testing for NuestrasRecetas
"""

import asyncio
import json
import sys
import os
from datetime import datetime
import aiohttp
import requests
from typing import Dict, List, Any

# Add tests directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))


class ComprehensiveTestRunner:
    """Run all tests and generate reports"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "server_health": {},
            "api_tests": {},
            "frontend_tests": {},
            "database_tests": {},
            "performance_tests": {},
            "summary": {}
        }
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("\n" + "="*80)
        print("🚀 NUESTRASRECETAS COMPREHENSIVE TEST SUITE")
        print("="*80)
        print(f"Timestamp: {self.results['timestamp']}")
        print("="*80 + "\n")
        
        # 1. Test server health
        print("📋 Testing server health...")
        await self.test_server_health()
        
        # 2. Test API endpoints
        print("\n🔌 Testing API endpoints...")
        await self.test_api_endpoints()
        
        # 3. Test frontend routes
        print("\n🖥️  Testing frontend routes...")
        await self.test_frontend_routes()
        
        # 4. Test database connectivity
        print("\n💾 Testing database connectivity...")
        await self.test_database()
        
        # 5. Basic performance tests
        print("\n⚡ Running performance tests...")
        await self.test_performance()
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
        
        # Display results
        self.display_results()
        
        return self.results
    
    async def test_server_health(self):
        """Test server health endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as resp:
                    data = await resp.json()
                    self.results["server_health"] = {
                        "status": "passed" if resp.status == 200 else "failed",
                        "response": data,
                        "supabase_connected": data.get("supabase") == "enabled",
                        "database_connected": data.get("database") == "connected",
                        "profile_count": data.get("profiles_count", 0)
                    }
        except Exception as e:
            self.results["server_health"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_api_endpoints(self):
        """Test API endpoints"""
        endpoints = [
            # Public endpoints
            {"method": "GET", "path": "/api/recipes", "auth": False},
            
            # Protected endpoints (will return 401 without auth)
            {"method": "GET", "path": "/api/activity", "auth": True},
            {"method": "GET", "path": "/api/community/feed", "auth": True},
            {"method": "GET", "path": "/api/users/suggestions", "auth": True},
            {"method": "GET", "path": "/api/user/preferences", "auth": True},
        ]
        
        results = []
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    url = f"{self.base_url}{endpoint['path']}"
                    async with session.request(endpoint["method"], url) as resp:
                        result = {
                            "endpoint": f"{endpoint['method']} {endpoint['path']}",
                            "status_code": resp.status,
                            "auth_required": endpoint["auth"],
                            "content_type": resp.headers.get('Content-Type', '')
                        }
                        
                        # Determine if test passed
                        if endpoint["auth"] and resp.status == 401:
                            result["status"] = "passed"  # Expected 401 for protected endpoints
                            result["note"] = "Protected endpoint correctly returns 401"
                        elif not endpoint["auth"] and resp.status in [200, 201, 204]:
                            result["status"] = "passed"
                        else:
                            result["status"] = "failed"
                            
                        results.append(result)
                except Exception as e:
                    results.append({
                        "endpoint": f"{endpoint['method']} {endpoint['path']}",
                        "status": "failed",
                        "error": str(e)
                    })
        
        total = len(results)
        passed = len([r for r in results if r["status"] == "passed"])
        
        self.results["api_tests"] = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "tests": results
        }
    
    async def test_frontend_routes(self):
        """Test frontend HTML routes"""
        routes = [
            # Public routes (should return 200)
            {"path": "/", "auth": False},
            {"path": "/recipes", "auth": False},
            {"path": "/community", "auth": False},  # Public community discovery
            {"path": "/groups", "auth": False},     # Public group discovery
            
            # Protected routes (should return 401 without auth)
            {"path": "/activity", "auth": True},
            
            # Special case: /profile redirects when not authenticated (302 expected)
            {"path": "/profile", "auth": "redirect"},
        ]
        
        results = []
        async with aiohttp.ClientSession() as session:
            for route_info in routes:
                route = route_info["path"]
                auth_required = route_info["auth"]
                try:
                    async with session.get(f"{self.base_url}{route}", allow_redirects=False) as resp:
                        text = await resp.text()
                        result = {
                            "route": route,
                            "status_code": resp.status,
                            "auth_required": auth_required,
                            "has_html": "<html" in text.lower(),
                            "size": len(text)
                        }
                        
                        # Determine if test passed
                        if auth_required == True and resp.status == 401:
                            result["status"] = "passed"  # Expected 401 for protected routes
                            result["note"] = "Protected route correctly returns 401"
                        elif auth_required == "redirect" and resp.status == 302:
                            result["status"] = "passed"  # Expected 302 for profile redirect
                            result["note"] = "Profile route correctly redirects when not authenticated"
                        elif auth_required == False and resp.status == 200:
                            result["status"] = "passed"
                        else:
                            result["status"] = "failed"
                            
                        results.append(result)
                except Exception as e:
                    results.append({
                        "route": route,
                        "status": "failed",
                        "error": str(e)
                    })
        
        total = len(results)
        passed = len([r for r in results if r["status"] == "passed"])
        
        self.results["frontend_tests"] = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "tests": results
        }
    
    async def test_database(self):
        """Test database connectivity through API"""
        try:
            # Use the health endpoint data
            if self.results["server_health"].get("database_connected"):
                self.results["database_tests"] = {
                    "status": "passed",
                    "connection": "active",
                    "profile_count": self.results["server_health"].get("profile_count", 0),
                    "supabase_enabled": self.results["server_health"].get("supabase_connected", False)
                }
            else:
                self.results["database_tests"] = {
                    "status": "failed",
                    "error": "Database not connected according to health check"
                }
        except Exception as e:
            self.results["database_tests"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_performance(self):
        """Basic performance tests"""
        endpoints = [
            {"path": "/", "auth": False},
            {"path": "/health", "auth": False},
            {"path": "/api/recipes", "auth": False},
            {"path": "/api/activity", "auth": True}  # This will return 401, which is expected
        ]
        results = []
        
        async with aiohttp.ClientSession() as session:
            for endpoint_info in endpoints:
                endpoint = endpoint_info["path"]
                auth_required = endpoint_info["auth"]
                try:
                    start_time = datetime.now()
                    async with session.get(f"{self.base_url}{endpoint}") as resp:
                        end_time = datetime.now()
                        response_time = (end_time - start_time).total_seconds() * 1000
                        
                        # For performance testing, we care about response time regardless of auth
                        performance_status = "good" if response_time < 200 else "slow" if response_time < 500 else "poor"
                        
                        results.append({
                            "endpoint": endpoint,
                            "response_time_ms": round(response_time, 2),
                            "status_code": resp.status,
                            "auth_required": auth_required,
                            "performance": performance_status,
                            "note": "Protected endpoint - 401 expected" if auth_required and resp.status == 401 else None
                        })
                except Exception as e:
                    results.append({
                        "endpoint": endpoint,
                        "error": str(e)
                    })
        
        avg_response_time = sum(r.get("response_time_ms", 0) for r in results) / len(results) if results else 0
        
        self.results["performance_tests"] = {
            "average_response_time_ms": round(avg_response_time, 2),
            "tests": results
        }
    
    def generate_summary(self):
        """Generate test summary"""
        total_tests = 0
        total_passed = 0
        
        # Count API tests
        if "api_tests" in self.results and "total" in self.results["api_tests"]:
            total_tests += self.results["api_tests"]["total"]
            total_passed += self.results["api_tests"]["passed"]
        
        # Count frontend tests
        if "frontend_tests" in self.results and "total" in self.results["frontend_tests"]:
            total_tests += self.results["frontend_tests"]["total"]
            total_passed += self.results["frontend_tests"]["passed"]
        
        # Count other tests
        if self.results.get("server_health", {}).get("status") == "passed":
            total_tests += 1
            total_passed += 1
        else:
            total_tests += 1
            
        if self.results.get("database_tests", {}).get("status") == "passed":
            total_tests += 1
            total_passed += 1
        else:
            total_tests += 1
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_tests - total_passed,
            "success_rate": round(success_rate, 2),
            "status": "PASSED" if success_rate >= 70 else "FAILED"
        }
    
    def save_results(self):
        """Save test results to file"""
        filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Results saved to: {filename}")
    
    def display_results(self):
        """Display test results"""
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        
        summary = self.results["summary"]
        print(f"\nTotal Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"\nOverall Status: {summary['status']}")
        
        # Server Health
        print("\n📋 Server Health:")
        health = self.results["server_health"]
        if health.get("status") == "passed":
            print(f"  ✅ Server is healthy")
            print(f"  ✅ Supabase: {health.get('supabase_connected', False)}")
            print(f"  ✅ Database: {health.get('database_connected', False)}")
            print(f"  ✅ Profiles: {health.get('profile_count', 0)}")
        else:
            print(f"  ❌ Server health check failed: {health.get('error', 'Unknown')}")
        
        # API Tests
        print("\n🔌 API Endpoints:")
        api = self.results["api_tests"]
        if api:
            print(f"  Total: {api['total']} | Passed: {api['passed']} | Failed: {api['failed']}")
            for test in api.get("tests", []):
                status_icon = "✅" if test["status"] == "passed" else "❌"
                auth_info = " (Auth Required)" if test.get("auth_required") else " (Public)"
                note = f" - {test['note']}" if test.get("note") else ""
                print(f"  {status_icon} {test['endpoint']}{auth_info} - {test.get('status_code', 'error')}{note}")
        
        # Frontend Tests
        print("\n🖥️  Frontend Routes:")
        frontend = self.results["frontend_tests"]
        if frontend:
            print(f"  Total: {frontend['total']} | Passed: {frontend['passed']} | Failed: {frontend['failed']}")
            for test in frontend.get("tests", []):
                status_icon = "✅" if test["status"] == "passed" else "❌"
                if test.get("auth_required") == True:
                    auth_info = " (Auth Required)"
                elif test.get("auth_required") == "redirect":
                    auth_info = " (Redirect)"
                else:
                    auth_info = " (Public)"
                note = f" - {test['note']}" if test.get("note") else ""
                print(f"  {status_icon} {test['route']}{auth_info} - {test.get('status_code', 'error')}{note}")
        
        # Performance
        print("\n⚡ Performance:")
        perf = self.results["performance_tests"]
        if perf:
            print(f"  Average Response Time: {perf['average_response_time_ms']}ms")
        
        print("\n" + "="*80)


async def main():
    """Run the test suite"""
    runner = ComprehensiveTestRunner()
    results = await runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if results["summary"]["status"] == "PASSED" else 1)


if __name__ == "__main__":
    asyncio.run(main())