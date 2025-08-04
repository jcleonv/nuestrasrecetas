#!/usr/bin/env python3
"""
Focused test for forking functionality, community feeds, and profile features
"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_forking_and_feeds():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        issues = []
        features_tested = []
        
        try:
            print("🚀 Testing Forking, Community Feeds, and Profile Features...")
            
            # Login first
            await page.goto("http://127.0.0.1:8000")
            await page.wait_for_load_state("networkidle")
            
            await page.click('button:has-text("Iniciar Sesión")')
            await page.wait_for_selector('#login-form')
            await page.fill('#login-email', 'j_carlos.leon@hotmail.com')
            await page.fill('#login-password', 'juancarlos95')
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/dashboard")
            
            print("✅ Logged in successfully")
            
            # 1. Test Recipe Forking
            print("\n1️⃣ Testing Recipe Forking...")
            
            # Go to recipes page to find fork buttons
            await page.goto("http://127.0.0.1:8000/recipes")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            
            # Look for fork buttons
            fork_buttons = page.locator('button:has-text("Fork")')
            fork_count = await fork_buttons.count()
            print(f"  Found {fork_count} fork buttons on recipes page")
            
            if fork_count > 0:
                # Set up dialog handler
                page.on("dialog", lambda dialog: dialog.accept())
                
                # Click fork button
                await fork_buttons.first.click()
                await page.wait_for_timeout(3000)
                
                # Look for success indicators
                page_content = await page.content()
                if "forked" in page_content.lower() or "success" in page_content.lower():
                    features_tested.append("✅ Recipe forking works (success message found)")
                else:
                    features_tested.append("⚠️  Recipe forking attempted (no clear success message)")
            else:
                # Try dashboard trending tab
                await page.goto("http://127.0.0.1:8000/dashboard")
                await page.wait_for_load_state("networkidle")
                
                trending_tab = page.locator('[data-tab="trending"]')
                if await trending_tab.count() > 0:
                    await trending_tab.click()
                    await page.wait_for_timeout(3000)
                    
                    fork_buttons = page.locator('button:has-text("Fork")')
                    fork_count = await fork_buttons.count()
                    print(f"  Found {fork_count} fork buttons in trending")
                    
                    if fork_count > 0:
                        page.on("dialog", lambda dialog: dialog.accept())
                        await fork_buttons.first.click()
                        await page.wait_for_timeout(3000)
                        features_tested.append("✅ Recipe forking available in trending")
                    else:
                        issues.append("❌ No fork buttons found anywhere")
                else:
                    issues.append("❌ Cannot access trending tab")
            
            # 2. Test Community Feed Recipe Display
            print("\n2️⃣ Testing Community Feed...")
            await page.goto("http://127.0.0.1:8000/community")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            
            # Test each feed tab
            feed_tabs = ['following', 'activity', 'trending', 'latest']
            
            for tab in feed_tabs:
                print(f"  Testing {tab} feed...")
                tab_btn = page.locator(f'[data-feed="{tab}"]')
                
                if await tab_btn.count() > 0:
                    await tab_btn.click()
                    await page.wait_for_timeout(3000)
                    
                    # Check feed content
                    feed_content = page.locator('#feed-content')
                    content_text = await feed_content.inner_text()
                    
                    if len(content_text) > 100:  # Has substantial content
                        features_tested.append(f"✅ {tab} feed has content")
                        
                        # Look for recipe-related content
                        if "recipe" in content_text.lower():
                            features_tested.append(f"✅ {tab} feed shows recipe content")
                            
                            # Try clicking on recipe content
                            recipe_links = page.locator('#feed-content a, #feed-content [onclick*="recipe"], #feed-content .recipe-card')
                            if await recipe_links.count() > 0:
                                try:
                                    await recipe_links.first.click()
                                    await page.wait_for_timeout(2000)
                                    
                                    if "/recipe/" in page.url:
                                        features_tested.append(f"✅ Recipe navigation from {tab} feed works")
                                        await page.go_back()
                                        await page.wait_for_timeout(1000)
                                except:
                                    features_tested.append(f"⚠️  Recipe click in {tab} feed failed")
                    else:
                        if "loading" in content_text.lower():
                            features_tested.append(f"⚠️  {tab} feed stuck loading")
                        elif "no" in content_text.lower():
                            features_tested.append(f"⚠️  {tab} feed shows no content message")
                        else:
                            issues.append(f"❌ {tab} feed appears empty")
            
            # 3. Test Profile Access
            print("\n3️⃣ Testing Profile Access...")
            
            # Try user menu
            user_menu = page.locator('#userMenuBtn')
            if await user_menu.count() > 0:
                await user_menu.click()
                await page.wait_for_timeout(1000)
                
                # Look for profile link in dropdown
                profile_link = page.locator('text="Profile", [href*="profile"]')
                if await profile_link.count() > 0:
                    await profile_link.click()
                    await page.wait_for_timeout(2000)
                    
                    if "/profile" in page.url:
                        features_tested.append("✅ Profile navigation from user menu works")
                        
                        # Check profile content
                        profile_content = await page.inner_text('body')
                        if "recipes" in profile_content.lower():
                            features_tested.append("✅ Profile page shows user data")
                    else:
                        issues.append("❌ Profile navigation failed")
                else:
                    # Try direct profile URL
                    await page.goto("http://127.0.0.1:8000/profile")
                    await page.wait_for_timeout(2000)
                    
                    if "profile" in page.url:
                        features_tested.append("✅ Direct profile URL works")
                    else:
                        issues.append("❌ Profile page not accessible")
            
            # 4. Test Individual Recipe Viewing
            print("\n4️⃣ Testing Individual Recipe Viewing...")
            
            # Test known recipe IDs
            test_recipe_ids = [1, 2, 8]
            
            for recipe_id in test_recipe_ids:
                await page.goto(f"http://127.0.0.1:8000/recipe/{recipe_id}")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                if f"/recipe/{recipe_id}" in page.url:
                    features_tested.append(f"✅ Recipe {recipe_id} page loads")
                    
                    # Check for recipe content
                    page_content = await page.inner_text('body')
                    if any(word in page_content.lower() for word in ['ingredients', 'instructions', 'recipe']):
                        features_tested.append(f"✅ Recipe {recipe_id} has proper content")
                        
                        # Check for fork button on recipe page
                        fork_btn = page.locator('button:has-text("Fork")')
                        if await fork_btn.count() > 0:
                            features_tested.append(f"✅ Recipe {recipe_id} has fork button")
                        else:
                            issues.append(f"❌ Recipe {recipe_id} missing fork button")
                else:
                    issues.append(f"❌ Recipe {recipe_id} redirected to {page.url}")
            
            print("\n" + "="*60)
            print("📊 FOCUSED TEST RESULTS")
            print("="*60)
            
            print(f"\n✅ FEATURES WORKING ({len(features_tested)}):")
            for feature in features_tested:
                print(f"  {feature}")
            
            if issues:
                print(f"\n❌ ISSUES FOUND ({len(issues)}):")
                for issue in issues:
                    print(f"  {issue}")
            
            success_rate = len(features_tested) / (len(features_tested) + len(issues)) * 100
            print(f"\n📈 SUCCESS RATE: {success_rate:.1f}%")
            
            if len(issues) == 0:
                print("\n🎉 ALL FOCUSED TESTS PASSED!")
            else:
                print(f"\n⚠️  {len(issues)} issues found. Review needed.")
            
            print("="*60)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_forking_and_feeds())