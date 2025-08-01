#!/usr/bin/env python3
"""Test Supabase database connection"""

import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    database_url = os.getenv('DATABASE_URL')
    print(f"Testing connection to: {database_url[:50]}...")
    
    try:
        # Parse the URL
        parsed = urlparse(database_url)
        
        print(f"Host: {parsed.hostname}")
        print(f"Port: {parsed.port}")
        print(f"Database: {parsed.path[1:]}")  # Remove leading slash
        print(f"Username: {parsed.username}")
        print(f"Password: {'*' * len(parsed.password) if parsed.password else 'None'}")
        
        # Test connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connection successful!")
        print(f"PostgreSQL version: {version[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        
        if "Wrong password" in str(e):
            print("\n💡 Password troubleshooting:")
            print("1. Go to Supabase Dashboard → Settings → Database")
            print("2. Click 'Reset database password'")
            print("3. Copy the NEW password")
            print("4. Update your .env file with the new password")
            print("5. Make sure there are no special characters causing issues")

if __name__ == "__main__":
    test_connection()