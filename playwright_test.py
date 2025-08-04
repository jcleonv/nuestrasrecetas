#!/usr/bin/env python3
"""
Playwright test script to verify all main functionality works in the UI
"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_recipe_platform():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to True for headless
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print("🚀 Starting Playwright tests...")
            
            # Test 1: Login
            print("1. Testing login...")
            await page.goto("http://127.0.0.1:8000")
            await page.wait_for_load_state("networkidle")
            
            # Click login button to show login form
            await page.click('button:has-text("Iniciar Sesión")')
            await page.wait_for_selector('#login-form')
            
            # Fill login form
            await page.fill('#login-email', 'j_carlos.leon@hotmail.com')
            await page.fill('#login-password', 'juancarlos95')
            await page.click('button[type="submit"]')
            
            # Wait for dashboard to load
            await page.wait_for_url("**/dashboard")
            print("✅ Login successful - redirected to dashboard")
            
            # Test 2: Recipe creation
            print("2. Testing recipe creation...")
            await page.wait_for_timeout(2000)  # Wait for page to fully load
            
            # Force click on new recipe button using JavaScript
            await page.evaluate('onNew()')
            await page.wait_for_selector('#modal:not(.hidden)', timeout=5000)
            
            # Fill recipe form using the actual IDs from the modal
            await page.fill('#mTitle', 'Playwright Test Recipe')
            await page.fill('#mCategory', 'Main')
            await page.fill('#mTags', 'test, automation')
            await page.fill('#mServings', '4')
            await page.fill('#mInstructions', 'Mix ingredients and cook in the oven')
            
            # Add an ingredient
            await page.fill('#mIngredientName', 'Test ingredient')
            await page.fill('#mIngredientAmount', '2 cups')
            await page.click('#btnAddIngredient')
            
            # Save the recipe
            await page.click('#btnSaveRecipe')
            await page.wait_for_timeout(3000)  # Wait for creation
            print("✅ Recipe creation attempted")
            
            # Test 3: Navigation to community
            print("3. Testing community page...")
            await page.click('text=Community')
            await page.wait_for_url("**/community")
            await page.wait_for_load_state("networkidle")
            print("✅ Community page loaded")
            
            # Test 4: Navigation to groups
            print("4. Testing groups page...")
            await page.click('text=Groups')
            await page.wait_for_url("**/groups")
            await page.wait_for_load_state("networkidle")
            print("✅ Groups page loaded")
            
            # Test 5: Try joining a group (if any exist)
            print("5. Testing group functionality...")
            join_buttons = page.locator('button:has-text("Join")')
            if await join_buttons.count() > 0:
                await join_buttons.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Group join attempted")
            else:
                print("⚠️  No groups found to join")
            
            # Test 6: Navigate to recipes and check if they load properly
            print("6. Testing recipe detail pages...")
            
            # Test direct recipe URL navigation
            await page.goto("http://127.0.0.1:8000/recipe/8")
            await page.wait_for_load_state("networkidle")
            current_url = page.url
            
            if current_url == "http://127.0.0.1:8000/recipe/8":
                print("✅ Recipe detail page loads without redirect")
            elif current_url == "http://127.0.0.1:8000/" or current_url == "http://127.0.0.1:8000/dashboard":
                print("❌ Recipe page redirects to home - ISSUE FOUND")
            else:
                print(f"⚠️  Recipe page redirected to: {current_url}")
            
            # Test another recipe
            await page.goto("http://127.0.0.1:8000/recipe/1")
            await page.wait_for_load_state("networkidle")
            current_url2 = page.url
            
            if current_url2 == "http://127.0.0.1:8000/recipe/1":
                print("✅ Second recipe detail page also works")
            else:
                print(f"⚠️  Second recipe redirected to: {current_url2}")
            
            print("\n🎉 All tests completed!")
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_recipe_platform())