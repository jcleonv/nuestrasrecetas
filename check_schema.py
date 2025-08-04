#!/usr/bin/env python3
"""
Check database schema for the profiles table
"""

import psycopg2

DATABASE_URL = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check profiles table schema
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'profiles'
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    print("Profiles table schema:")
    for col_name, data_type, nullable, default in columns:
        print(f"  {col_name}: {data_type} {'NULL' if nullable == 'YES' else 'NOT NULL'} {f'DEFAULT {default}' if default else ''}")
    
    # Check recipes table schema
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'recipes'
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    print("\nRecipes table schema:")
    for col_name, data_type, nullable, default in columns:
        print(f"  {col_name}: {data_type} {'NULL' if nullable == 'YES' else 'NOT NULL'} {f'DEFAULT {default}' if default else ''}")
    
    # Check foreign key constraints on profiles
    cursor.execute("""
        SELECT
            tc.constraint_name,
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'profiles'
            AND tc.table_schema = 'public';
    """)
    
    fks = cursor.fetchall()
    print("\nProfiles foreign keys:")
    for constraint_name, table_name, column_name, foreign_table_name, foreign_column_name in fks:
        print(f"  {constraint_name}: {table_name}.{column_name} -> {foreign_table_name}.{foreign_column_name}")
    
    # Check if users table exists and its schema
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'users'
        ORDER BY ordinal_position;
    """)
    
    user_columns = cursor.fetchall()
    if user_columns:
        print("\nUsers table schema:")
        for col_name, data_type, nullable, default in user_columns:
            print(f"  {col_name}: {data_type} {'NULL' if nullable == 'YES' else 'NOT NULL'} {f'DEFAULT {default}' if default else ''}")
    else:
        print("\nUsers table does not exist")
    
    # Check all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    
    tables = cursor.fetchall()
    print(f"\nAll tables: {[t[0] for t in tables]}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()