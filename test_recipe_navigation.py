#!/usr/bin/env python3
"""
Simple test to verify recipe navigation doesn't redirect to home page
"""

import asyncio
from playwright.async_api import async_playwright

async def test_recipe_navigation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print("🚀 Testing recipe navigation...")
            
            # Login first
            await page.goto("http://127.0.0.1:8000")
            await page.click('button:has-text("Iniciar Sesión")')
            await page.wait_for_selector('#login-form')
            await page.fill('#login-email', 'j_carlos.leon@hotmail.com')
            await page.fill('#login-password', 'juancarlos95')
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/dashboard")
            print("✅ Login successful")
            
            # Test recipe navigation
            print("Testing recipe detail pages...")
            
            # Test recipe 8
            await page.goto("http://127.0.0.1:8000/recipe/8")
            await page.wait_for_load_state("networkidle")
            current_url = page.url
            
            if current_url == "http://127.0.0.1:8000/recipe/8":
                print("✅ Recipe 8 loads correctly - no redirect")
            else:
                print(f"❌ Recipe 8 redirected to: {current_url}")
            
            # Test recipe 1
            await page.goto("http://127.0.0.1:8000/recipe/1")
            await page.wait_for_load_state("networkidle")
            current_url = page.url
            
            if current_url == "http://127.0.0.1:8000/recipe/1":
                print("✅ Recipe 1 loads correctly - no redirect")
            else:
                print(f"❌ Recipe 1 redirected to: {current_url}")
                
            # Test recipe 2
            await page.goto("http://127.0.0.1:8000/recipe/2")
            await page.wait_for_load_state("networkidle")
            current_url = page.url
            
            if current_url == "http://127.0.0.1:8000/recipe/2":
                print("✅ Recipe 2 loads correctly - no redirect")
            else:
                print(f"❌ Recipe 2 redirected to: {current_url}")
            
            print("\n🎉 Recipe navigation test completed!")
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_recipe_navigation())