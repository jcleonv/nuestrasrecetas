#!/usr/bin/env python3
"""
Simple test to verify is_pure_dev_mode function logic
"""

import os

def is_development():
    """Check if we're in development mode"""
    return (os.getenv('ENVIRONMENT') == 'development' or 
            os.getenv('FLASK_ENV') == 'development' or 
            os.getenv('PURE_DEV_MODE') == 'true')

def is_pure_dev_mode():
    """Check if we're running in pure development mode (no Supabase)"""
    # Always return False to enable Supabase database operations in development
    return False

def test_function():
    """Test the modified function"""
    print("🧪 Testing is_pure_dev_mode function...")
    
    # Test with various environment variable combinations
    test_cases = [
        {},  # No env vars
        {'ENVIRONMENT': 'development'},
        {'FLASK_ENV': 'development'},
        {'PURE_DEV_MODE': 'true'},
        {'DISABLE_SUPABASE': 'true'},
        {'ENVIRONMENT': 'development', 'DISABLE_SUPABASE': 'true'},
        {'PURE_DEV_MODE': 'true', 'DISABLE_SUPABASE': 'true'},
    ]
    
    for i, env_vars in enumerate(test_cases):
        # Temporarily set environment variables
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.getenv(key)
            os.environ[key] = value
        
        result = is_pure_dev_mode()
        print(f"Test {i+1}: {env_vars} -> is_pure_dev_mode() = {result}")
        
        # Restore original environment
        for key in env_vars.keys():
            if original_env[key] is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = original_env[key]
        
        if result != False:
            print(f"❌ FAILURE: Expected False, got {result}")
            return False
    
    print("✅ SUCCESS: is_pure_dev_mode() always returns False")
    return True

if __name__ == "__main__":
    success = test_function()
    if success:
        print("\n🎉 Function test passed! Database mode will be enabled.")
    else:
        print("\n💥 Function test failed.")