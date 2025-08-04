#!/usr/bin/env python3
"""
Frontend Functionality Test Suite for NuestrasRecetas.club
Tests user login flow, UI interactions, modals, forms, and navigation.
Uses Playwright for browser automation.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class FrontendTestResult:
    test_name: str
    success: bool
    duration: float
    error_message: str = None
    screenshot_path: str = None


class NuestrasRecetasFrontendTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.test_results: List[FrontendTestResult] = []
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.test_credentials = {
            "email": "dev@test.com",
            "password": "dev123"
        }
    
    async def setup_browser(self):
        """Initialize browser and page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False, slow_mo=500)  # Visible for debugging
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        self.page = await self.context.new_page()
        
        # Enable console logging
        self.page.on("console", lambda msg: print(f"🖥️  Console: {msg.text}"))
        self.page.on("pageerror", lambda error: print(f"🚨 Page Error: {error}"))
    
    async def cleanup_browser(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
    
    def log_result(self, result: FrontendTestResult):
        """Log test result"""
        self.test_results.append(result)
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"{status} {result.test_name} ({result.duration:.2f}s)")
        if result.error_message:
            print(f"    Error: {result.error_message}")
    
    async def take_screenshot(self, name: str) -> str:
        """Take screenshot and return path"""
        screenshot_path = f"screenshots/frontend_test_{name}_{int(time.time())}.png"
        await self.page.screenshot(path=screenshot_path, full_page=True)
        return screenshot_path
    
    async def wait_for_no_loading_spinner(self, timeout: int = 5000):
        """Wait for loading spinners to disappear"""
        try:
            await self.page.wait_for_selector('.loading, .spinner, [data-loading="true"]', 
                                            state='detached', timeout=timeout)
        except:
            pass  # No loading spinner present
    
    async def test_page_load(self, path: str, expected_title: str = None) -> FrontendTestResult:
        """Test if a page loads successfully"""
        start_time = time.time()
        test_name = f"Page Load: {path}"
        
        try:
            response = await self.page.goto(f"{self.base_url}{path}")
            
            if response.status >= 400:
                raise Exception(f"HTTP {response.status}")
            
            # Wait for page to be ready
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await self.wait_for_no_loading_spinner()
            
            # Check title if provided
            if expected_title:
                title = await self.page.title()
                if expected_title not in title:
                    raise Exception(f"Expected title to contain '{expected_title}', got '{title}'")
            
            # Check for JavaScript errors in console
            js_errors = []
            self.page.on("pageerror", lambda error: js_errors.append(str(error)))
            
            await asyncio.sleep(1)  # Wait for any async JS to execute
            
            if js_errors:
                raise Exception(f"JavaScript errors: {'; '.join(js_errors)}")
            
            duration = time.time() - start_time
            return FrontendTestResult(test_name, True, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self.take_screenshot(f"page_load_error_{path.replace('/', '_')}")
            return FrontendTestResult(test_name, False, duration, str(e), screenshot_path)
    
    async def test_user_login_flow(self) -> FrontendTestResult:
        """Test complete user login flow"""
        start_time = time.time()
        test_name = "User Login Flow"
        
        try:
            # Go to homepage
            await self.page.goto(self.base_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Look for login button/form
            login_selector = 'button:has-text("Login"), input[type="email"], #loginModal, .login-form'
            await self.page.wait_for_selector(login_selector, timeout=10000)
            
            # Check if there's a login modal trigger
            login_button = self.page.locator('button:has-text("Login"), button:has-text("Iniciar Sesión")')
            if await login_button.count() > 0:
                await login_button.first.click()
                await asyncio.sleep(1)
            
            # Fill login form
            email_input = self.page.locator('input[type="email"], input[name="email"], #email')
            password_input = self.page.locator('input[type="password"], input[name="password"], #password')
            
            await email_input.fill(self.test_credentials["email"])
            await password_input.fill(self.test_credentials["password"])
            
            # Submit form
            submit_button = self.page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Entrar")')
            await submit_button.click()
            
            # Wait for login to complete
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await self.wait_for_no_loading_spinner()
            await asyncio.sleep(2)
            
            # Check if login was successful - look for user-specific content
            success_indicators = [
                '.user-profile', '.dashboard', 'button:has-text("Logout")', 
                'button:has-text("Cerrar Sesión")', '.user-menu', '[data-user-authenticated="true"]'
            ]
            
            login_successful = False
            for indicator in success_indicators:
                if await self.page.locator(indicator).count() > 0:
                    login_successful = True
                    break
            
            # Also check if we're no longer on login page
            current_url = self.page.url
            if '/dashboard' in current_url or '/profile' in current_url:
                login_successful = True
            
            # Check that user name is NOT "Bienvenido" (should show real user name)
            welcome_text = await self.page.locator('text="Bienvenido"').count()
            if welcome_text > 0:
                print("⚠️  Warning: User still shows 'Bienvenido' instead of actual name")
            
            if not login_successful:
                raise Exception("Login appears to have failed - no success indicators found")
            
            duration = time.time() - start_time
            return FrontendTestResult(test_name, True, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self.take_screenshot("login_error")
            return FrontendTestResult(test_name, False, duration, str(e), screenshot_path)
    
    async def test_modal_functionality(self) -> FrontendTestResult:
        """Test modal open/close functionality"""
        start_time = time.time()
        test_name = "Modal Functionality"
        
        try:
            # Look for modal triggers
            modal_triggers = [
                'button:has-text("Create"), button:has-text("Add"), button:has-text("New")',
                'button:has-text("Crear"), button:has-text("Añadir"), button:has-text("Nuevo")',
                '.modal-trigger, [data-modal-target]'
            ]
            
            modal_opened = False
            for trigger_selector in modal_triggers:
                triggers = self.page.locator(trigger_selector)
                if await triggers.count() > 0:
                    # Click the first trigger
                    await triggers.first.click()
                    await asyncio.sleep(1)
                    
                    # Check if modal opened
                    modal_selectors = ['.modal.show', '.modal.active', '.modal[style*="display: block"]']
                    for modal_selector in modal_selectors:
                        if await self.page.locator(modal_selector).count() > 0:
                            modal_opened = True
                            
                            # Test close modal
                            close_selectors = [
                                '.modal .close', '.modal .btn-close', 'button:has-text("Close")',
                                'button:has-text("Cerrar")', '.modal-header .close'
                            ]
                            
                            for close_selector in close_selectors:
                                if await self.page.locator(close_selector).count() > 0:
                                    await self.page.locator(close_selector).first.click()
                                    await asyncio.sleep(1)
                                    break
                            
                            # Also test clicking outside modal
                            await self.page.locator('.modal-backdrop, .overlay').click()
                            await asyncio.sleep(1)
                            
                            break
                    
                    if modal_opened:
                        break
            
            if not modal_opened:
                raise Exception("No modals could be opened for testing")
            
            duration = time.time() - start_time
            return FrontendTestResult(test_name, True, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self.take_screenshot("modal_error")
            return FrontendTestResult(test_name, False, duration, str(e), screenshot_path)
    
    async def test_navigation(self) -> FrontendTestResult:
        """Test navigation between pages"""
        start_time = time.time()
        test_name = "Page Navigation"
        
        try:
            pages_to_test = [
                ("/", "Home"),
                ("/dashboard", "Dashboard"),
                ("/community", "Community"),
                ("/groups", "Groups")
            ]
            
            for path, page_name in pages_to_test:
                await self.page.goto(f"{self.base_url}{path}")
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                await self.wait_for_no_loading_spinner()
                
                # Check if page loaded successfully
                if self.page.url != f"{self.base_url}{path}":
                    # Allow for redirects
                    if not any(expected in self.page.url for expected in [path, "/login", "/dashboard"]):
                        raise Exception(f"Navigation to {path} failed, ended up at {self.page.url}")
                
                await asyncio.sleep(1)  # Brief pause between navigations
            
            duration = time.time() - start_time
            return FrontendTestResult(test_name, True, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self.take_screenshot("navigation_error")
            return FrontendTestResult(test_name, False, duration, str(e), screenshot_path)
    
    async def test_form_functionality(self) -> FrontendTestResult:
        """Test form submissions"""
        start_time = time.time()
        test_name = "Form Functionality"
        
        try:
            # Test different types of forms
            forms_tested = 0
            
            # Look for recipe creation form
            if await self.page.locator('button:has-text("Create Recipe"), button:has-text("New Recipe")').count() > 0:
                await self.page.locator('button:has-text("Create Recipe"), button:has-text("New Recipe")').first.click()
                await asyncio.sleep(1)
                
                # Fill out form if available
                if await self.page.locator('input[name="name"], input[placeholder*="recipe name"]').count() > 0:
                    await self.page.locator('input[name="name"], input[placeholder*="recipe name"]').first.fill("Test Recipe")
                    forms_tested += 1
                
                # Close modal/form
                if await self.page.locator('.close, button:has-text("Cancel")').count() > 0:
                    await self.page.locator('.close, button:has-text("Cancel")').first.click()
                    await asyncio.sleep(1)
            
            # Look for search forms
            search_inputs = self.page.locator('input[type="search"], input[placeholder*="search"], input[name="search"]')
            if await search_inputs.count() > 0:
                await search_inputs.first.fill("test search")
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(2)
                forms_tested += 1
            
            # Look for comment/post forms
            if await self.page.locator('textarea[placeholder*="comment"], textarea[placeholder*="post"]').count() > 0:
                await self.page.locator('textarea[placeholder*="comment"], textarea[placeholder*="post"]').first.fill("Test comment")
                forms_tested += 1
            
            if forms_tested == 0:
                print("⚠️  Warning: No forms found to test")
            
            duration = time.time() - start_time
            return FrontendTestResult(test_name, True, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self.take_screenshot("form_error")
            return FrontendTestResult(test_name, False, duration, str(e), screenshot_path)
    
    async def test_button_functionality(self) -> FrontendTestResult:
        """Test that buttons trigger correct functions"""
        start_time = time.time()
        test_name = "Button Functionality"
        
        try:
            # Test various buttons
            button_selectors = [
                'button:not([disabled])',
                '.btn:not([disabled])',
                'a.button:not([disabled])'
            ]
            
            buttons_tested = 0
            for selector in button_selectors:
                buttons = self.page.locator(selector)
                button_count = await buttons.count()
                
                # Test first few buttons (to avoid overwhelming)
                for i in range(min(5, button_count)):
                    try:
                        button = buttons.nth(i)
                        button_text = await button.text_content()
                        
                        # Skip certain buttons that might cause navigation away
                        skip_buttons = ['logout', 'delete', 'remove', 'cerrar sesión', 'eliminar']
                        if any(skip in button_text.lower() for skip in skip_buttons):
                            continue
                        
                        # Click button and check for response
                        await button.click()
                        await asyncio.sleep(0.5)  # Brief pause to see response
                        buttons_tested += 1
                        
                        # Check if button triggered a modal, loading state, or other response
                        # This is a basic check - more specific tests would be needed for each button
                        
                    except Exception as e:
                        print(f"⚠️  Button test failed for button {i}: {str(e)}")
                        continue
            
            if buttons_tested == 0:
                print("⚠️  Warning: No buttons could be tested")
            
            duration = time.time() - start_time
            return FrontendTestResult(test_name, True, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self.take_screenshot("button_error")
            return FrontendTestResult(test_name, False, duration, str(e), screenshot_path)
    
    async def test_mobile_responsiveness(self) -> FrontendTestResult:
        """Test mobile viewport"""
        start_time = time.time()
        test_name = "Mobile Responsiveness"
        
        try:
            # Set mobile viewport
            await self.page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE size
            
            # Test homepage in mobile
            await self.page.goto(self.base_url)
            await self.page.wait_for_load_state('networkidle')
            await self.wait_for_no_loading_spinner()
            
            # Check if mobile navigation works
            mobile_menu_trigger = self.page.locator('.navbar-toggler, .mobile-menu-trigger, .hamburger')
            if await mobile_menu_trigger.count() > 0:
                await mobile_menu_trigger.first.click()
                await asyncio.sleep(1)
                
                # Check if mobile menu opened
                mobile_menu = self.page.locator('.navbar-collapse.show, .mobile-menu.active')
                if await mobile_menu.count() == 0:
                    raise Exception("Mobile menu did not open")
            
            # Reset to desktop viewport
            await self.page.set_viewport_size({"width": 1280, "height": 720})
            
            duration = time.time() - start_time
            return FrontendTestResult(test_name, True, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self.take_screenshot("mobile_error")
            return FrontendTestResult(test_name, False, duration, str(e), screenshot_path)
    
    async def test_javascript_console_errors(self) -> FrontendTestResult:
        """Test for JavaScript console errors across pages"""
        start_time = time.time()
        test_name = "JavaScript Console Errors"
        
        try:
            js_errors = []
            console_messages = []
            
            # Capture console messages and errors
            self.page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
            self.page.on("pageerror", lambda error: js_errors.append(str(error)))
            
            # Visit multiple pages and check for errors
            pages = ["/", "/dashboard", "/community", "/groups"]
            
            for page_path in pages:
                await self.page.goto(f"{self.base_url}{page_path}")
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                await asyncio.sleep(2)  # Wait for any async JS to execute
            
            # Filter out non-critical console messages
            critical_errors = [
                error for error in js_errors 
                if not any(ignore in error.lower() for ignore in [
                    'favicon', 'non-passive event listener', 'third-party'
                ])
            ]
            
            if critical_errors:
                raise Exception(f"JavaScript errors found: {'; '.join(critical_errors[:3])}")
            
            # Check for critical console errors
            critical_console_errors = [
                msg for msg in console_messages 
                if msg.startswith('error:') and not any(ignore in msg.lower() for ignore in [
                    'favicon', '404', 'third-party'
                ])
            ]
            
            if critical_console_errors:
                print(f"⚠️  Console warnings: {len(critical_console_errors)} messages")
            
            duration = time.time() - start_time
            return FrontendTestResult(test_name, True, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            screenshot_path = await self.take_screenshot("js_error")
            return FrontendTestResult(test_name, False, duration, str(e), screenshot_path)
    
    async def run_all_tests(self):
        """Run all frontend tests"""
        print("🚀 Starting Frontend Functionality Test Suite")
        print(f"🎯 Target: {self.base_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        await self.setup_browser()
        
        try:
            # Test basic page loads first
            pages_to_test = [
                ("/", "NuestrasRecetas"),
                ("/dashboard", None),
                ("/community", None),
                ("/groups", None)
            ]
            
            print("\n📄 Testing Page Loads...")
            for path, expected_title in pages_to_test:
                result = await self.test_page_load(path, expected_title)
                self.log_result(result)
            
            # Test user login flow
            print("\n🔐 Testing User Login Flow...")
            result = await self.test_user_login_flow()
            self.log_result(result)
            
            # Test navigation
            print("\n🧭 Testing Navigation...")
            result = await self.test_navigation()
            self.log_result(result)
            
            # Test modals
            print("\n🪟 Testing Modal Functionality...")
            result = await self.test_modal_functionality()
            self.log_result(result)
            
            # Test forms
            print("\n📝 Testing Form Functionality...")
            result = await self.test_form_functionality()
            self.log_result(result)
            
            # Test buttons
            print("\n🔘 Testing Button Functionality...")
            result = await self.test_button_functionality()
            self.log_result(result)
            
            # Test mobile responsiveness
            print("\n📱 Testing Mobile Responsiveness...")
            result = await self.test_mobile_responsiveness()
            self.log_result(result)
            
            # Test JavaScript errors
            print("\n🐛 Testing JavaScript Console Errors...")
            result = await self.test_javascript_console_errors()
            self.log_result(result)
            
        finally:
            await self.cleanup_browser()
        
        # Generate summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 FRONTEND TEST RESULTS SUMMARY")
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
                    print(f"  • {result.test_name} - {result.error_message}")
                    if result.screenshot_path:
                        print(f"    📸 Screenshot: {result.screenshot_path}")
        
        # Performance stats
        durations = [r.duration for r in self.test_results]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            print(f"\n⚡ PERFORMANCE:")
            print(f"  • Average Test Duration: {avg_duration:.2f}s")
            print(f"  • Slowest Test: {max_duration:.2f}s")
        
        print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def save_results_json(self, filename: str = "frontend_test_results.json"):
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
                    "error_message": r.error_message,
                    "screenshot_path": r.screenshot_path
                }
                for r in self.test_results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


async def main():
    tester = NuestrasRecetasFrontendTester()
    await tester.run_all_tests()
    tester.save_results_json()


if __name__ == "__main__":
    asyncio.run(main())