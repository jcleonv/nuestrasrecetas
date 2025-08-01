#!/usr/bin/env python3
"""
Supabase Setup Helper
This script helps you get the correct connection string for Supabase.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def get_supabase_connection_string():
    """Guide user to get Supabase connection string"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    if not supabase_url:
        print("❌ SUPABASE_URL not found in .env file")
        return None
    
    # Extract project reference
    project_ref = supabase_url.replace('https://', '').replace('http://', '').split('.')[0]
    
    print("🔗 Setting up Supabase connection...")
    print(f"📍 Project Reference: {project_ref}")
    print()
    print("To get your Supabase connection string:")
    print("1. Go to https://supabase.com/dashboard")
    print("2. Select your project")
    print("3. Go to Settings → Database")
    print("4. Scroll down to 'Connection string'")
    print("5. Select 'URI' tab")
    print("6. Copy the connection string")
    print()
    print("The connection string should look like:")
    print(f"postgresql://postgres.{project_ref}:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres")
    print()
    print("Replace [YOUR-PASSWORD] with your actual database password.")
    print()
    
    connection_string = input("Paste your Supabase connection string here (or press Enter to skip): ").strip()
    
    if connection_string:
        # Update .env file
        try:
            with open('.env', 'r') as f:
                lines = f.readlines()
            
            # Update DATABASE_URL
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('DATABASE_URL='):
                    lines[i] = f'DATABASE_URL={connection_string}\n'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'DATABASE_URL={connection_string}\n')
            
            with open('.env', 'w') as f:
                f.writelines(lines)
            
            print("✅ Updated .env file with Supabase connection string")
            return connection_string
            
        except Exception as e:
            print(f"❌ Error updating .env file: {e}")
            print(f"Please manually update DATABASE_URL in .env to: {connection_string}")
            return connection_string
    else:
        print("⏭️  Skipping Supabase setup. Using SQLite instead.")
        return None

def test_connection(connection_string):
    """Test the database connection"""
    try:
        from sqlalchemy import create_engine
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Database connection successful!")
                return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your connection string and try again.")
        return False
    return False

def main():
    print("🍽️  Family Recipe Planner - Supabase Setup")
    print("=" * 50)
    
    connection_string = get_supabase_connection_string()
    
    if connection_string:
        print("\n🧪 Testing connection...")
        if test_connection(connection_string):
            print("\n🎉 Supabase is ready!")
            print("You can now run: ./deploy.sh")
        else:
            print("\n💡 Connection failed. You can still use SQLite by running:")
            print("./deploy.sh")
    else:
        print("\n💡 Using SQLite. Run: ./deploy.sh")

if __name__ == "__main__":
    main()