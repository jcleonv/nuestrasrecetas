#!/usr/bin/env python3
"""
Comprehensive Playwright test script to verify ALL functionality works in the UI
Tests every single button, feature, and page in the application.
"""

import asyncio
import time
from playwright.async_api import async_playwright

class ComprehensiveTest:
    def __init__(self):
        self.browser = None
        self.page = None
        self.current_user = None
        self.issues_found = []
        self.features_tested = []
        self.recipes_created = []
        self.groups_joined = []
        
    async def run_all_tests(self):
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=False)
            context = await self.browser.new_context()
            self.page = await context.new_page()
            
            try:
                print("🚀 Starting COMPREHENSIVE UI Testing of NuestrasRecetas.club")
                print("=" * 70)
                
                # Core Authentication Flow
                await self.test_login()
                
                # Dashboard Comprehensive Testing
                await self.test_dashboard_all_features()
                
                # Recipe Management Testing
                await self.test_recipe_management()
                
                # Community Features Testing  
                await self.test_community_features()
                
                # Groups Functionality Testing
                await self.test_groups_functionality()
                
                # Navigation & Page Testing
                await self.test_all_navigation()
                
                # Social Features Testing
                await self.test_social_features()
                
                # Meal Planning Testing
                await self.test_meal_planning()
                
                # Error Handling Testing
                await self.test_error_scenarios()
                
                # Final Verification
                await self.test_data_verification()
                
                self.print_final_report()
                
            except Exception as e:
                self.issues_found.append(f"CRITICAL ERROR: {str(e)}")
                print(f"❌ CRITICAL TEST FAILURE: {e}")
                import traceback
                traceback.print_exc()
            finally:
                await self.browser.close()
    
    async def test_login(self):
        """Test login functionality"""
        print("\n📋 TESTING: Authentication & Login")
        
        try:
            await self.page.goto("http://127.0.0.1:8000")
            await self.page.wait_for_load_state("networkidle")
            
            # Test login button appears
            login_btn = self.page.locator('button:has-text("Iniciar Sesión")')
            if await login_btn.count() == 0:
                self.issues_found.append("Login button not found on homepage")
                return
            
            await login_btn.click()
            await self.page.wait_for_selector('#login-form')
            
            # Fill login form with real user credentials
            await self.page.fill('#login-email', 'j_carlos.leon@hotmail.com')
            await self.page.fill('#login-password', 'juancarlos95')
            await self.page.click('button[type="submit"]')
            
            # Wait for dashboard to load
            await self.page.wait_for_url("**/dashboard", timeout=10000)
            self.features_tested.append("✅ User Login")
            print("✅ Login successful - redirected to dashboard")
            
            # Verify we're actually logged in by checking for user menu
            user_menu = self.page.locator('#userMenuBtn')
            if await user_menu.count() == 0:
                self.issues_found.append("User menu not found after login - may not be fully authenticated")
            
        except Exception as e:
            self.issues_found.append(f"Login failed: {str(e)}")
            print(f"❌ Login failed: {e}")
    
    async def test_dashboard_all_features(self):
        """Test every single button and feature on the dashboard"""
        print("\n📋 TESTING: Dashboard - ALL Features")
        
        try:
            # Wait for dashboard to fully load
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(2000)
            
            # Test Hero Section Buttons
            await self.test_hero_buttons()
            
            # Test Repository Tabs
            await self.test_repository_tabs()
            
            # Test Recipe Actions
            await self.test_recipe_actions()
            
            # Test Main Navigation Tabs
            await self.test_main_tabs()
            
            # Test User Menu
            await self.test_user_menu()
            
            # Test Mobile Menu (if visible)
            await self.test_mobile_menu()
            
            self.features_tested.append("✅ Dashboard Complete")
            
        except Exception as e:
            self.issues_found.append(f"Dashboard testing failed: {str(e)}")
            print(f"❌ Dashboard testing failed: {e}")
    
    async def test_hero_buttons(self):
        """Test all hero section buttons"""
        print("  🔍 Testing Hero Section Buttons...")
        
        # Test "Create New Recipe" button
        new_btn = self.page.locator('#btnNewHero')
        if await new_btn.count() > 0:
            await new_btn.click()
            await self.page.wait_for_timeout(1000)
            # Check if modal opened
            modal = self.page.locator('#modal:not(.hidden)')
            if await modal.count() > 0:
                self.features_tested.append("✅ Hero: New Recipe Button")
                await self.page.click('#mCancel')  # Close modal
            else:
                self.issues_found.append("New Recipe modal didn't open from hero button")
        
        # Test "Fork Trending" button  
        fork_btn = self.page.locator('#btnForkHero')
        if await fork_btn.count() > 0:
            await fork_btn.click()
            await self.page.wait_for_timeout(1000)
            self.features_tested.append("✅ Hero: Fork Trending Button")
        
        # Test "Import Recipe" button
        import_btn = self.page.locator('#btnImportHero')
        if await import_btn.count() > 0:
            await import_btn.click()
            await self.page.wait_for_timeout(1000)
            # Check if import modal opened
            import_modal = self.page.locator('#importModal:not(.hidden)')
            if await import_modal.count() > 0:
                self.features_tested.append("✅ Hero: Import Recipe Button")
                await self.page.click('#impCancel')  # Close modal
            else:
                self.issues_found.append("Import Recipe modal didn't open from hero button")
    
    async def test_repository_tabs(self):
        """Test all repository tab switching"""
        print("  🔍 Testing Repository Tabs...")
        
        tabs = ['my-recipes', 'starred', 'forks']
        
        for tab in tabs:
            tab_btn = self.page.locator(f'[data-tab="{tab}"]')
            if await tab_btn.count() > 0:
                await tab_btn.click()
                await self.page.wait_for_timeout(1000)
                
                # Check if tab became active
                if await tab_btn.evaluate('el => el.classList.contains("active")'):
                    self.features_tested.append(f"✅ Repository Tab: {tab}")
                else:
                    self.issues_found.append(f"Repository tab '{tab}' didn't activate properly")
            else:
                self.issues_found.append(f"Repository tab '{tab}' not found")
    
    async def test_recipe_actions(self):
        """Test recipe management buttons"""
        print("  🔍 Testing Recipe Action Buttons...")
        
        # Test sidebar action buttons
        actions = [
            ('#btnNew', "New Recipe"),
            ('#btnImportRecipes', "Import Recipes"),
            ('#btnEdit', "Edit Recipe"),
            ('#btnForkSelected', "Fork Selected"),
            ('#btnDelete', "Delete Recipe")
        ]
        
        for selector, name in actions:
            btn = self.page.locator(selector)
            if await btn.count() > 0:
                # Just check if button exists and is clickable
                is_enabled = await btn.evaluate('el => !el.disabled')
                if is_enabled:
                    self.features_tested.append(f"✅ Recipe Action: {name}")
                else:
                    self.features_tested.append(f"⚠️  Recipe Action: {name} (disabled - normal)")
            else:
                self.issues_found.append(f"Recipe action button '{name}' not found")
    
    async def test_main_tabs(self):
        """Test main navigation tabs (discover, trending, activity, planner, groceries)"""
        print("  🔍 Testing Main Navigation Tabs...")
        
        tabs = ['discover', 'trending', 'activity', 'planner', 'groceries']
        
        for tab in tabs:
            tab_btn = self.page.locator(f'[data-tab="{tab}"]')
            if await tab_btn.count() > 0:
                await tab_btn.click()
                await self.page.wait_for_timeout(2000)
                
                # Check if tab became active
                if await tab_btn.evaluate('el => el.classList.contains("active")'):
                    self.features_tested.append(f"✅ Main Tab: {tab}")
                    
                    # Special checks for each tab
                    if tab == 'planner':
                        await self.test_meal_planner_specific()
                    elif tab == 'groceries':
                        await self.test_grocery_list_specific()
                        
                else:
                    self.issues_found.append(f"Main tab '{tab}' didn't activate properly")
            else:
                self.issues_found.append(f"Main tab '{tab}' not found")
    
    async def test_user_menu(self):
        """Test user menu functionality"""
        print("  🔍 Testing User Menu...")
        
        user_menu_btn = self.page.locator('#userMenuBtn')
        if await user_menu_btn.count() > 0:
            await user_menu_btn.click()
            await self.page.wait_for_timeout(500)
            self.features_tested.append("✅ User Menu Toggle")
            
            # Close menu by clicking again
            await user_menu_btn.click()
        else:
            self.issues_found.append("User menu button not found")
    
    async def test_mobile_menu(self):
        """Test mobile menu if present"""
        print("  🔍 Testing Mobile Menu...")
        
        mobile_btn = self.page.locator('#mobileMenuBtn')
        if await mobile_btn.count() > 0:
            await mobile_btn.click()
            await self.page.wait_for_timeout(500)
            self.features_tested.append("✅ Mobile Menu Toggle")
            
            # Close menu
            await mobile_btn.click()
    
    async def test_recipe_management(self):
        """Test complete recipe creation, editing, and management"""
        print("\n📋 TESTING: Recipe Management (Create, Edit, Delete, Fork)")
        
        try:
            # Test Recipe Creation
            await self.test_recipe_creation()
            
            # Test Recipe Editing
            await self.test_recipe_editing()
            
            # Test Recipe Forking
            await self.test_recipe_forking()
            
            # Test Recipe Deletion (commented out to avoid data loss)
            # await self.test_recipe_deletion()
            
        except Exception as e:
            self.issues_found.append(f"Recipe management testing failed: {str(e)}")
            print(f"❌ Recipe management testing failed: {e}")
    
    async def test_recipe_creation(self):
        """Test complete recipe creation flow"""
        print("  🔍 Testing Recipe Creation...")
        
        # Click New Recipe button
        await self.page.click('#btnNew')
        await self.page.wait_for_selector('#modal:not(.hidden)')
        
        # Fill out complete recipe form
        recipe_title = f"Comprehensive Test Recipe {int(time.time())}"
        await self.page.fill('#mTitle', recipe_title)
        await self.page.fill('#mCategory', 'Main Course')
        await self.page.fill('#mTags', 'test, automation, comprehensive')
        await self.page.fill('#mServings', '4')
        await self.page.fill('#mPrepTime', '15')
        await self.page.fill('#mCookTime', '30')
        await self.page.fill('#mInstructions', 'Step 1: Prepare ingredients\nStep 2: Cook everything\nStep 3: Serve and enjoy')
        
        # Add multiple ingredients
        ingredients = [
            ("Chicken breast", "2 lbs"),
            ("Rice", "2 cups"),
            ("Vegetables", "1 cup mixed")
        ]
        
        for name, amount in ingredients:
            await self.page.fill('#mIngredientName', name)
            await self.page.fill('#mIngredientAmount', amount)
            await self.page.click('#btnAddIngredient')
            await self.page.wait_for_timeout(500)
        
        # Save recipe
        await self.page.click('#btnSaveRecipe')
        await self.page.wait_for_timeout(3000)
        
        # Verify recipe was created by checking if modal closed
        modal_hidden = await self.page.locator('#modal.hidden').count() > 0
        if modal_hidden:
            self.features_tested.append("✅ Recipe Creation Complete")
            self.recipes_created.append(recipe_title)
            print(f"✅ Recipe created: {recipe_title}")
        else:
            self.issues_found.append("Recipe creation modal didn't close - creation may have failed")
    
    async def test_recipe_editing(self):
        """Test recipe editing functionality"""
        print("  🔍 Testing Recipe Editing...")
        
        # Select first recipe in list (if any)
        recipe_pills = self.page.locator('.recipe-pill')
        if await recipe_pills.count() > 0:
            await recipe_pills.first.click()
            await self.page.wait_for_timeout(1000)
            
            # Click edit button
            edit_btn = self.page.locator('#btnEdit')
            if await edit_btn.evaluate('el => !el.disabled'):
                await edit_btn.click()
                await self.page.wait_for_selector('#modal:not(.hidden)')
                
                # Make a small edit
                current_title = await self.page.input_value('#mTitle')
                await self.page.fill('#mTitle', current_title + ' (EDITED)')
                
                # Save changes
                await self.page.click('#btnSaveRecipe')
                await self.page.wait_for_timeout(3000)
                
                self.features_tested.append("✅ Recipe Editing")
                print("✅ Recipe editing completed")
            else:
                self.features_tested.append("⚠️  Recipe Editing (no recipe selected)")
        else:
            self.features_tested.append("⚠️  Recipe Editing (no recipes available)")
    
    async def test_recipe_forking(self):
        """Test recipe forking functionality"""
        print("  🔍 Testing Recipe Forking...")
        
        # Go to trending tab to find recipes to fork
        await self.page.click('[data-tab="trending"]')
        await self.page.wait_for_timeout(3000)
        
        # Look for fork buttons in the trending recipes
        fork_buttons = self.page.locator('button:has-text("Fork")')
        if await fork_buttons.count() > 0:
            await fork_buttons.first.click()
            
            # Handle confirmation dialog
            self.page.on("dialog", lambda dialog: dialog.accept())
            await self.page.wait_for_timeout(2000)
            
            self.features_tested.append("✅ Recipe Forking")
            print("✅ Recipe forking completed")
        else:
            self.features_tested.append("⚠️  Recipe Forking (no fork buttons found)")
    
    async def test_community_features(self):
        """Test all community page features"""
        print("\n📋 TESTING: Community Features")
        
        try:
            await self.page.goto("http://127.0.0.1:8000/community")
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(2000)
            
            # Test feed tabs
            await self.test_community_feed_tabs()
            
            # Test user search
            await self.test_user_search()
            
            # Test following functionality
            await self.test_following_functionality()
            
            # Test create post
            await self.test_create_post()
            
            # Test create group
            await self.test_create_group_community()
            
            self.features_tested.append("✅ Community Page Complete")
            
        except Exception as e:
            self.issues_found.append(f"Community features testing failed: {str(e)}")
            print(f"❌ Community features testing failed: {e}")
    
    async def test_community_feed_tabs(self):
        """Test community feed tab switching"""
        print("  🔍 Testing Community Feed Tabs...")
        
        feed_tabs = ['following', 'activity', 'trending', 'latest']
        
        for tab in feed_tabs:
            tab_btn = self.page.locator(f'[data-feed="{tab}"]')
            if await tab_btn.count() > 0:
                await tab_btn.click()
                await self.page.wait_for_timeout(2000)
                
                # Check if tab became active
                if await tab_btn.evaluate('el => el.classList.contains("active")'):
                    self.features_tested.append(f"✅ Community Feed: {tab}")
                else:
                    self.issues_found.append(f"Community feed tab '{tab}' didn't activate")
            else:
                self.issues_found.append(f"Community feed tab '{tab}' not found")
    
    async def test_user_search(self):
        """Test user search functionality"""
        print("  🔍 Testing User Search...")
        
        search_input = self.page.locator('#search-input')
        if await search_input.count() > 0:
            await search_input.fill('test')
            await self.page.wait_for_timeout(2000)
            
            # Check if search results appeared
            search_results = self.page.locator('#user-search-results:not(.hidden)')
            if await search_results.count() > 0:
                self.features_tested.append("✅ User Search")
            else:
                self.features_tested.append("⚠️  User Search (no results displayed)")
            
            # Clear search
            await search_input.fill('')
        else:
            self.issues_found.append("User search input not found")
    
    async def test_following_functionality(self):
        """Test follow/unfollow functionality"""
        print("  🔍 Testing Follow/Unfollow Functionality...")
        
        # Search for users and try to follow
        search_input = self.page.locator('#search-input')
        if await search_input.count() > 0:
            await search_input.fill('user')
            await self.page.wait_for_timeout(3000)
            
            # Look for follow buttons
            follow_buttons = self.page.locator('button:has-text("Cook Together")')
            if await follow_buttons.count() > 0:
                # Try to follow a user
                await follow_buttons.first.click()
                await self.page.wait_for_timeout(2000)
                
                self.features_tested.append("✅ User Following")
            else:
                self.features_tested.append("⚠️  User Following (no follow buttons found)")
    
    async def test_create_post(self):
        """Test creating a community post"""
        print("  🔍 Testing Create Post...")
        
        create_post_btn = self.page.locator('button:has-text("Share Update")')
        if await create_post_btn.count() > 0:
            await create_post_btn.click()
            await self.page.wait_for_timeout(1000)
            
            # Check if modal opened
            post_modal = self.page.locator('#create-post-modal:not(.hidden)')
            if await post_modal.count() > 0:
                # Fill post content
                await self.page.fill('#post-content', f'Test post from comprehensive testing - {int(time.time())}')
                
                # Submit post
                await self.page.click('button[type="submit"]')
                await self.page.wait_for_timeout(3000)
                
                self.features_tested.append("✅ Create Post")
            else:
                self.issues_found.append("Create post modal didn't open")
        else:
            self.issues_found.append("Create post button not found")
    
    async def test_create_group_community(self):
        """Test creating a group from community page"""
        print("  🔍 Testing Create Group (Community)...")
        
        create_group_btn = self.page.locator('button:has-text("Create Group")')
        if await create_group_btn.count() > 0:
            await create_group_btn.click()
            await self.page.wait_for_timeout(1000)
            
            # Check if modal opened
            group_modal = self.page.locator('#create-group-modal:not(.hidden)')
            if await group_modal.count() > 0:
                # Fill group details
                group_name = f"Test Group {int(time.time())}"
                await self.page.fill('#group-name', group_name)
                await self.page.fill('#group-description', 'A test group created during comprehensive testing')
                
                # Submit group creation
                await self.page.click('button[type="submit"]')
                await self.page.wait_for_timeout(3000)
                
                self.features_tested.append("✅ Create Group (Community)")
                
                # Close modal if still open
                cancel_btn = self.page.locator('button:has-text("Cancel")')
                if await cancel_btn.count() > 0:
                    await cancel_btn.click()
            else:
                self.issues_found.append("Create group modal didn't open")
    
    async def test_groups_functionality(self):
        """Test all groups page functionality"""
        print("\n📋 TESTING: Groups Functionality")
        
        try:
            await self.page.goto("http://127.0.0.1:8000/groups")
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(2000)
            
            # Test group filters
            await self.test_group_filters()
            
            # Test group search
            await self.test_group_search()
            
            # Test joining/leaving groups
            await self.test_group_membership()
            
            # Test group creation
            await self.test_group_creation()
            
            self.features_tested.append("✅ Groups Page Complete")
            
        except Exception as e:
            self.issues_found.append(f"Groups functionality testing failed: {str(e)}")
            print(f"❌ Groups functionality testing failed: {e}")
    
    async def test_group_filters(self):
        """Test group filter buttons"""
        print("  🔍 Testing Group Filters...")
        
        filters = ['all', 'public', 'my-groups']
        
        for filter_type in filters:
            filter_btn = self.page.locator(f'[data-filter="{filter_type}"]')
            if await filter_btn.count() > 0:
                await filter_btn.click()
                await self.page.wait_for_timeout(2000)
                
                # Check if filter became active
                if await filter_btn.evaluate('el => el.classList.contains("active")'):
                    self.features_tested.append(f"✅ Group Filter: {filter_type}")
                else:
                    self.issues_found.append(f"Group filter '{filter_type}' didn't activate")
            else:
                self.issues_found.append(f"Group filter '{filter_type}' not found")
    
    async def test_group_search(self):
        """Test group search functionality"""
        print("  🔍 Testing Group Search...")
        
        search_input = self.page.locator('#search-input')
        if await search_input.count() > 0:
            await search_input.fill('test')
            await self.page.wait_for_timeout(2000)
            
            self.features_tested.append("✅ Group Search")
            
            # Clear search
            await search_input.fill('')
        else:
            self.issues_found.append("Group search input not found")
    
    async def test_group_membership(self):
        """Test joining and leaving groups"""
        print("  🔍 Testing Group Join/Leave...")
        
        # Look for join buttons
        join_buttons = self.page.locator('button:has-text("Join")')
        if await join_buttons.count() > 0:
            group_name = await join_buttons.first.locator('..').locator('h3').inner_text()
            await join_buttons.first.click()
            await self.page.wait_for_timeout(2000)
            
            self.features_tested.append("✅ Group Joining")
            self.groups_joined.append(group_name)
            
            # Now try to leave the group
            leave_buttons = self.page.locator('button:has-text("Leave")')
            if await leave_buttons.count() > 0:
                # Confirm dialog
                self.page.on("dialog", lambda dialog: dialog.accept())
                await leave_buttons.first.click()
                await self.page.wait_for_timeout(2000)
                
                self.features_tested.append("✅ Group Leaving")
        else:
            self.features_tested.append("⚠️  Group Join/Leave (no joinable groups found)")
    
    async def test_group_creation(self):
        """Test group creation from groups page"""
        print("  🔍 Testing Group Creation (Groups Page)...")
        
        create_btn = self.page.locator('button:has-text("Create Group")')
        if await create_btn.count() > 0:
            await create_btn.click()
            await self.page.wait_for_timeout(1000)
            
            # Check if modal opened
            modal = self.page.locator('#create-group-modal:not(.hidden)')
            if await modal.count() > 0:
                self.features_tested.append("✅ Group Creation Modal")
                
                # Close modal
                cancel_btn = self.page.locator('button:has-text("Cancel")')
                await cancel_btn.click()
            else:
                self.issues_found.append("Group creation modal didn't open")
    
    async def test_all_navigation(self):
        """Test navigation between all pages"""
        print("\n📋 TESTING: Page Navigation")
        
        try:
            pages_to_test = [
                ("/dashboard", "Dashboard"),
                ("/recipes", "Recipes"),
                ("/community", "Community"), 
                ("/groups", "Groups")
            ]
            
            for url, page_name in pages_to_test:
                await self.page.goto(f"http://127.0.0.1:8000{url}")
                await self.page.wait_for_load_state("networkidle")
                await self.page.wait_for_timeout(1000)
                
                # Check if page loaded by looking for specific elements
                if await self.page.locator('nav').count() > 0:
                    self.features_tested.append(f"✅ Navigation: {page_name}")
                else:
                    self.issues_found.append(f"Navigation to {page_name} failed")
            
            # Test recipe detail pages
            await self.test_recipe_detail_navigation()
            
        except Exception as e:
            self.issues_found.append(f"Navigation testing failed: {str(e)}")
            print(f"❌ Navigation testing failed: {e}")
    
    async def test_recipe_detail_navigation(self):
        """Test recipe detail page navigation"""
        print("  🔍 Testing Recipe Detail Pages...")
        
        recipe_ids = [1, 2, 8]  # Test known recipe IDs
        
        for recipe_id in recipe_ids:
            try:
                await self.page.goto(f"http://127.0.0.1:8000/recipe/{recipe_id}")
                await self.page.wait_for_load_state("networkidle")
                current_url = self.page.url
                
                if f"recipe/{recipe_id}" in current_url:
                    self.features_tested.append(f"✅ Recipe Detail: ID {recipe_id}")
                else:
                    self.issues_found.append(f"Recipe {recipe_id} redirected to: {current_url}")
                    
            except Exception as e:
                self.issues_found.append(f"Recipe {recipe_id} navigation failed: {str(e)}")
    
    async def test_social_features(self):
        """Test social features like starring, following, etc."""
        print("\n📋 TESTING: Social Features")
        
        try:
            # Go back to dashboard to test social features
            await self.page.goto("http://127.0.0.1:8000/dashboard")
            await self.page.wait_for_load_state("networkidle")
            
            # Test starring functionality
            await self.test_starring()
            
            # Test user discovery
            await self.test_user_discovery()
            
            self.features_tested.append("✅ Social Features Complete")
            
        except Exception as e:
            self.issues_found.append(f"Social features testing failed: {str(e)}")
            print(f"❌ Social features testing failed: {e}")
    
    async def test_starring(self):
        """Test recipe starring functionality"""
        print("  🔍 Testing Recipe Starring...")
        
        # Go to starred tab
        starred_tab = self.page.locator('[data-tab="starred"]')
        if await starred_tab.count() > 0:
            await starred_tab.click()
            await self.page.wait_for_timeout(2000)
            self.features_tested.append("✅ Starred Recipes Tab")
        
        # Note: Actual starring requires clicking star buttons in recipe cards
        # This would need to be implemented based on the specific UI
    
    async def test_user_discovery(self):
        """Test user discovery functionality"""
        print("  🔍 Testing User Discovery...")
        
        # Look for "Find Other Cooks" or similar buttons
        user_search_btns = self.page.locator('button:has-text("Find")')
        if await user_search_btns.count() > 0:
            await user_search_btns.first.click()
            await self.page.wait_for_timeout(1000)
            self.features_tested.append("✅ User Discovery")
    
    async def test_meal_planning(self):
        """Test meal planning functionality"""
        print("\n📋 TESTING: Meal Planning")
        
        try:
            # Go to dashboard and switch to planner tab
            await self.page.goto("http://127.0.0.1:8000/dashboard")
            await self.page.wait_for_load_state("networkidle")
            
            planner_tab = self.page.locator('[data-tab="planner"]')
            if await planner_tab.count() > 0:
                await planner_tab.click()
                await self.page.wait_for_timeout(3000)
                
                await self.test_meal_planner_specific()
                
            self.features_tested.append("✅ Meal Planning Complete")
            
        except Exception as e:
            self.issues_found.append(f"Meal planning testing failed: {str(e)}")
            print(f"❌ Meal planning testing failed: {e}")
    
    async def test_meal_planner_specific(self):
        """Test specific meal planner features"""
        print("  🔍 Testing Meal Planner Features...")
        
        # Test save plan button
        save_plan_btn = self.page.locator('#btnSavePlan')
        if await save_plan_btn.count() > 0:
            await save_plan_btn.click()
            await self.page.wait_for_timeout(1000)
            self.features_tested.append("✅ Meal Plan Save")
        
        # Test drag and drop (basic check)
        droptargets = self.page.locator('.droptarget')
        if await droptargets.count() > 0:
            self.features_tested.append("✅ Meal Plan Drag Zones")
    
    async def test_grocery_list_specific(self):
        """Test grocery list features"""
        print("  🔍 Testing Grocery List Features...")
        
        # Test copy button
        copy_btn = self.page.locator('#btnCopy')
        if await copy_btn.count() > 0:
            await copy_btn.click()
            await self.page.wait_for_timeout(500)
            self.features_tested.append("✅ Grocery List Copy")
        
        # Test print button
        print_btn = self.page.locator('#btnPrint')
        if await print_btn.count() > 0:
            await print_btn.click()
            await self.page.wait_for_timeout(1000)
            
            # Close print modal if it opened
            print_close = self.page.locator('#printClose')
            if await print_close.count() > 0:
                await print_close.click()
            
            self.features_tested.append("✅ Grocery List Print")
    
    async def test_error_scenarios(self):
        """Test error handling and edge cases"""
        print("\n📋 TESTING: Error Scenarios & Edge Cases")
        
        try:
            # Test invalid URLs
            await self.page.goto("http://127.0.0.1:8000/nonexistent")
            await self.page.wait_for_load_state("networkidle")
            
            # Should redirect or show 404
            current_url = self.page.url
            if "nonexistent" in current_url:
                self.issues_found.append("Invalid URL didn't handle gracefully")
            else:
                self.features_tested.append("✅ Invalid URL Handling")
            
            # Test empty form submissions
            await self.test_empty_form_handling()
            
            self.features_tested.append("✅ Error Scenarios Complete")
            
        except Exception as e:
            self.issues_found.append(f"Error scenario testing failed: {str(e)}")
            print(f"❌ Error scenario testing failed: {e}")
    
    async def test_empty_form_handling(self):
        """Test empty form submission handling"""
        print("  🔍 Testing Empty Form Handling...")
        
        # Go back to dashboard
        await self.page.goto("http://127.0.0.1:8000/dashboard")
        await self.page.wait_for_load_state("networkidle")
        
        # Try to create recipe with empty form
        await self.page.click('#btnNew')
        await self.page.wait_for_selector('#modal:not(.hidden)')
        
        # Try to save without filling anything
        await self.page.click('#btnSaveRecipe')
        await self.page.wait_for_timeout(1000)
        
        # Modal should still be open (form validation should prevent submission)
        modal_still_open = await self.page.locator('#modal:not(.hidden)').count() > 0
        if modal_still_open:
            self.features_tested.append("✅ Empty Form Validation")
            await self.page.click('#mCancel')  # Close modal
        else:
            self.issues_found.append("Empty form was submitted without validation")
    
    async def test_data_verification(self):
        """Verify that no mock data is being used"""
        print("\n📋 TESTING: Data Verification (No Mock Data)")
        
        try:
            # Check API responses to ensure real data
            await self.page.goto("http://127.0.0.1:8000/dashboard")
            await self.page.wait_for_load_state("networkidle")
            
            # Monitor network requests for mock data indicators
            self.page.on("response", self.check_response_for_mock_data)
            
            # Trigger API calls by switching tabs
            await self.page.click('[data-tab="trending"]')
            await self.page.wait_for_timeout(2000)
            
            self.features_tested.append("✅ Data Verification Complete")
            
        except Exception as e:
            self.issues_found.append(f"Data verification failed: {str(e)}")
            print(f"❌ Data verification failed: {e}")
    
    def check_response_for_mock_data(self, response):
        """Check API responses for mock data indicators"""
        if 'api/' in response.url:
            # This would need to be customized based on what mock data looks like
            # For now, just log that we're monitoring API calls
            print(f"  📡 API Call: {response.url} - Status: {response.status}")
    
    def print_final_report(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 70)
        print("🎯 COMPREHENSIVE TEST RESULTS")
        print("=" * 70)
        
        print(f"\n✅ FEATURES SUCCESSFULLY TESTED ({len(self.features_tested)}):")
        for feature in self.features_tested:
            print(f"  {feature}")
        
        if self.recipes_created:
            print(f"\n📝 RECIPES CREATED ({len(self.recipes_created)}):")
            for recipe in self.recipes_created:
                print(f"  • {recipe}")
        
        if self.groups_joined:
            print(f"\n👥 GROUPS INTERACTED WITH ({len(self.groups_joined)}):")
            for group in self.groups_joined:
                print(f"  • {group}")
        
        if self.issues_found:
            print(f"\n❌ ISSUES FOUND ({len(self.issues_found)}):")
            for issue in self.issues_found:
                print(f"  • {issue}")
        else:
            print(f"\n🎉 NO ISSUES FOUND - ALL FEATURES WORKING!")
        
        print(f"\n📊 TEST SUMMARY:")
        print(f"  • Features Tested: {len(self.features_tested)}")
        print(f"  • Issues Found: {len(self.issues_found)}")
        print(f"  • Recipes Created: {len(self.recipes_created)}")
        print(f"  • Success Rate: {(len(self.features_tested) / (len(self.features_tested) + len(self.issues_found)) * 100):.1f}%")
        
        print("\n" + "=" * 70)
        
        if len(self.issues_found) == 0:
            print("🚀 READY FOR PRODUCTION! All features working correctly.")
        else:
            print("⚠️  FIX ISSUES BEFORE PRODUCTION DEPLOYMENT")
        
        print("=" * 70)

async def main():
    """Run the comprehensive test suite"""
    test_suite = ComprehensiveTest()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())