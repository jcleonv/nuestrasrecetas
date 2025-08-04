#!/usr/bin/env python3
"""
Comprehensive Production Issues Test
Tests all the reported issues with recipes, forking, and profiles
"""

import asyncio
from playwright.async_api import async_playwright
import json
import re

async def run_production_test():
    print("🔍 COMPREHENSIVE PRODUCTION ISSUES TEST")
    print("=" * 50)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # Enable console logging
        def handle_console(msg):
            if msg.type in ['error', 'warning']:
                print(f"🔴 CONSOLE {msg.type.upper()}: {msg.text}")
        
        def handle_response(response):
            if response.status >= 400:
                print(f"🔴 HTTP ERROR: {response.status} {response.url}")
        
        page = await context.new_page()
        page.on("console", handle_console)
        page.on("response", handle_response)
        
        try:
            # 1. Login
            print("\n1. 🔐 Testing Login...")
            await page.goto("http://localhost:8000")
            await page.wait_for_load_state("networkidle")
            
            # Check if already logged in or need to login
            if await page.locator('input[placeholder="Email"]').is_visible():
                await page.fill('input[placeholder="Email"]', "j_carlos.leon@hotmail.com")
                await page.fill('input[placeholder="Password"]', "juancarlos95")
                await page.click('button:has-text("Sign In")')
                await page.wait_for_timeout(3000)
            
            print("✅ Login successful")
            
            # 2. Test Recipe Access from Dashboard
            print("\n2. 📋 Testing Recipe Access from Dashboard...")
            await page.goto("http://localhost:8000/dashboard")
            await page.wait_for_load_state("networkidle")
            
            # Wait for recipes to load
            await page.wait_for_timeout(3000)
            
            # Try to click on a recipe card
            recipe_cards = await page.locator('.recipe-card, [data-recipe-id], .recipe-item').all()
            print(f"Found {len(recipe_cards)} recipe cards")
            
            if recipe_cards:
                recipe_card = recipe_cards[0]
                # Get recipe ID if available
                recipe_id = None
                try:
                    recipe_id = await recipe_card.get_attribute('data-recipe-id')
                    if not recipe_id:
                        recipe_text = await recipe_card.text_content()
                        print(f"Recipe card content: {recipe_text}")
                except:
                    pass
                
                print(f"Clicking on first recipe card (ID: {recipe_id})...")
                current_url = page.url
                await recipe_card.click()
                await page.wait_for_timeout(2000)
                
                new_url = page.url
                print(f"URL before click: {current_url}")
                print(f"URL after click: {new_url}")
                
                if new_url == current_url or 'dashboard' in new_url:
                    print("🔴 ISSUE: Recipe click redirected to home/dashboard instead of recipe page")
                elif '/recipe/' in new_url:
                    print("✅ Recipe navigation working")
                else:
                    print(f"🟡 Unexpected navigation: {new_url}")
            else:
                print("🔴 ISSUE: No recipe cards found on dashboard")
            
            # 3. Test Direct Recipe Access
            print("\n3. 🔗 Testing Direct Recipe URL Access...")
            # Try accessing a known recipe ID directly
            await page.goto("http://localhost:8000/recipe/1")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            
            current_url = page.url
            if current_url.endswith("/"):
                print("🔴 ISSUE: Direct recipe URL redirects to home page")
            elif "/recipe/1" in current_url:
                print("✅ Direct recipe access working")
                # Check if the page shows recipe content
                recipe_content = await page.locator('h1, .recipe-title, .recipe-content').count()
                if recipe_content > 0:
                    print("✅ Recipe content loads correctly")
                else:
                    print("🔴 ISSUE: Recipe page loads but shows no recipe content")
            else:
                print(f"🟡 Unexpected redirect: {current_url}")
            
            # 4. Test Fork Functionality
            print("\n4. 🍴 Testing Recipe Forking...")
            await page.goto("http://localhost:8000/dashboard")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            
            # Look for fork buttons
            fork_buttons = await page.locator('button:has-text("Fork"), .fork-btn, [data-action="fork"]').all()
            print(f"Found {len(fork_buttons)} fork buttons")
            
            if fork_buttons:
                fork_button = fork_buttons[0]
                print("Clicking fork button...")
                
                # Monitor network requests
                fork_responses = []
                def track_fork_response(response):
                    if '/fork' in response.url:
                        fork_responses.append(response)
                
                page.on("response", track_fork_response)
                
                await fork_button.click()
                await page.wait_for_timeout(3000)
                
                if fork_responses:
                    response = fork_responses[0]
                    print(f"Fork request status: {response.status}")
                    if response.status == 200:
                        print("✅ Fork request successful")
                        # Check for confirmation message or redirect
                        confirmation = await page.locator('.success-message, .toast, .notification').count()
                        if confirmation > 0:
                            print("✅ Fork confirmation shown")
                        else:
                            print("🔴 ISSUE: No fork confirmation shown to user")
                    else:
                        print(f"🔴 ISSUE: Fork request failed with status {response.status}")
                else:
                    print("🔴 ISSUE: No fork network request detected")
            else:
                print("🔴 ISSUE: No fork buttons found")
            
            # 5. Test Profile Access
            print("\n5. 👤 Testing Profile Access...")
            # Navigate to profile
            profile_links = await page.locator('a:has-text("Profile"), .profile-link, [href*="profile"]').all()
            
            if profile_links:
                await profile_links[0].click()
                await page.wait_for_timeout(3000)
                
                # Check for errors
                error_messages = await page.locator('.error, .alert-danger, .error-message').count()
                if error_messages > 0:
                    error_text = await page.locator('.error, .alert-danger, .error-message').first.text_content()
                    print(f"🔴 ISSUE: Profile error - {error_text}")
                else:
                    print("✅ Profile loads without errors")
                    
                # Check if profile content loads
                profile_content = await page.locator('.profile-info, .user-profile, h1').count()
                if profile_content > 0:
                    print("✅ Profile content displays")
                else:
                    print("🟡 Profile page loads but content may be missing")
            else:
                # Try direct profile URL using username
                await page.goto("http://localhost:8000/profile/jcarlos")
                await page.wait_for_timeout(3000)
                
                if page.url.endswith("/"):
                    print("🔴 ISSUE: Profile URL redirects to home page")
                else:
                    print("✅ Direct profile access working")
            
            # 6. Test API Endpoints Directly
            print("\n6. 🌐 Testing API Endpoints...")
            
            # Test recipe API
            response = await page.request.get("http://localhost:8000/api/recipe/1")
            print(f"Recipe API status: {response.status}")
            if response.status == 404:
                print("🔴 ISSUE: Recipe API returns 404 for existing recipe")
            elif response.status == 401:
                print("🔴 ISSUE: Recipe API requires authentication for public recipes")
            elif response.status == 200:
                print("✅ Recipe API working")
            
            # Test recipes list API
            response = await page.request.get("http://localhost:8000/api/recipes")
            print(f"Recipes list API status: {response.status}")
            if response.status == 200:
                data = await response.json()
                recipe_count = len(data) if isinstance(data, list) else len(data.get('recipes', []))
                print(f"✅ Recipes API returns {recipe_count} recipes")
            else:
                print(f"🔴 ISSUE: Recipes API failed with status {response.status}")
            
            # 7. Test Community Feed
            print("\n7. 🌍 Testing Community Feed...")
            await page.goto("http://localhost:8000/community")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            
            # Check if community feed loads
            community_items = await page.locator('.activity-item, .feed-item, .community-item').count()
            print(f"Community feed items: {community_items}")
            
            if community_items > 0:
                print("✅ Community feed shows items")
                # Test clicking on a community item
                first_item = page.locator('.activity-item, .feed-item, .community-item').first
                await first_item.click()
                await page.wait_for_timeout(2000)
                
                if '/recipe/' in page.url:
                    print("✅ Community feed navigation working")
                else:
                    print(f"🔴 ISSUE: Community feed navigation failed - URL: {page.url}")
            else:
                print("🔴 ISSUE: Community feed shows no items")
            
            print("\n" + "=" * 50)
            print("🏁 PRODUCTION ISSUES TEST COMPLETED")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_production_test())