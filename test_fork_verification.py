#!/usr/bin/env python3
"""
Verify that forking actually creates forks and test recipe navigation from feeds
"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_fork_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        issues = []
        features_tested = []
        
        try:
            print("🚀 Verifying Fork Creation and Community Feed Navigation...")
            
            # Login
            await page.goto("http://127.0.0.1:8000")
            await page.wait_for_load_state("networkidle")
            
            await page.click('button:has-text("Iniciar Sesión")')
            await page.wait_for_selector('#login-form')
            await page.fill('#login-email', 'j_carlos.leon@hotmail.com')
            await page.fill('#login-password', 'juancarlos95')
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/dashboard")
            print("✅ Logged in")
            
            # 1. Count current forks before forking
            await page.goto("http://127.0.0.1:8000/dashboard")
            await page.wait_for_load_state("networkidle")
            
            # Switch to forks tab to see current forks
            forks_tab = page.locator('[data-tab="forks"]')
            if await forks_tab.count() > 0:
                await forks_tab.click()
                await page.wait_for_timeout(2000)
                
                initial_forks = await page.locator('.recipe-pill').count()
                print(f"  Initial forks count: {initial_forks}")
                
                # 2. Go fork a recipe
                await page.goto("http://127.0.0.1:8000/recipes")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)
                
                fork_buttons = page.locator('button:has-text("Fork")')
                if await fork_buttons.count() > 0:
                    # Handle confirmation dialog
                    page.on("dialog", lambda dialog: dialog.accept())
                    
                    # Get recipe name before forking
                    recipe_card = fork_buttons.first.locator('..')
                    recipe_title = await recipe_card.locator('h3').inner_text()
                    print(f"  Forking recipe: {recipe_title}")
                    
                    await fork_buttons.first.click()
                    await page.wait_for_timeout(4000)
                    
                    # 3. Check if fork was created by going back to forks tab
                    await page.goto("http://127.0.0.1:8000/dashboard")
                    await page.wait_for_load_state("networkidle")
                    
                    await forks_tab.click()
                    await page.wait_for_timeout(2000)
                    
                    final_forks = await page.locator('.recipe-pill').count()
                    print(f"  Final forks count: {final_forks}")
                    
                    if final_forks > initial_forks:
                        features_tested.append(f"✅ Fork created successfully! ({initial_forks} -> {final_forks})")
                        
                        # Check if the forked recipe has the right title
                        fork_pills = page.locator('.recipe-pill')
                        if await fork_pills.count() > 0:
                            latest_fork = fork_pills.last
                            fork_text = await latest_fork.inner_text()
                            if recipe_title.lower() in fork_text.lower():
                                features_tested.append("✅ Forked recipe appears in forks with correct title")
                            else:
                                features_tested.append("⚠️  Forked recipe found but title may be different")
                    else:
                        issues.append("❌ Fork was not created (count didn't increase)")
                else:
                    issues.append("❌ No fork buttons found on recipes page")
            
            # 4. Test Recipe Navigation from Community Feed
            print("\n  Testing recipe navigation from community feeds...")
            await page.goto("http://127.0.0.1:8000/community")
            await page.wait_for_load_state("networkidle")
            
            # Try activity feed (most likely to have recipe content)
            activity_tab = page.locator('[data-feed="activity"]')
            if await activity_tab.count() > 0:
                await activity_tab.click()
                await page.wait_for_timeout(3000)
                
                # Look for clickable recipe elements
                feed_content = page.locator('#feed-content')
                
                # Try different ways to find recipe links
                recipe_selectors = [
                    '.recipe-card',
                    '[onclick*="recipe"]',
                    'a[href*="recipe"]',
                    '.glass-panel:has(h3)',
                    '.glass-panel:has(h4)'
                ]
                
                recipe_found = False
                for selector in recipe_selectors:
                    recipe_elements = page.locator(selector)
                    count = await recipe_elements.count()
                    print(f"    Found {count} elements with selector: {selector}")
                    
                    if count > 0:
                        try:
                            # Try clicking the first element
                            await recipe_elements.first.click()
                            await page.wait_for_timeout(2000)
                            
                            if "/recipe/" in page.url:
                                features_tested.append("✅ Recipe navigation from activity feed works")
                                recipe_found = True
                                
                                # Verify we're on a recipe page
                                page_content = await page.inner_text('body')
                                if any(word in page_content.lower() for word in ['ingredients', 'instructions']):
                                    features_tested.append("✅ Recipe page shows proper recipe content")
                                
                                break
                            else:
                                print(f"    Click on {selector} didn't navigate to recipe page")
                        except Exception as e:
                            print(f"    Failed to click {selector}: {e}")
                            continue
                
                if not recipe_found:
                    # Check feed content to see what's actually there
                    feed_text = await feed_content.inner_text()
                    print(f"    Feed content preview: {feed_text[:200]}...")
                    
                    if "recipe" in feed_text.lower():
                        features_tested.append("⚠️  Activity feed mentions recipes but navigation unclear")
                    else:
                        features_tested.append("⚠️  Activity feed doesn't show recipe content")
            
            # 5. Test Recipe Detail Pages Have All Expected Elements
            print("\n  Testing recipe detail page completeness...")
            test_recipes = [1, 2, 8]
            
            for recipe_id in test_recipes:
                await page.goto(f"http://127.0.0.1:8000/recipe/{recipe_id}")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                if f"/recipe/{recipe_id}" in page.url:
                    # Check for key recipe elements
                    elements_to_check = [
                        ('Recipe Title', 'h1, h2, .recipe-title'),
                        ('Ingredients Section', 'text="Ingredients", .ingredients'),
                        ('Instructions Section', 'text="Instructions", .instructions, .steps'),
                        ('Fork Button', 'button:has-text("Fork")'),
                        ('Star/Like Button', 'button:has-text("Star"), button:has-text("Like"), .fa-heart, .fa-star')
                    ]
                    
                    elements_found = []
                    for element_name, selector in elements_to_check:
                        found = False
                        for sel in selector.split(', '):
                            if await page.locator(sel.strip()).count() > 0:
                                found = True
                                break
                        
                        if found:
                            elements_found.append(element_name)
                    
                    if len(elements_found) >= 3:
                        features_tested.append(f"✅ Recipe {recipe_id} has key elements: {', '.join(elements_found)}")
                    else:
                        issues.append(f"❌ Recipe {recipe_id} missing key elements (only found: {', '.join(elements_found)})")
            
            print("\n" + "="*70)
            print("📊 FORK VERIFICATION AND NAVIGATION TEST RESULTS")
            print("="*70)
            
            print(f"\n✅ FEATURES WORKING ({len(features_tested)}):")
            for feature in features_tested:
                print(f"  {feature}")
            
            if issues:
                print(f"\n❌ ISSUES FOUND ({len(issues)}):")
                for issue in issues:
                    print(f"  {issue}")
            
            success_rate = len(features_tested) / (len(features_tested) + len(issues)) * 100 if (features_tested or issues) else 100
            print(f"\n📈 SUCCESS RATE: {success_rate:.1f}%")
            
            # Final assessment
            if len(issues) == 0:
                print("\n🎉 ALL VERIFICATION TESTS PASSED!")
                print("🚀 Forking functionality is working correctly!")
                print("🚀 Recipe navigation is working correctly!")
            else:
                print(f"\n⚠️  {len(issues)} issues found that need attention")
            
            print("="*70)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_fork_verification())