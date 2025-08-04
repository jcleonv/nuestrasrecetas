#!/usr/bin/env python3
"""
Test and identify critical issues: dashboard forks, profile errors, community feed recipes
"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_critical_issues():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capture console errors
        console_errors = []
        network_errors = []
        
        def handle_console(msg):
            if msg.type == 'error':
                console_errors.append(f"Console Error: {msg.text}")
                print(f"🔴 Console Error: {msg.text}")
        
        def handle_response(response):
            if response.status >= 400:
                network_errors.append(f"Network Error: {response.url} - {response.status}")
                print(f"🔴 Network Error: {response.url} - {response.status}")
        
        page.on("console", handle_console)
        page.on("response", handle_response)
        
        issues = []
        features_tested = []
        
        try:
            print("🔍 TESTING CRITICAL ISSUES...")
            print("="*70)
            
            # Login
            await page.goto("http://127.0.0.1:8000")
            await page.wait_for_load_state("networkidle")
            
            await page.click('button:has-text("Iniciar Sesión")')
            await page.wait_for_selector('#login-form')
            await page.fill('#login-email', 'j_carlos.leon@hotmail.com')
            await page.fill('#login-password', 'juancarlos95')
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/dashboard")
            print("✅ Logged in successfully")
            
            # ISSUE 1: Test Dashboard Forks Display
            print("\n1️⃣ TESTING DASHBOARD FORKS DISPLAY...")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            
            # Click on forks tab
            forks_tab = page.locator('[data-tab="forks"]')
            if await forks_tab.count() > 0:
                print("  Found forks tab, clicking...")
                await forks_tab.click()
                await page.wait_for_timeout(4000)  # Give extra time for loading
                
                # Check if forks are displayed
                fork_pills = page.locator('.recipe-pill')
                fork_count = await fork_pills.count()
                print(f"  Fork pills found: {fork_count}")
                
                if fork_count > 0:
                    features_tested.append(f"✅ Dashboard shows {fork_count} forks")
                    
                    # Check fork content
                    first_fork = fork_pills.first
                    fork_content = await first_fork.inner_text()
                    print(f"  First fork content: {fork_content[:100]}...")
                    
                    if len(fork_content.strip()) > 10:
                        features_tested.append("✅ Fork content is properly displayed")
                    else:
                        issues.append("❌ Fork pills are empty or have no content")
                else:
                    issues.append("❌ CRITICAL: No forks showing on dashboard despite forks existing")
                    
                    # Check for loading states or error messages
                    loading_indicators = await page.locator('.loading, [class*="loading"]').count()
                    error_messages = await page.locator('[class*="error"], .text-red').count()
                    
                    print(f"  Loading indicators: {loading_indicators}")
                    print(f"  Error messages: {error_messages}")
                    
                    if loading_indicators > 0:
                        issues.append("❌ Forks tab stuck in loading state")
                    if error_messages > 0:
                        issues.append("❌ Error messages present in forks tab")
                    
                    # Check the actual tab content area
                    tab_content = await page.locator('#recipe-list, .recipe-container, .tab-content').inner_text()
                    print(f"  Tab content area: {tab_content[:200]}...")
                    
            else:
                issues.append("❌ CRITICAL: Forks tab not found on dashboard")
            
            # ISSUE 2: Test Profile Functionality 
            print("\n2️⃣ TESTING PROFILE FUNCTIONALITY...")
            
            # Method 1: Try user menu dropdown
            user_menu_btn = page.locator('#userMenuBtn')
            if await user_menu_btn.count() > 0:
                print("  Found user menu button, clicking...")
                await user_menu_btn.click()
                await page.wait_for_timeout(1000)
                
                # Look for profile option in dropdown
                profile_option = page.locator('text="Profile", text="View Profile", [href*="profile"]')
                if await profile_option.count() > 0:
                    print("  Found profile option in menu...")
                    await profile_option.click()
                    await page.wait_for_timeout(3000)
                    
                    current_url = page.url
                    print(f"  Current URL after profile click: {current_url}")
                    
                    if "/profile" in current_url:
                        features_tested.append("✅ Profile navigation from menu works")
                        
                        # Check for profile content
                        page_content = await page.inner_text('body')
                        if "error" in page_content.lower() or "500" in page_content or "404" in page_content:
                            issues.append("❌ CRITICAL: Profile page shows error")
                            print(f"  Profile page error content: {page_content[:300]}...")
                        else:
                            features_tested.append("✅ Profile page loads without errors")
                    else:
                        issues.append("❌ Profile menu option doesn't navigate to profile")
                else:
                    print("  No profile option found in user menu")
            
            # Method 2: Try direct profile URL
            print("  Testing direct profile URL...")
            await page.goto("http://127.0.0.1:8000/profile")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            print(f"  Profile URL result: {current_url}")
            
            if "/profile" in current_url:
                page_content = await page.inner_text('body')
                if "error" in page_content.lower() or "500" in page_content or "404" in page_content:
                    issues.append("❌ CRITICAL: Direct profile URL shows error")
                    print(f"  Profile page error: {page_content[:500]}...")
                else:
                    features_tested.append("✅ Direct profile URL works")
                    
                    # Check for profile elements
                    profile_elements = [
                        page.locator('h1, h2, h3'),  # Profile title
                        page.locator('.avatar, [class*="avatar"]'),  # Avatar
                        page.locator('text="recipes", text="followers"')  # Stats
                    ]
                    
                    elements_found = 0
                    for element in profile_elements:
                        if await element.count() > 0:
                            elements_found += 1
                    
                    if elements_found >= 1:
                        features_tested.append(f"✅ Profile page has content elements ({elements_found}/3)")
                    else:
                        issues.append("❌ Profile page missing basic elements")
            else:
                issues.append("❌ CRITICAL: Profile URL redirects away from profile")
            
            # ISSUE 3: Test Community Feed Recipe Display
            print("\n3️⃣ TESTING COMMUNITY FEED RECIPE DISPLAY...")
            await page.goto("http://127.0.0.1:8000/community")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            
            # Test each feed tab for recipe content
            feed_tabs = ['following', 'activity', 'trending', 'latest']
            recipes_found_in_any_feed = False
            
            for tab in feed_tabs:
                print(f"  Testing {tab} feed...")
                tab_btn = page.locator(f'[data-feed="{tab}"]')
                
                if await tab_btn.count() > 0:
                    await tab_btn.click()
                    await page.wait_for_timeout(4000)  # Extra time for loading
                    
                    # Get feed content
                    feed_content_elem = page.locator('#feed-content')
                    feed_text = await feed_content_elem.inner_text()
                    print(f"    {tab} feed content length: {len(feed_text)}")
                    print(f"    {tab} feed preview: {feed_text[:150]}...")
                    
                    # Check for recipe-related content
                    recipe_indicators = [
                        "recipe",
                        "ingredient",
                        "cooking",
                        "fork",
                        "created",
                        "shared"
                    ]
                    
                    recipe_mentions = sum(1 for indicator in recipe_indicators if indicator in feed_text.lower())
                    print(f"    Recipe-related mentions in {tab}: {recipe_mentions}")
                    
                    if recipe_mentions > 0:
                        features_tested.append(f"✅ {tab} feed mentions recipes ({recipe_mentions} indicators)")
                        recipes_found_in_any_feed = True
                        
                        # Look for clickable recipe elements
                        clickable_elements = [
                            page.locator('#feed-content .recipe-card'),
                            page.locator('#feed-content [onclick*="recipe"]'),
                            page.locator('#feed-content a[href*="recipe"]'),
                            page.locator('#feed-content .glass-panel:has(h3)'),
                            page.locator('#feed-content .glass-panel:has(h4)')
                        ]
                        
                        clickable_found = False
                        for element in clickable_elements:
                            count = await element.count()
                            if count > 0:
                                print(f"      Found {count} clickable recipe elements")
                                features_tested.append(f"✅ {tab} feed has {count} clickable recipe elements")
                                clickable_found = True
                                
                                # Try clicking first element
                                try:
                                    await element.first.click()
                                    await page.wait_for_timeout(2000)
                                    
                                    if "/recipe/" in page.url:
                                        features_tested.append(f"✅ Recipe navigation from {tab} feed works")
                                        await page.go_back()
                                        await page.wait_for_timeout(1000)
                                    else:
                                        print(f"      Click didn't navigate to recipe page: {page.url}")
                                except Exception as e:
                                    print(f"      Failed to click recipe element: {e}")
                                break
                        
                        if not clickable_found:
                            issues.append(f"❌ {tab} feed mentions recipes but has no clickable elements")
                    
                    elif len(feed_text.strip()) < 50:
                        issues.append(f"❌ {tab} feed appears empty or minimal")
                    elif "loading" in feed_text.lower():
                        issues.append(f"❌ {tab} feed stuck in loading state")
                    else:
                        issues.append(f"❌ {tab} feed has content but no recipe mentions")
                else:
                    issues.append(f"❌ {tab} feed tab not found")
            
            if not recipes_found_in_any_feed:
                issues.append("❌ CRITICAL: No recipes found in any community feed")
            
            # ADDITIONAL: Test API endpoints directly
            print("\n4️⃣ TESTING API ENDPOINTS...")
            
            # Test community feed API
            try:
                response = await page.request.get("/api/community/feed", headers={"Cookie": await page.context.cookies()})
                if response.status == 200:
                    data = await response.json()
                    activities = data.get('activities', [])
                    print(f"  Community feed API returned {len(activities)} activities")
                    
                    if len(activities) > 0:
                        features_tested.append(f"✅ Community feed API working ({len(activities)} activities)")
                        
                        # Check if activities mention recipes
                        recipe_activities = [a for a in activities if 'recipe' in str(a).lower()]
                        if recipe_activities:
                            features_tested.append(f"✅ Community feed API includes recipe activities ({len(recipe_activities)})")
                        else:
                            issues.append("❌ Community feed API has no recipe activities")
                    else:
                        issues.append("❌ Community feed API returns empty activities")
                else:
                    issues.append(f"❌ Community feed API error: {response.status}")
            except Exception as e:
                issues.append(f"❌ Community feed API request failed: {e}")
            
            # Test recipes API
            try:
                response = await page.request.get("/api/recipes", headers={"Cookie": await page.context.cookies()})
                if response.status == 200:
                    data = await response.json()
                    recipes = data.get('recipes', [])
                    print(f"  Recipes API returned {len(recipes)} recipes")
                    
                    if len(recipes) > 0:
                        features_tested.append(f"✅ Recipes API working ({len(recipes)} recipes)")
                    else:
                        issues.append("❌ Recipes API returns no recipes")
                else:
                    issues.append(f"❌ Recipes API error: {response.status}")
            except Exception as e:
                issues.append(f"❌ Recipes API request failed: {e}")
            
            print("\n" + "="*70)
            print("🔍 CRITICAL ISSUES TEST RESULTS")
            print("="*70)
            
            print(f"\n✅ WORKING FEATURES ({len(features_tested)}):")
            for feature in features_tested:
                print(f"  {feature}")
            
            print(f"\n❌ CRITICAL ISSUES FOUND ({len(issues)}):")
            for issue in issues:
                print(f"  {issue}")
            
            if console_errors:
                print(f"\n🔴 CONSOLE ERRORS ({len(console_errors)}):")
                for error in console_errors:
                    print(f"  {error}")
            
            if network_errors:
                print(f"\n🌐 NETWORK ERRORS ({len(network_errors)}):")
                for error in network_errors:
                    print(f"  {error}")
            
            # Final assessment
            critical_issues = len(issues)
            if critical_issues == 0:
                print(f"\n🎉 ALL CRITICAL ISSUES RESOLVED!")
                print("🚀 READY FOR PRODUCTION!")
            else:
                print(f"\n⚠️  {critical_issues} CRITICAL ISSUES MUST BE FIXED BEFORE PRODUCTION")
                print("🛑 DO NOT MERGE UNTIL ISSUES ARE RESOLVED")
            
            success_rate = len(features_tested) / (len(features_tested) + len(issues)) * 100 if (features_tested or issues) else 100
            print(f"\n📊 SUCCESS RATE: {success_rate:.1f}%")
            print("="*70)
            
        except Exception as e:
            print(f"❌ Critical test failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_critical_issues())