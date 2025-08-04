#!/usr/bin/env python3
"""
Integration Test Suite for NuestrasRecetas.club
Tests end-to-end workflows combining API and frontend functionality.
Validates user session persistence, data consistency, and mock data integration.
"""

import asyncio
import json
import requests
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class IntegrationTestResult:
    test_name: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error_message: Optional[str] = None


class NuestrasRecetasIntegrationTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.test_results: List[IntegrationTestResult] = []
        self.session = requests.Session()
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.auth_token = None
        self.test_credentials = {
            "email": "dev@test.com",
            "password": "dev123"
        }
    
    async def setup_browser(self):
        """Initialize browser and page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False, slow_mo=300)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        self.page = await self.context.new_page()
        
        # Capture console messages for debugging
        self.page.on("console", lambda msg: print(f"🖥️  Console: {msg.text}"))
    
    async def cleanup_browser(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
    
    def log_result(self, result: IntegrationTestResult):
        """Log test result"""
        self.test_results.append(result)
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"{status} {result.test_name} ({result.duration:.2f}s)")
        if result.error_message:
            print(f"    Error: {result.error_message}")
        if result.details:
            for key, value in result.details.items():
                print(f"    {key}: {value}")
    
    def api_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request with authentication if available"""
        url = f"{self.base_url}{endpoint}"
        if self.auth_token:
            headers = kwargs.get('headers', {})
            headers['Authorization'] = f'Bearer {self.auth_token}'
            kwargs['headers'] = headers
        return self.session.request(method, url, **kwargs)
    
    async def test_user_authentication_flow(self) -> IntegrationTestResult:
        """Test complete user authentication flow (API + Frontend)"""
        start_time = time.time()
        test_name = "User Authentication Flow Integration"
        details = {}
        
        try:
            # Step 1: API Login
            api_response = self.api_request('POST', '/api/auth/login', json=self.test_credentials)
            details['api_login_status'] = api_response.status_code
            
            if api_response.status_code == 200:
                api_data = api_response.json()
                if 'access_token' in api_data:
                    self.auth_token = api_data['access_token']
                    details['api_token_received'] = True
                else:
                    details['api_token_received'] = False
            
            # Step 2: Verify API /me endpoint
            me_response = self.api_request('GET', '/api/auth/me')
            details['api_me_status'] = me_response.status_code
            
            if me_response.status_code == 200:
                user_data = me_response.json()
                details['api_user_data'] = {
                    'email': user_data.get('email'),
                    'username': user_data.get('username'),
                    'id': user_data.get('id')
                }
            
            # Step 3: Frontend Login
            await self.page.goto(self.base_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Look for login form
            login_button = self.page.locator('button:has-text("Login"), button:has-text("Iniciar Sesión")')
            if await login_button.count() > 0:
                await login_button.first.click()
                await asyncio.sleep(1)
            
            # Fill login form
            await self.page.locator('input[type="email"]').fill(self.test_credentials["email"])
            await self.page.locator('input[type="password"]').fill(self.test_credentials["password"])
            
            # Submit form
            await self.page.locator('button[type="submit"], button:has-text("Login")').click()
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(2)
            
            # Step 4: Verify frontend shows user is logged in
            current_url = self.page.url
            details['frontend_redirect_url'] = current_url
            
            # Check for user-specific content
            user_indicators = [
                '.user-profile', '.dashboard', 'button:has-text("Logout")',
                '.user-menu', '[data-user-authenticated="true"]'
            ]
            
            frontend_login_success = False
            for indicator in user_indicators:
                if await self.page.locator(indicator).count() > 0:
                    frontend_login_success = True
                    break
            
            details['frontend_login_success'] = frontend_login_success
            
            # Step 5: Check user name display (should not be "Bienvenido")
            welcome_elements = await self.page.locator('text="Bienvenido"').count()
            details['shows_bienvenido'] = welcome_elements > 0
            
            # Step 6: Test session persistence - refresh page
            await self.page.reload()
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)
            
            # Check if still logged in after refresh
            still_logged_in = False
            for indicator in user_indicators:
                if await self.page.locator(indicator).count() > 0:
                    still_logged_in = True
                    break
            
            details['session_persists'] = still_logged_in
            
            # Success criteria
            success = (
                api_response.status_code == 200 and
                me_response.status_code == 200 and
                frontend_login_success and
                still_logged_in
            )
            
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, success, duration, details)
            
        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, False, duration, details, str(e))
    
    async def test_recipe_data_consistency(self) -> IntegrationTestResult:
        """Test that recipe data is consistent between API and frontend"""
        start_time = time.time()
        test_name = "Recipe Data Consistency"
        details = {}
        
        try:
            # Step 1: Get recipes from API
            api_response = self.api_request('GET', '/api/recipes')
            details['api_recipes_status'] = api_response.status_code
            
            api_recipes = []
            if api_response.status_code == 200:
                api_recipes = api_response.json()
                details['api_recipes_count'] = len(api_recipes)
                details['api_sample_recipe'] = api_recipes[0] if api_recipes else None
            
            # Step 2: Navigate to dashboard/recipes page
            await self.page.goto(f"{self.base_url}/dashboard")
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Step 3: Count recipes displayed in frontend
            recipe_elements = await self.page.locator('.recipe-card, .recipe-item, [data-recipe-id]').count()
            details['frontend_recipes_count'] = recipe_elements
            
            # Step 4: Check if recipe names match
            if api_recipes and recipe_elements > 0:
                # Get first recipe name from API
                first_recipe_name = api_recipes[0].get('name', '') if api_recipes else ''
                
                # Check if this name appears in the frontend
                name_found = await self.page.locator(f'text="{first_recipe_name}"').count() > 0
                details['first_recipe_name_matches'] = name_found
                details['first_recipe_name'] = first_recipe_name
            
            # Step 5: Test individual recipe page
            if api_recipes:
                first_recipe_id = api_recipes[0].get('id')
                if first_recipe_id:
                    # Get recipe details from API
                    recipe_detail_response = self.api_request('GET', f'/api/recipe/{first_recipe_id}')
                    details['api_recipe_detail_status'] = recipe_detail_response.status_code
                    
                    if recipe_detail_response.status_code == 200:
                        recipe_detail = recipe_detail_response.json()
                        details['api_recipe_detail'] = {
                            'name': recipe_detail.get('name'),
                            'description': recipe_detail.get('description'),
                            'ingredients_count': len(recipe_detail.get('ingredients', []))
                        }
            
            # Success criteria
            success = (
                api_response.status_code == 200 and
                len(api_recipes) > 0 and
                recipe_elements > 0
            )
            
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, success, duration, details)
            
        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, False, duration, details, str(e))
    
    async def test_community_feed_integration(self) -> IntegrationTestResult:
        """Test community feed API and frontend integration"""
        start_time = time.time()
        test_name = "Community Feed Integration"
        details = {}
        
        try:
            # Step 1: Get community feed from API (new endpoint)
            api_response = self.api_request('GET', '/api/community/feed')
            details['api_community_feed_status'] = api_response.status_code
            
            feed_items = []
            if api_response.status_code == 200:
                feed_items = api_response.json()
                details['api_feed_items_count'] = len(feed_items)
                details['api_sample_feed_item'] = feed_items[0] if feed_items else None
            
            # Step 2: Navigate to community page
            await self.page.goto(f"{self.base_url}/community")
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Step 3: Check if feed items are displayed
            feed_elements = await self.page.locator('.feed-item, .post-item, .community-post').count()
            details['frontend_feed_items_count'] = feed_elements
            
            # Step 4: Test user suggestions endpoint
            suggestions_response = self.api_request('GET', '/api/users/suggestions')
            details['api_user_suggestions_status'] = suggestions_response.status_code
            
            if suggestions_response.status_code == 200:
                suggestions = suggestions_response.json()
                details['api_user_suggestions_count'] = len(suggestions)
            
            # Step 5: Test posting to community (if possible)
            post_form = self.page.locator('textarea[placeholder*="post"], textarea[placeholder*="share"]')
            if await post_form.count() > 0:
                await post_form.fill("Test integration post")
                
                # Look for submit button
                submit_btn = self.page.locator('button:has-text("Post"), button:has-text("Share")')
                if await submit_btn.count() > 0:
                    await submit_btn.click()
                    await asyncio.sleep(2)
                    details['post_form_tested'] = True
            
            # Success criteria
            success = api_response.status_code == 200
            
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, success, duration, details)
            
        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, False, duration, details, str(e))
    
    async def test_user_profile_consistency(self) -> IntegrationTestResult:
        """Test user profile data consistency between API and frontend"""
        start_time = time.time()
        test_name = "User Profile Consistency"
        details = {}
        
        try:
            # Step 1: Get user profile from API
            profile_response = self.api_request('GET', '/api/profile/dev')
            details['api_profile_status'] = profile_response.status_code
            
            profile_data = {}
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                details['api_profile_data'] = {
                    'username': profile_data.get('username'),
                    'email': profile_data.get('email'),
                    'bio': profile_data.get('bio'),
                    'recipes_count': profile_data.get('recipes_count', 0)
                }
            
            # Step 2: Navigate to profile page
            await self.page.goto(f"{self.base_url}/profile")
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Step 3: Check if profile data is displayed correctly
            username_element = await self.page.locator('.username, .user-name, h1, h2').first.text_content()
            details['frontend_username'] = username_element.strip() if username_element else None
            
            # Check that it's not showing "Bienvenido"
            shows_welcome = await self.page.locator('text="Bienvenido"').count() > 0
            details['shows_generic_welcome'] = shows_welcome
            
            # Step 4: Check profile stats
            stats_elements = await self.page.locator('.stat, .stats, .profile-stat').count()
            details['frontend_stats_count'] = stats_elements
            
            # Step 5: Test profile update
            edit_button = self.page.locator('button:has-text("Edit"), button:has-text("Editar")')
            if await edit_button.count() > 0:
                await edit_button.click()
                await asyncio.sleep(1)
                
                # Test updating bio
                bio_field = self.page.locator('textarea[name="bio"], textarea[placeholder*="bio"]')
                if await bio_field.count() > 0:
                    test_bio = f"Integration test bio - {datetime.now().strftime('%H:%M:%S')}"
                    await bio_field.fill(test_bio)
                    
                    # Save changes
                    save_button = self.page.locator('button:has-text("Save"), button[type="submit"]')
                    if await save_button.count() > 0:
                        await save_button.click()
                        await asyncio.sleep(2)
                        details['profile_update_tested'] = True
            
            # Success criteria
            success = (
                profile_response.status_code == 200 and
                not shows_welcome and
                username_element and "bienvenido" not in username_element.lower()
            )
            
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, success, duration, details)
            
        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, False, duration, details, str(e))
    
    async def test_mock_data_integration(self) -> IntegrationTestResult:
        """Test that mock data is properly integrated and displayed"""
        start_time = time.time()
        test_name = "Mock Data Integration"
        details = {}
        
        try:
            # Step 1: Test dashboard stats
            stats_response = self.api_request('GET', '/api/dashboard/stats')
            details['api_dashboard_stats_status'] = stats_response.status_code
            
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                details['api_dashboard_stats'] = stats_data
            
            # Step 2: Navigate to dashboard
            await self.page.goto(f"{self.base_url}/dashboard")
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Step 3: Check if stats are displayed
            stat_numbers = await self.page.locator('.stat-number, .count, .metric-value').count()
            details['frontend_stats_displayed'] = stat_numbers
            
            # Step 4: Test recipe data
            recipes_response = self.api_request('GET', '/api/recipes')
            if recipes_response.status_code == 200:
                recipes = recipes_response.json()
                details['total_mock_recipes'] = len(recipes)
                
                # Check for mock data characteristics
                mock_recipe_names = [r.get('name', '') for r in recipes if 'mock' in r.get('name', '').lower()]
                details['mock_recipes_found'] = len(mock_recipe_names)
            
            # Step 5: Test groups data
            groups_response = self.api_request('GET', '/api/groups')
            if groups_response.status_code == 200:
                groups = groups_response.json()
                details['total_mock_groups'] = len(groups)
            
            # Step 6: Test user suggestions
            suggestions_response = self.api_request('GET', '/api/users/suggestions')
            if suggestions_response.status_code == 200:
                suggestions = suggestions_response.json()
                details['total_user_suggestions'] = len(suggestions)
            
            # Success criteria - check that we have mock data
            success = (
                stats_response.status_code == 200 and
                recipes_response.status_code == 200 and
                len(recipes) > 0
            )
            
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, success, duration, details)
            
        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, False, duration, details, str(e))
    
    async def test_git_for_recipes_workflow(self) -> IntegrationTestResult:
        """Test Git-for-Recipes workflow integration"""
        start_time = time.time()
        test_name = "Git-for-Recipes Workflow"
        details = {}
        
        try:
            # Step 1: Get recipe for testing
            recipes_response = self.api_request('GET', '/api/recipes')
            if recipes_response.status_code != 200:
                raise Exception("Could not get recipes for testing")
            
            recipes = recipes_response.json()
            if not recipes:
                raise Exception("No recipes available for testing")
            
            test_recipe_id = recipes[0]['id']
            details['test_recipe_id'] = test_recipe_id
            
            # Step 2: Test fork creation
            fork_data = {
                "name": f"Integration Test Fork - {datetime.now().strftime('%H:%M:%S')}",
                "description": "Fork created during integration testing"
            }
            
            fork_response = self.api_request('POST', f'/api/recipes/{test_recipe_id}/fork', json=fork_data)
            details['fork_creation_status'] = fork_response.status_code
            
            if fork_response.status_code == 201:
                fork_data_response = fork_response.json()
                details['fork_id'] = fork_data_response.get('id')
            
            # Step 3: Test getting forks
            forks_response = self.api_request('GET', f'/api/recipes/{test_recipe_id}/forks')
            details['get_forks_status'] = forks_response.status_code
            
            if forks_response.status_code == 200:
                forks = forks_response.json()
                details['total_forks'] = len(forks)
            
            # Step 4: Test recipe history
            history_response = self.api_request('GET', f'/api/recipes/{test_recipe_id}/history')
            details['history_status'] = history_response.status_code
            
            # Step 5: Test commit creation
            commit_data = {
                "message": "Integration test commit",
                "changes": {
                    "ingredients": ["New test ingredient"],
                    "instructions": ["New test instruction"]
                }
            }
            
            commit_response = self.api_request('POST', f'/api/recipes/{test_recipe_id}/commit', json=commit_data)
            details['commit_creation_status'] = commit_response.status_code
            
            # Step 6: Test recipe stats
            stats_response = self.api_request('GET', f'/api/recipes/{test_recipe_id}/stats')
            details['recipe_stats_status'] = stats_response.status_code
            
            if stats_response.status_code == 200:
                stats = stats_response.json()
                details['recipe_stats'] = stats
            
            # Success criteria
            success = (
                recipes_response.status_code == 200 and
                forks_response.status_code == 200 and
                history_response.status_code == 200
            )
            
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, success, duration, details)
            
        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(test_name, False, duration, details, str(e))
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Integration Test Suite")
        print(f"🎯 Target: {self.base_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        await self.setup_browser()
        
        try:
            # Test 1: User Authentication Flow
            print("\n🔐 Testing User Authentication Flow Integration...")
            result = await self.test_user_authentication_flow()
            self.log_result(result)
            
            # Test 2: Recipe Data Consistency
            print("\n🍽️ Testing Recipe Data Consistency...")
            result = await self.test_recipe_data_consistency()
            self.log_result(result)
            
            # Test 3: Community Feed Integration
            print("\n🌐 Testing Community Feed Integration...")
            result = await self.test_community_feed_integration()
            self.log_result(result)
            
            # Test 4: User Profile Consistency
            print("\n👤 Testing User Profile Consistency...")
            result = await self.test_user_profile_consistency()
            self.log_result(result)
            
            # Test 5: Mock Data Integration
            print("\n🎭 Testing Mock Data Integration...")
            result = await self.test_mock_data_integration()
            self.log_result(result)
            
            # Test 6: Git-for-Recipes Workflow
            print("\n🍴 Testing Git-for-Recipes Workflow...")
            result = await self.test_git_for_recipes_workflow()
            self.log_result(result)
            
        finally:
            await self.cleanup_browser()
        
        # Generate summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 INTEGRATION TEST RESULTS SUMMARY")
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
                    print(f"  • {result.test_name}")
                    if result.error_message:
                        print(f"    Error: {result.error_message}")
        
        # Show key insights
        print(f"\n🔍 KEY INSIGHTS:")
        for result in self.test_results:
            if result.success and result.details:
                key_details = []
                if 'api_recipes_count' in result.details:
                    key_details.append(f"API Recipes: {result.details['api_recipes_count']}")
                if 'frontend_recipes_count' in result.details:
                    key_details.append(f"Frontend Recipes: {result.details['frontend_recipes_count']}")
                if 'shows_generic_welcome' in result.details:
                    welcome_status = "❌ Still shows 'Bienvenido'" if result.details['shows_generic_welcome'] else "✅ Shows actual username"
                    key_details.append(welcome_status)
                if 'session_persists' in result.details:
                    session_status = "✅ Session persists" if result.details['session_persists'] else "❌ Session lost"
                    key_details.append(session_status)
                
                if key_details:
                    print(f"  • {result.test_name}: {', '.join(key_details)}")
        
        print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def save_results_json(self, filename: str = "integration_test_results.json"):
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
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "details": r.details,
                    "error_message": r.error_message
                }
                for r in self.test_results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


async def main():
    tester = NuestrasRecetasIntegrationTester()
    await tester.run_all_tests()
    tester.save_results_json()


if __name__ == "__main__":
    asyncio.run(main())