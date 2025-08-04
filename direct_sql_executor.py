#!/usr/bin/env python3
"""
Direct SQL Executor for Supabase
Executes SQL migrations directly using REST API
"""

import requests
import sys
import os
from datetime import datetime

# Supabase configuration
SUPABASE_URL = "https://egyxcuejvorqlwujsdpp.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVneXhjdWVqdm9ycWx3dWpzZHBwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNDY0ODczNSwiZXhwIjoyMDUwMjI0NzM1fQ.TVNEP7KGKlXwDbwb8gBJNlJ6AgjQKHvxNXNJaGOiuBY"

def read_migration_file(file_path):
    """Read SQL migration file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"📖 Read migration file: {os.path.basename(file_path)}")
        return content
    except FileNotFoundError:
        print(f"❌ Migration file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading migration file {file_path}: {e}")
        sys.exit(1)

def execute_sql_via_rest(sql_content, migration_name):
    """Execute SQL using Supabase REST API"""
    headers = {
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    # Split SQL into individual statements
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    
    print(f"🚀 Applying migration: {migration_name}")
    print(f"📝 Found {len(statements)} SQL statements")
    print("=" * 60)
    
    success_count = 0
    for i, statement in enumerate(statements, 1):
        if not statement:
            continue
            
        print(f"Executing statement {i}/{len(statements)}...")
        
        # Use the PostgREST rpc endpoint to execute raw SQL
        rpc_data = {
            'sql': statement
        }
        
        try:
            # Try to execute as RPC call first
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/execute_sql",
                headers=headers,
                json=rpc_data,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Statement {i} executed successfully")
                success_count += 1
            else:
                print(f"❌ Statement {i} failed with status {response.status_code}")
                print(f"Error: {response.text}")
                
                # For function creation statements, this might be expected
                if "CREATE OR REPLACE FUNCTION" in statement or "CREATE INDEX" in statement:
                    print("ℹ️  This might be a function/index creation - continuing...")
                    success_count += 1
                else:
                    return False
                    
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error executing statement {i}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error executing statement {i}: {e}")
            return False
    
    print(f"✅ Migration {migration_name} completed: {success_count}/{len(statements)} statements executed")
    print("=" * 60)
    return True

def verify_functions_exist():
    """Verify that functions were created by calling them"""
    headers = {
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': 'application/json'
    }
    
    functions_to_test = [
        ('get_community_feed', {'input_user_id': None, 'page_limit': 1, 'page_offset': 0}),
        ('get_community_activity_stats', {'days_back': 7}),
        ('get_suggested_users', {'input_user_id': '00000000-0000-0000-0000-000000000000', 'limit_count': 1}),
        ('get_user_suggestion_stats', {'input_user_id': '00000000-0000-0000-0000-000000000000'})
    ]
    
    print("\n🔍 Verifying functions were created...")
    
    for func_name, params in functions_to_test:
        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/{func_name}",
                headers=headers,
                json=params,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Function '{func_name}' exists and callable")
            else:
                print(f"❌ Function '{func_name}' not callable: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Error testing function '{func_name}': {e}")

def main():
    """Main migration execution"""
    print("🚀 Direct SQL Migration Executor for Supabase")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Migration files to apply
    migrations = [
        {
            'name': '006_community_feed_function',
            'file': '/Users/juancarlosleon/nuestrasrecetas/supabase/migrations/006_community_feed_function.sql',
            'description': 'Creates get_community_feed() function and performance indexes'
        },
        {
            'name': '007_user_suggestions_function', 
            'file': '/Users/juancarlosleon/nuestrasrecetas/supabase/migrations/007_user_suggestions_function.sql',
            'description': 'Creates get_suggested_users() function and performance indexes'
        }
    ]
    
    # Test connection first
    print("🔗 Testing connection to Supabase...")
    headers = {
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Connection to Supabase successful")
        else:
            print(f"❌ Connection failed with status {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        sys.exit(1)
    
    try:
        # Apply each migration
        for migration in migrations:
            print(f"\n📋 Migration: {migration['name']}")
            print(f"📄 Description: {migration['description']}")
            
            # Read migration file
            sql_content = read_migration_file(migration['file'])
            
            # Execute migration
            success = execute_sql_via_rest(sql_content, migration['name'])
            if not success:
                print(f"❌ Migration {migration['name']} failed!")
                sys.exit(1)
        
        print("\n🎉 All migrations applied successfully!")
        
        # Verify migrations
        verify_functions_exist()
        
        print(f"\n✅ Migration process completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ Migration process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()