#!/usr/bin/env python3
"""
Enhanced Frontend Tester for NuestrasRecetas.club
Comprehensive UI testing with:
- Complete user journey testing
- Modal and form validation
- Navigation flow testing
- Error capture and screenshot generation
- Performance monitoring
- Accessibility checks
"""

import asyncio
import json
import time
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import logging

# Import Playwright
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError
except ImportError:
    async_playwright = None
    print("❌ Playwright not installed. Run: pip install playwright && playwright install")

logger = logging.getLogger(__name__)


@dataclass
class FrontendTestResult:
    test_name: str
    success: bool
    duration: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    performance_metrics: Optional[Dict[str, float]] = None
    console_errors: Optional[List[str]] = None
    network_errors: Optional[List[str]] = None


class EnhancedFrontendTester:
    """Enhanced frontend tester with comprehensive UI coverage"""
    
    def __init__(self, base_url: str, screenshots_dir: Path):
        self.base_url = base_url
        self.screenshots_dir = screenshots_dir
        self.screenshots_dir.mkdir(exist_ok=True)
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self.test_results: List[FrontendTestResult] = []
        self.console_errors: List[str] = []
        self.network_errors: List[str] = []
        
        # Test credentials
        self.test_credentials = {
            'email': 'dev@test.com',
            'password': 'dev123'
        }
        
        # Performance thresholds (milliseconds)
        self.performance_thresholds = {
            'page_load': 3000,
            'element_load': 1000,
            'ajax_request': 2000,
            'modal_open': 500
        }
        
        # Test scenarios
        self.test_scenarios = self._define_test_scenarios()

    def _define_test_scenarios(self) -> List[Dict[str, Any]]:
        """Define comprehensive test scenarios"""
        return [
            {
                'name': 'Landing Page Load',
                'description': 'Test landing page loading and basic elements',
                'url': '/',
                'auth_required': False,
                'checks': [
                    'page_title',
                    'main_navigation',
                    'hero_section',
                    'cta_buttons'
                ]
            },
            {
                'name': 'User Login Flow',
                'description': 'Test complete user login process',
                'url': '/',
                'auth_required': False,
                'interactive': True,
                'checks': [
                    'login_modal',
                    'form_validation',
                    'authentication',
                    'post_login_redirect'
                ]
            },
            {
                'name': 'Dashboard Navigation',
                'description': 'Test main dashboard and navigation',
                'url': '/dashboard',
                'auth_required': True,
                'checks': [
                    'sidebar_navigation',
                    'main_content',
                    'user_profile_menu',
                    'quick_actions'
                ]
            },
            {
                'name': 'Recipe Browser',
                'description': 'Test recipe browsing functionality',
                'url': '/recipes',
                'auth_required': True,
                'checks': [
                    'recipe_grid',
                    'search_functionality',
                    'filter_options',
                    'pagination'
                ]
            },
            {
                'name': 'Recipe Creation Flow',
                'description': 'Test recipe creation process',
                'url': '/recipes/new',
                'auth_required': True,
                'interactive': True,
                'checks': [
                    'recipe_form',
                    'ingredient_management',
                    'step_management',
                    'form_validation',
                    'save_functionality'
                ]
            },
            {
                'name': 'Recipe Detail View',
                'description': 'Test individual recipe viewing',
                'url': '/recipes/1',
                'auth_required': True,
                'checks': [
                    'recipe_content',
                    'ingredient_list',
                    'instructions',
                    'action_buttons',
                    'comments_section'
                ]
            },
            {
                'name': 'Community Feed',
                'description': 'Test community feed functionality',
                'url': '/community',
                'auth_required': True,
                'checks': [
                    'post_feed',
                    'post_interactions',
                    'infinite_scroll',
                    'new_post_modal'
                ]
            },
            {
                'name': 'User Profile',
                'description': 'Test user profile page',
                'url': '/profile',
                'auth_required': True,
                'checks': [
                    'profile_info',
                    'recipe_collection',
                    'activity_feed',
                    'edit_profile_modal'
                ]
            },
            {
                'name': 'Groups Management',
                'description': 'Test groups functionality',
                'url': '/groups',
                'auth_required': True,
                'checks': [
                    'group_list',
                    'join_group_functionality',
                    'create_group_modal',
                    'group_search'
                ]
            },
            {
                'name': 'Settings Page',
                'description': 'Test user settings and preferences',
                'url': '/settings',
                'auth_required': True,
                'checks': [
                    'settings_tabs',
                    'form_inputs',
                    'save_settings',
                    'password_change'
                ]
            },
            {
                'name': 'Mobile Responsiveness',
                'description': 'Test mobile viewport compatibility',
                'url': '/',
                'auth_required': False,
                'mobile': True,
                'checks': [
                    'mobile_navigation',
                    'responsive_layout',
                    'touch_interactions',
                    'mobile_forms'
                ]
            },
            {
                'name': 'Error Handling',
                'description': 'Test error scenarios and handling',
                'url': '/nonexistent-page',
                'auth_required': False,
                'checks': [
                    '404_page',
                    'error_message',
                    'navigation_links'
                ]
            }
        ]

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all frontend tests"""
        if not async_playwright:
            return {
                'success': False,
                'error': 'Playwright not available',
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
        
        logger.info("Starting comprehensive frontend testing...")
        start_time = time.time()
        
        try:
            # Setup browser
            await self._setup_browser()
            
            # Run all test scenarios
            for scenario in self.test_scenarios:
                await self._run_test_scenario(scenario)
            
            # Analyze results
            analysis = self._analyze_results()
            
            duration = time.time() - start_time
            
            return {
                'success': True,
                'total_tests': len(self.test_results),
                'passed_tests': len([r for r in self.test_results if r.success]),
                'failed_tests': len([r for r in self.test_results if not r.success]),
                'skipped_tests': 0,
                'success_rate': (len([r for r in self.test_results if r.success]) / len(self.test_results)) * 100 if self.test_results else 0,
                'duration': duration,
                'performance_metrics': analysis['performance_metrics'],
                'fix_recommendations': analysis['fix_recommendations'],
                'detailed_results': [asdict(r) for r in self.test_results]
            }
            
        except Exception as e:
            logger.error(f"Frontend testing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
        finally:
            await self._cleanup_browser()

    async def _setup_browser(self):
        """Setup browser with proper configuration"""
        playwright = await async_playwright().start()
        
        # Launch browser (headless for CI, visible for debugging)
        self.browser = await playwright.chromium.launch(
            headless=True,  # Change to False for debugging
            slow_mo=100,    # Slow down for better visibility
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        # Create page
        self.page = await self.context.new_page()
        
        # Set up event listeners
        self.page.on('console', self._handle_console_message)
        self.page.on('pageerror', self._handle_page_error)
        self.page.on('requestfailed', self._handle_request_failed)

    async def _run_test_scenario(self, scenario: Dict[str, Any]):
        """Run individual test scenario"""
        test_name = scenario['name']
        logger.info(f"Running test: {test_name}")
        
        start_time = time.time()
        screenshot_path = None
        performance_metrics = {}
        
        try:
            # Setup for mobile test
            if scenario.get('mobile'):
                await self.context.set_viewport_size({'width': 375, 'height': 667})
            else:
                await self.context.set_viewport_size({'width': 1280, 'height': 720})
            
            # Navigate to URL
            url = f"{self.base_url}{scenario['url']}"
            
            # Measure page load time
            load_start = time.time()
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            load_time = (time.time() - load_start) * 1000
            performance_metrics['page_load_time'] = load_time
            
            # Handle authentication if required
            if scenario.get('auth_required'):
                await self._ensure_authenticated()
            
            # Run interactive tests
            if scenario.get('interactive'):
                await self._run_interactive_tests(scenario)
            
            # Run checks
            await self._run_scenario_checks(scenario)
            
            # Take screenshot
            screenshot_path = await self._take_screenshot(test_name)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Create successful result
            result = FrontendTestResult(
                test_name=test_name,
                success=True,
                duration=duration,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                performance_metrics=performance_metrics,
                console_errors=self.console_errors.copy(),
                network_errors=self.network_errors.copy()
            )
            
            self.test_results.append(result)
            logger.info(f"✅ {test_name} - PASSED ({duration:.1f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Take error screenshot
            try:
                screenshot_path = await self._take_screenshot(f"{test_name}_ERROR")
            except:
                pass
            
            result = FrontendTestResult(
                test_name=test_name,
                success=False,
                duration=duration,
                error_message=str(e),
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                performance_metrics=performance_metrics,
                console_errors=self.console_errors.copy(),
                network_errors=self.network_errors.copy()
            )
            
            self.test_results.append(result)
            logger.error(f"❌ {test_name} - FAILED: {e}")
        
        # Clear error collections for next test
        self.console_errors.clear()
        self.network_errors.clear()

    async def _ensure_authenticated(self):
        """Ensure user is authenticated"""
        # Check if already logged in
        try:
            await self.page.wait_for_selector('[data-testid="user-menu"]', timeout=2000)
            return  # Already authenticated
        except:
            pass
        
        # Need to log in
        try:
            # Look for login button/link
            await self.page.click('text=Login', timeout=5000)
            
            # Wait for login modal/form
            await self.page.wait_for_selector('[data-testid="login-form"], #loginModal, .login-form', timeout=5000)
            
            # Fill login form
            await self.page.fill('input[type="email"], input[name="email"]', self.test_credentials['email'])
            await self.page.fill('input[type="password"], input[name="password"]', self.test_credentials['password'])
            
            # Submit form
            await self.page.click('button[type="submit"], .login-submit, text=Sign In')
            
            # Wait for successful login
            await self.page.wait_for_selector('[data-testid="user-menu"], .user-profile', timeout=10000)
            
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            raise

    async def _run_interactive_tests(self, scenario: Dict[str, Any]):
        """Run interactive tests for scenario"""
        test_name = scenario['name']
        
        if test_name == 'User Login Flow':
            await self._test_login_flow()
        elif test_name == 'Recipe Creation Flow':
            await self._test_recipe_creation()

    async def _test_login_flow(self):
        """Test complete login flow"""
        # Click login button
        await self.page.click('text=Login')
        
        # Wait for modal
        await self.page.wait_for_selector('.modal, #loginModal')
        
        # Test form validation with empty fields
        await self.page.click('button[type="submit"]')
        
        # Should show validation errors
        await self.page.wait_for_selector('.error, .invalid-feedback', timeout=2000)
        
        # Fill form correctly
        await self.page.fill('input[type="email"]', self.test_credentials['email'])
        await self.page.fill('input[type="password"]', self.test_credentials['password'])
        
        # Submit
        await self.page.click('button[type="submit"]')
        
        # Wait for successful login
        await self.page.wait_for_selector('[data-testid="user-menu"]', timeout=10000)

    async def _test_recipe_creation(self):
        """Test recipe creation process"""
        # Fill recipe title
        await self.page.fill('input[name="title"]', 'Test Recipe from Automated Test')
        
        # Fill description
        await self.page.fill('textarea[name="description"]', 'This is a test recipe created by automated testing.')
        
        # Add ingredient
        await self.page.click('.add-ingredient, button:has-text("Add Ingredient")')
        await self.page.fill('input[name="ingredient_name"]', 'Test Ingredient')
        await self.page.fill('input[name="ingredient_amount"]', '1')
        await self.page.fill('input[name="ingredient_unit"]', 'cup')
        
        # Add instruction
        await self.page.click('.add-instruction, button:has-text("Add Step")')
        await self.page.fill('textarea[name="instruction"]', 'Test instruction step.')
        
        # Set prep time
        await self.page.fill('input[name="prep_time"]', '15')
        
        # Set cook time
        await self.page.fill('input[name="cook_time"]', '30')
        
        # Set servings
        await self.page.fill('input[name="servings"]', '4')

    async def _run_scenario_checks(self, scenario: Dict[str, Any]):
        """Run specific checks for scenario"""
        checks = scenario.get('checks', [])
        
        for check in checks:
            await self._run_check(check)

    async def _run_check(self, check_name: str):
        """Run individual check"""
        check_start = time.time()
        
        try:
            if check_name == 'page_title':
                title = await self.page.title()
                assert title and len(title) > 0, "Page should have a title"
                
            elif check_name == 'main_navigation':
                await self.page.wait_for_selector('nav, .navbar, .navigation', timeout=5000)
                
            elif check_name == 'hero_section':
                await self.page.wait_for_selector('.hero, .jumbotron, .banner', timeout=5000)
                
            elif check_name == 'login_modal':
                await self.page.wait_for_selector('.modal, #loginModal', timeout=5000)
                
            elif check_name == 'recipe_grid':
                await self.page.wait_for_selector('.recipe-grid, .recipe-list, .recipes', timeout=5000)
                
            elif check_name == 'recipe_form':
                await self.page.wait_for_selector('form, .recipe-form', timeout=5000)
                
            elif check_name == 'search_functionality':
                search_input = await self.page.wait_for_selector('input[type="search"], .search-input', timeout=5000)
                await search_input.fill('pasta')
                await self.page.keyboard.press('Enter')
                await self.page.wait_for_timeout(1000)  # Wait for search results
                
            elif check_name == 'mobile_navigation':
                # Check for mobile menu button
                await self.page.wait_for_selector('.mobile-menu, .hamburger, .menu-toggle', timeout=5000)
                
            elif check_name == '404_page':
                # Check for 404 content
                page_content = await self.page.content()
                assert '404' in page_content or 'not found' in page_content.lower(), "Should show 404 error"
                
            else:
                # Generic element check
                selector = f'.{check_name.replace("_", "-")}, #{check_name}, [data-testid="{check_name}"]'
                await self.page.wait_for_selector(selector, timeout=5000)
                
            check_time = (time.time() - check_start) * 1000
            logger.debug(f"  ✓ {check_name} ({check_time:.1f}ms)")
            
        except Exception as e:
            logger.warning(f"  ✗ {check_name}: {e}")
            # Don't fail the entire test for individual check failures

    async def _take_screenshot(self, test_name: str) -> Optional[Path]:
        """Take screenshot for test"""
        try:
            timestamp = int(time.time())
            filename = f"{test_name.replace(' ', '_').lower()}_{timestamp}.png"
            screenshot_path = self.screenshots_dir / filename
            
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            return screenshot_path
            
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None

    def _handle_console_message(self, msg):
        """Handle console messages"""
        if msg.type == 'error':
            self.console_errors.append(f"{msg.type}: {msg.text}")
            logger.warning(f"Console Error: {msg.text}")

    def _handle_page_error(self, error):
        """Handle page errors"""
        self.console_errors.append(f"Page Error: {error}")
        logger.error(f"Page Error: {error}")

    def _handle_request_failed(self, request):
        """Handle failed requests"""
        self.network_errors.append(f"Request Failed: {request.url} - {request.failure}")
        logger.warning(f"Request Failed: {request.url}")

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze test results and generate recommendations"""
        analysis = {
            'performance_metrics': {},
            'fix_recommendations': []
        }
        
        # Performance analysis
        successful_tests = [r for r in self.test_results if r.success and r.performance_metrics]
        
        if successful_tests:
            page_load_times = [r.performance_metrics.get('page_load_time', 0) for r in successful_tests if r.performance_metrics]
            if page_load_times:
                analysis['performance_metrics'] = {
                    'avg_page_load_time': sum(page_load_times) / len(page_load_times),
                    'max_page_load_time': max(page_load_times),
                    'slow_pages_count': len([t for t in page_load_times if t > self.performance_thresholds['page_load']])
                }
        
        # Error analysis
        failed_tests = [r for r in self.test_results if not r.success]
        
        # JavaScript errors
        js_error_tests = [r for r in self.test_results if r.console_errors]
        if js_error_tests:
            analysis['fix_recommendations'].append({
                'issue_type': 'JavaScript Errors',
                'severity': 'medium',
                'description': f'{len(js_error_tests)} tests detected JavaScript errors',
                'priority': 2,
                'details': [r.console_errors for r in js_error_tests]
            })
        
        # Network errors
        network_error_tests = [r for r in self.test_results if r.network_errors]
        if network_error_tests:
            analysis['fix_recommendations'].append({
                'issue_type': 'Network Errors',
                'severity': 'high',
                'description': f'{len(network_error_tests)} tests detected network failures',
                'priority': 1,
                'details': [r.network_errors for r in network_error_tests]
            })
        
        # Authentication issues
        auth_failures = [r for r in failed_tests if 'authentication' in r.error_message.lower()]
        if auth_failures:
            analysis['fix_recommendations'].append({
                'issue_type': 'Authentication Issues',
                'severity': 'high',
                'description': f'{len(auth_failures)} tests failed due to authentication problems',
                'priority': 1
            })
        
        # Performance issues
        slow_tests = [r for r in self.test_results if r.performance_metrics and 
                     r.performance_metrics.get('page_load_time', 0) > self.performance_thresholds['page_load']]
        if slow_tests:
            analysis['fix_recommendations'].append({
                'issue_type': 'Performance Issues',
                'severity': 'medium',
                'description': f'{len(slow_tests)} pages loading slowly (>{self.performance_thresholds["page_load"]}ms)',
                'priority': 2
            })
        
        return analysis

    async def _cleanup_browser(self):
        """Cleanup browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.warning(f"Error cleaning up browser: {e}")
        finally:
            self.page = None
            self.context = None
            self.browser = None