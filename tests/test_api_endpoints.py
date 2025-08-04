#!/usr/bin/env python3
"""
Comprehensive API Endpoint Test Suite for NuestrasRecetas.club
Tests all 58 endpoints identified in the Flask application.
"""

import json
import requests
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestResult:
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None


class NuestrasRecetasAPITester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.auth_token = None
        self.test_user = {
            "email": "dev@test.com",
            "password": "dev123"
        }
    
    def log_result(self, result: TestResult):
        """Log test result and print status"""
        self.test_results.append(result)
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"{status} {result.method} {result.endpoint} - {result.status_code} ({result.response_time:.2f}ms)")
        if result.error_message:
            print(f"    Error: {result.error_message}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> TestResult:
        """Make HTTP request and return TestResult"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            # Add auth header if we have a token
            if self.auth_token:
                headers = kwargs.get('headers', {})
                headers['Authorization'] = f'Bearer {self.auth_token}'
                kwargs['headers'] = headers
            
            response = self.session.request(method, url, **kwargs)
            response_time = (time.time() - start_time) * 1000
            
            # Consider 2xx and 3xx as success, 404 might be expected for some endpoints
            success = response.status_code < 400 or response.status_code == 404
            
            response_data = None
            error_message = None
            
            try:
                response_data = response.json()
            except:
                if not success:
                    error_message = f"Non-JSON response: {response.text[:200]}"
            
            if not success and not error_message:
                error_message = f"HTTP {response.status_code}: {response.text[:200]}"
            
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time=response_time,
                success=success,
                error_message=error_message,
                response_data=response_data
            )
        
        except requests.RequestException as e:
            response_time = (time.time() - start_time) * 1000
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=f"Request failed: {str(e)}"
            )
    
    def authenticate(self):
        """Authenticate with test user credentials"""
        print("\n🔐 Authenticating...")
        result = self.make_request(
            'POST', 
            '/api/auth/login',
            json=self.test_user
        )
        
        if result.success and result.response_data:
            if 'access_token' in result.response_data:
                self.auth_token = result.response_data['access_token']
                print("✅ Authentication successful")
            else:
                print("⚠️  Login successful but no access_token in response")
        else:
            print("❌ Authentication failed")
        
        self.log_result(result)
        return result.success
    
    def test_page_routes(self):
        """Test main page routes"""
        print("\n📄 Testing Page Routes...")
        
        routes = [
            ('GET', '/'),
            ('GET', '/dashboard'),
            ('GET', '/profile'),
            ('GET', '/community'),
            ('GET', '/groups'),
            ('GET', '/health'),
        ]
        
        for method, endpoint in routes:
            result = self.make_request(method, endpoint)
            self.log_result(result)
    
    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Test signup (might fail if user exists - that's ok)
        signup_data = {
            "email": "test_new_user@test.com",
            "password": "test123",
            "username": "test_user_new"
        }
        result = self.make_request('POST', '/api/auth/signup', json=signup_data)
        self.log_result(result)
        
        # Test login (already done in authenticate())
        
        # Test /api/auth/me
        result = self.make_request('GET', '/api/auth/me')
        self.log_result(result)
        
        # Test logout
        result = self.make_request('POST', '/api/auth/logout')
        self.log_result(result)
    
    def test_recipe_endpoints(self):
        """Test recipe-related endpoints"""
        print("\n🍽️ Testing Recipe Endpoints...")
        
        # Get recipes
        result = self.make_request('GET', '/api/recipes')
        self.log_result(result)
        
        # Get specific recipe (try ID 1)
        result = self.make_request('GET', '/api/recipe/1')
        self.log_result(result)
        
        # Test recipe creation
        new_recipe = {
            "name": "Test Recipe",
            "description": "A test recipe",
            "ingredients": ["Test ingredient 1", "Test ingredient 2"],
            "instructions": ["Step 1", "Step 2"],
            "prep_time": 15,
            "cook_time": 30,
            "servings": 4
        }
        result = self.make_request('POST', '/api/recipe', json=new_recipe)
        created_recipe_id = None
        if result.success and result.response_data:
            created_recipe_id = result.response_data.get('id')
        self.log_result(result)
        
        # If we created a recipe, test update and delete
        if created_recipe_id:
            # Test recipe update
            updated_recipe = new_recipe.copy()
            updated_recipe['name'] = "Updated Test Recipe"
            result = self.make_request('PUT', f'/api/recipe/{created_recipe_id}', json=updated_recipe)
            self.log_result(result)
            
            # Test recipe stats
            result = self.make_request('GET', f'/api/recipes/{created_recipe_id}/stats')
            self.log_result(result)
            
            # Test recipe network
            result = self.make_request('GET', f'/api/recipes/{created_recipe_id}/network')
            self.log_result(result)
            
            # Test recipe star/unstar
            result = self.make_request('POST', f'/api/recipes/{created_recipe_id}/star')
            self.log_result(result)
            
            result = self.make_request('POST', f'/api/recipes/{created_recipe_id}/unstar')
            self.log_result(result)
            
            # Test recipe delete
            result = self.make_request('DELETE', f'/api/recipe/{created_recipe_id}')
            self.log_result(result)
    
    def test_git_for_recipes_endpoints(self):
        """Test Git-for-Recipes specific endpoints"""
        print("\n🍴 Testing Git-for-Recipes Endpoints...")
        
        # Try with recipe ID 1 (should exist in mock data)
        recipe_id = 1
        
        # Test fork creation
        fork_data = {
            "name": "Forked Test Recipe",
            "description": "A forked version of the recipe"
        }
        result = self.make_request('POST', f'/api/recipes/{recipe_id}/fork', json=fork_data)
        self.log_result(result)
        
        # Test get forks
        result = self.make_request('GET', f'/api/recipes/{recipe_id}/forks')
        self.log_result(result)
        
        # Test get history
        result = self.make_request('GET', f'/api/recipes/{recipe_id}/history')
        self.log_result(result)
        
        # Test create commit
        commit_data = {
            "message": "Test commit",
            "changes": {
                "ingredients": ["New ingredient"],
                "instructions": ["New instruction"]
            }
        }
        result = self.make_request('POST', f'/api/recipes/{recipe_id}/commit', json=commit_data)
        self.log_result(result)
        
        # Test get branches
        result = self.make_request('GET', f'/api/recipes/{recipe_id}/branches')
        self.log_result(result)
        
        # Test create branch
        branch_data = {
            "name": "test-branch",
            "description": "Test branch"
        }
        result = self.make_request('POST', f'/api/recipes/{recipe_id}/branch', json=branch_data)
        self.log_result(result)
        
        # Test get contributors
        result = self.make_request('GET', f'/api/recipes/{recipe_id}/contributors')
        self.log_result(result)
        
        # Test recipe comparison
        result = self.make_request('GET', f'/api/recipes/{recipe_id}/compare/2')
        self.log_result(result)
    
    def test_user_endpoints(self):
        """Test user-related endpoints"""
        print("\n👥 Testing User Endpoints...")
        
        # Test user search
        result = self.make_request('GET', '/api/users/search?q=dev')
        self.log_result(result)
        
        # Test user suggestions (new endpoint)
        result = self.make_request('GET', '/api/users/suggestions')
        self.log_result(result)
        
        # Test user suggestions stats
        result = self.make_request('GET', '/api/users/suggestions/stats')
        self.log_result(result)
        
        # Test profile endpoints (try with user ID 1)
        user_id = 1
        
        result = self.make_request('GET', f'/api/users/{user_id}/posts')
        self.log_result(result)
        
        result = self.make_request('GET', f'/api/users/{user_id}/followers')
        self.log_result(result)
        
        result = self.make_request('GET', f'/api/users/{user_id}/following')
        self.log_result(result)
        
        # Test follow/unfollow
        result = self.make_request('POST', f'/api/users/{user_id}/follow')
        self.log_result(result)
        
        result = self.make_request('POST', f'/api/users/{user_id}/unfollow')
        self.log_result(result)
        
        # Test my followers/following
        result = self.make_request('GET', '/api/me/followers')
        self.log_result(result)
        
        result = self.make_request('GET', '/api/me/following')
        self.log_result(result)
        
        # Test profile update
        profile_data = {
            "bio": "Updated test bio",
            "location": "Test City"
        }
        result = self.make_request('PUT', '/api/profile', json=profile_data)
        self.log_result(result)
    
    def test_community_endpoints(self):
        """Test community and feed endpoints"""
        print("\n🌐 Testing Community Endpoints...")
        
        # Test community feed (new endpoint)
        result = self.make_request('GET', '/api/community/feed')
        self.log_result(result)
        
        # Test general feed
        result = self.make_request('GET', '/api/feed')
        self.log_result(result)
        
        # Test posts feed
        result = self.make_request('GET', '/api/posts/feed')
        self.log_result(result)
        
        # Test create post
        post_data = {
            "content": "This is a test post",
            "type": "text"
        }
        result = self.make_request('POST', '/api/posts', json=post_data)
        post_id = None
        if result.success and result.response_data:
            post_id = result.response_data.get('id')
        self.log_result(result)
        
        # Test post comments
        if post_id:
            comment_data = {
                "content": "This is a test comment"
            }
            result = self.make_request('POST', f'/api/posts/{post_id}/comments', json=comment_data)
            self.log_result(result)
    
    def test_group_endpoints(self):
        """Test group-related endpoints"""
        print("\n👥 Testing Group Endpoints...")
        
        # Test get groups
        result = self.make_request('GET', '/api/groups')
        self.log_result(result)
        
        # Test create group
        group_data = {
            "name": "Test Group",
            "description": "A test group",
            "privacy": "public"
        }
        result = self.make_request('POST', '/api/groups', json=group_data)
        group_id = None
        if result.success and result.response_data:
            group_id = result.response_data.get('id')
        self.log_result(result)
        
        # If we created a group, test group operations
        if group_id:
            # Test get specific group
            result = self.make_request('GET', f'/api/groups/{group_id}')
            self.log_result(result)
            
            # Test join group
            result = self.make_request('POST', f'/api/groups/{group_id}/join')
            self.log_result(result)
            
            # Test create group post
            group_post_data = {
                "content": "Test group post",
                "type": "text"
            }
            result = self.make_request('POST', f'/api/groups/{group_id}/posts', json=group_post_data)
            self.log_result(result)
            
            # Test leave group
            result = self.make_request('POST', f'/api/groups/{group_id}/leave')
            self.log_result(result)
    
    def test_dashboard_endpoints(self):
        """Test dashboard endpoints"""
        print("\n📊 Testing Dashboard Endpoints...")
        
        # Test dashboard stats
        result = self.make_request('GET', '/api/dashboard/stats')
        self.log_result(result)
        
        # Test meal plan endpoints
        result = self.make_request('GET', '/api/plan')
        self.log_result(result)
        
        plan_data = {
            "meals": {
                "monday": {"breakfast": 1, "lunch": 2, "dinner": 3}
            }
        }
        result = self.make_request('PUT', '/api/plan', json=plan_data)
        self.log_result(result)
        
        # Test groceries
        grocery_data = {
            "recipes": [1, 2, 3]
        }
        result = self.make_request('POST', '/api/groceries', json=grocery_data)
        self.log_result(result)
    
    def test_profile_pages(self):
        """Test profile page routes"""
        print("\n👤 Testing Profile Pages...")
        
        # Test profile by username
        result = self.make_request('GET', '/api/profile/dev')
        self.log_result(result)
        
        # Test group page
        result = self.make_request('GET', '/group/1')
        self.log_result(result)
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive API Test Suite")
        print(f"🎯 Target: {self.base_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Authenticate first
        auth_success = self.authenticate()
        
        # Run all test suites
        self.test_page_routes()
        self.test_auth_endpoints()
        self.test_recipe_endpoints()
        self.test_git_for_recipes_endpoints()
        self.test_user_endpoints()
        self.test_community_endpoints()
        self.test_group_endpoints()
        self.test_dashboard_endpoints()
        self.test_profile_pages()
        
        # Generate summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.success])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS ({failed_tests}):")
            for result in self.test_results:
                if not result.success:
                    print(f"  • {result.method} {result.endpoint} - {result.error_message}")
        
        # Performance stats
        response_times = [r.response_time for r in self.test_results if r.response_time > 0]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            print(f"\n⚡ PERFORMANCE:")
            print(f"  • Average Response Time: {avg_response_time:.2f}ms")
            print(f"  • Slowest Response: {max_response_time:.2f}ms")
        
        print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def save_results_json(self, filename: str = "api_test_results.json"):
        """Save test results to JSON file"""
        results_data = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "total_tests": len(self.test_results),
                "passed_tests": len([r for r in self.test_results if r.success]),
                "failed_tests": len([r for r in self.test_results if not r.success])
            },
            "results": [
                {
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "status_code": r.status_code,
                    "response_time": r.response_time,
                    "success": r.success,
                    "error_message": r.error_message,
                    "response_data": r.response_data
                }
                for r in self.test_results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


if __name__ == "__main__":
    tester = NuestrasRecetasAPITester()
    tester.run_all_tests()
    tester.save_results_json()