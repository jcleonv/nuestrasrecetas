#!/usr/bin/env python3
"""
Verification script to check if database mode is properly enabled
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_configuration():
    """Test the configuration changes"""
    print("🧪 Testing database mode configuration...")
    
    try:
        # Import the functions from app.py
        from app import is_pure_dev_mode, is_development
        
        # Test is_pure_dev_mode function
        pure_dev_result = is_pure_dev_mode()
        print(f"📊 is_pure_dev_mode() returns: {pure_dev_result}")
        
        if pure_dev_result == False:
            print("✅ SUCCESS: Pure dev mode is disabled - database operations will be used")
        else:
            print("❌ FAILURE: Pure dev mode is still enabled - will use mock data")
            return False
            
        # Test is_development function
        dev_result = is_development()
        print(f"📊 is_development() returns: {dev_result}")
        
        # Test datetime import
        from app import datetime, timezone
        print("✅ SUCCESS: datetime and timezone imported correctly")
        
        # Test config
        from app import config
        print(f"📊 config.use_supabase: {config.use_supabase}")
        
        if config.use_supabase:
            print("✅ SUCCESS: Supabase is enabled in configuration")
        else:
            print("⚠️  WARNING: Supabase is not enabled - check SUPABASE_URL and SUPABASE_KEY environment variables")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_configuration()
    if success:
        print("\n🎉 All tests passed! Database mode is properly configured.")
    else:
        print("\n💥 Some tests failed. Please check the configuration.")
        sys.exit(1)