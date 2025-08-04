#!/usr/bin/env python3
"""
Test profile API directly to debug the 500 error
"""

import requests

def test_profile_api():
    # First login to get session
    session = requests.Session()
    
    # Login
    login_data = {
        'email': 'j_carlos.leon@hotmail.com',
        'password': 'juancarlos95'
    }
    
    login_response = session.post('http://127.0.0.1:8000/api/auth/login', json=login_data)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        print("Login successful")
        
        # Test profile API
        profile_response = session.get('http://127.0.0.1:8000/api/profile/jctest')
        print(f"Profile API status: {profile_response.status_code}")
        
        if profile_response.status_code == 200:
            print("Profile API successful:")
            print(profile_response.json())
        else:
            print(f"Profile API error: {profile_response.text}")
            
        # Also test current user info
        me_response = session.get('http://127.0.0.1:8000/api/auth/me')
        print(f"Current user API status: {me_response.status_code}")
        if me_response.status_code == 200:
            user_data = me_response.json()
            print(f"Current user: {user_data}")
            
            # Extract the actual username from current user
            if 'user' in user_data:
                current_user = user_data['user']
                actual_username = current_user.get('username') or current_user.get('email', '').split('@')[0]
                print(f"Actual username should be: {actual_username}")
                
                # Test with the correct username
                correct_profile_response = session.get(f'http://127.0.0.1:8000/api/profile/{actual_username}')
                print(f"Correct profile API status: {correct_profile_response.status_code}")
                if correct_profile_response.status_code == 200:
                    print("Correct profile API successful!")
                else:
                    print(f"Correct profile API error: {correct_profile_response.text}")
    else:
        print(f"Login failed: {login_response.text}")

if __name__ == "__main__":
    test_profile_api()