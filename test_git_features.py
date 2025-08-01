#!/usr/bin/env python3
"""
Test script for Git-like recipe features
This script can be used to verify the implementation works correctly
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_git_features():
    """Test the Git-like recipe features"""
    
    print("🧪 Testing Git for Recipes Implementation")
    print("=" * 50)
    
    # Test endpoints (assuming you have some recipes in the database)
    test_recipe_id = 1  # Adjust this to an actual recipe ID
    
    endpoints_to_test = [
        f"/api/recipes/{test_recipe_id}/stats",
        f"/api/recipes/{test_recipe_id}/history",
        f"/api/recipes/{test_recipe_id}/forks",
        f"/api/recipes/{test_recipe_id}/branches",
        f"/api/recipes/{test_recipe_id}/contributors",
        f"/api/recipes/{test_recipe_id}/network",
    ]
    
    for endpoint in endpoints_to_test:
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"\n📍 Testing: {endpoint}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success - Got response with {len(str(data))} characters")
                
                # Print sample of response structure
                if isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"   List with {len(data)} items")
                    
            elif response.status_code == 401:
                print(f"🔒 Authentication required - endpoint protected correctly")
            elif response.status_code == 404:
                print(f"❓ Not found - recipe {test_recipe_id} might not exist")
            else:
                print(f"⚠️  Status {response.status_code}: {response.text[:100]}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection failed - is the server running on {BASE_URL}?")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Testing complete!")
    print("\nNext steps:")
    print("1. Apply the migration: supabase/migrations/005_git_for_recipes.sql")
    print("2. Start the Flask app: python app.py")
    print("3. Test the new Git-like features with a real recipe")
    print("4. Try forking a recipe and viewing its history")

if __name__ == "__main__":
    test_git_features()