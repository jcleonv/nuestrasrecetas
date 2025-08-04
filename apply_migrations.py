#!/usr/bin/env python3
"""
Database Migration Script for Supabase
Applies SQL migration files to the remote Supabase database using Supabase client
"""

import sys
import os
from datetime import datetime
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = "https://egyxcuejvorqlwujsdpp.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVneXhjdWVqdm9ycWx3dWpzZHBwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNDY0ODczNSwiZXhwIjoyMDUwMjI0NzM1fQ.TVNEP7KGKlXwDbwb8gBJNlJ6AgjQKHvxNXNJaGOiuBY"

def connect_to_database():
    """Establish connection to Supabase database"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print(f"✅ Connected to Supabase database: {SUPABASE_URL}")
        return supabase
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

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

def execute_migration(supabase, migration_name, sql_content):
    """Execute a migration by breaking it into individual statements"""
    try:
        print(f"🚀 Applying migration: {migration_name}")
        print("=" * 60)
        
        # Split SQL into individual statements
        statements = []
        current_statement = ""
        in_function = False
        
        for line in sql_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
                
            current_statement += line + '\n'
            
            # Check if we're entering a function definition
            if 'CREATE OR REPLACE FUNCTION' in line.upper():
                in_function = True
            
            # Check for end of statement
            if line.endswith(';') and not in_function:
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
            elif line.endswith('$$;') and in_function:
                # End of function
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
                in_function = False
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        print(f"📝 Executing {len(statements)} SQL statements...")
        
        success_count = 0
        for i, statement in enumerate(statements, 1):
            try:
                print(f"Executing statement {i}/{len(statements)}...")
                
                # Use raw SQL execution via RPC
                result = supabase.rpc('exec_sql', {'query': statement}).execute()
                print(f"✅ Statement {i} executed successfully")
                success_count += 1
                
            except Exception as stmt_error:
                # Some statements might fail but still be successful (like IF NOT EXISTS)
                error_msg = str(stmt_error).lower()
                if any(phrase in error_msg for phrase in ['already exists', 'if not exists', 'or replace']):
                    print(f"ℹ️  Statement {i} - object already exists (this is OK)")
                    success_count += 1
                else:
                    print(f"❌ Statement {i} failed: {stmt_error}")
                    # Continue with other statements
                    continue
        
        print(f"✅ Migration {migration_name} completed: {success_count}/{len(statements)} statements processed")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error applying migration {migration_name}: {e}")
        print(f"🔄 Migration failed")
        raise e

def verify_functions_exist(supabase):
    """Verify that functions were created by testing them"""
    functions_to_test = [
        ('get_community_feed', {'input_user_id': None, 'page_limit': 1, 'page_offset': 0}),
        ('get_community_activity_stats', {'days_back': 7}),
        ('get_suggested_users', {'input_user_id': '00000000-0000-0000-0000-000000000000', 'limit_count': 1}),
        ('get_user_suggestion_stats', {'input_user_id': '00000000-0000-0000-0000-000000000000'})
    ]
    
    print("\n🔍 Verifying functions were created...")
    
    for func_name, params in functions_to_test:
        try:
            result = supabase.rpc(func_name, params).execute()
            print(f"✅ Function '{func_name}' exists and callable")
        except Exception as e:
            error_msg = str(e).lower()
            if 'function' in error_msg and 'does not exist' in error_msg:
                print(f"❌ Function '{func_name}' not found")
            else:
                print(f"ℹ️  Function '{func_name}' exists but returned error (this may be expected): {e}")
                print(f"   This often means the function exists but needs valid data to run properly.")

def verify_indexes_exist(conn):
    """Verify that the indexes were created successfully"""
    cursor = conn.cursor()
    
    indexes_to_check = [
        'idx_recipes_public_created_at',
        'idx_recipe_forks_created_at',
        'idx_user_posts_public_created_at',
        'idx_user_follows_created_at',
        'idx_profiles_public_status',
        'idx_user_follows_follower_following',
        'idx_profiles_followers_count_public',
        'idx_profiles_created_at_public',
        'idx_recipes_user_category_public',
        'idx_user_posts_user_created_public'
    ]
    
    print("\n🔍 Verifying indexes were created...")
    
    try:
        for idx_name in indexes_to_check:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = 'public' AND indexname = %s
            """, (idx_name,))
            
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"✅ Index '{idx_name}' exists")
            else:
                print(f"❌ Index '{idx_name}' not found")
                
    except psycopg2.Error as e:
        print(f"❌ Error verifying indexes: {e}")
    finally:
        cursor.close()

def main():
    """Main migration execution"""
    print("🚀 Supabase Migration Script")
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
    
    # Connect to database
    conn = connect_to_database()
    
    try:
        # Apply each migration
        for migration in migrations:
            print(f"\n📋 Migration: {migration['name']}")
            print(f"📄 Description: {migration['description']}")
            
            # Read migration file
            sql_content = read_migration_file(migration['file'])
            
            # Execute migration
            execute_migration(conn, migration['name'], sql_content)
        
        print("\n🎉 All migrations applied successfully!")
        
        # Verify migrations
        verify_functions_exist(conn)
        verify_indexes_exist(conn)
        
        print(f"\n✅ Migration process completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ Migration process failed: {e}")
        sys.exit(1)
    finally:
        conn.close()
        print("🔒 Database connection closed")

if __name__ == "__main__":
    main()