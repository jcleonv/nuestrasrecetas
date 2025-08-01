#!/usr/bin/env python3
"""
Check existing users and create test user if needed
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def main():
    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        return
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {e}")
        return
    
    # Check existing profiles
    try:
        response = supabase.table('profiles').select('*').execute()
        profiles = response.data or []
        
        print(f"📋 Found {len(profiles)} profiles:")
        for profile in profiles:
            print(f"  - ID: {profile['id']}")
            print(f"    Username: {profile.get('username', 'N/A')}")
            print(f"    Name: {profile.get('name', 'N/A')}")
            print(f"    Email: {profile.get('email', 'N/A')}")
            print()
        
        if profiles:
            # Use the first profile as test user
            test_user = profiles[0]
            print(f"🎯 Using test user: {test_user['username']} ({test_user['id']})")
            
            # Update the test-login endpoint to use this user
            print("\n📝 Update the test-login endpoint in app.py to use this user ID:")
            print(f"user_id = \"{test_user['id']}\"")
        else:
            print("❌ No profiles found")
            
    except Exception as e:
        print(f"❌ Error checking profiles: {e}")

if __name__ == "__main__":
    main() 