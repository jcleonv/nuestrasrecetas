#!/usr/bin/env python3
"""
Test Dev Mode Endpoints - Verify all fixes work correctly
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Test an endpoint and return result"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data)
        
        success = response.status_code == expected_status
        return {
            "endpoint": f"{method} {endpoint}",
            "status_code": response.status_code,
            "expected": expected_status,
            "success": success,
            "response": response.text[:200] if not success else "OK"
        }
    except Exception as e:
        return {
            "endpoint": f"{method} {endpoint}",
            "success": False,
            "error": str(e)
        }

def main():
    print("🧪 Testing Dev Mode Endpoints")
    print("=" * 50)
    
    # Test the previously failing endpoints
    tests = [
        ("GET", "/api/plan"),
        ("POST", "/api/recipe", {
            "title": "Test Recipe",
            "description": "Test description",
            "ingredients": [{"name": "test", "amount": "1", "unit": "cup"}],
            "instructions": ["Test step"]
        }),
        ("POST", "/api/groups/group-1/join"),
        ("GET", "/api/groups/group-1"),
        ("POST", "/api/recipes/1/fork"),
        ("POST", "/api/recipes/1/star"),
    ]
    
    results = []
    for test in tests:
        if len(test) == 3:
            result = test_endpoint(test[0], test[1], test[2])
        else:
            result = test_endpoint(test[0], test[1])
        results.append(result)
    
    # Display results
    passed = 0
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['endpoint']} - {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"    Error: {result.get('error', result.get('response', 'Unknown'))}")
        else:
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All dev mode endpoints are working!")
        sys.exit(0)
    else:
        print("❌ Some endpoints are still failing")
        sys.exit(1)

if __name__ == "__main__":
    main()