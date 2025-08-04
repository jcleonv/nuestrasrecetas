#!/usr/bin/env python3
"""
Check all constraints in the database
"""

import psycopg2

DATABASE_URL = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check all constraints
    cursor.execute("""
        SELECT 
            conname as constraint_name,
            contype as constraint_type,
            conrelid::regclass as table_name,
            confrelid::regclass as referenced_table,
            pg_get_constraintdef(oid) as definition
        FROM pg_constraint 
        WHERE connamespace = 'public'::regnamespace
        ORDER BY conrelid::regclass::text, conname;
    """)
    
    constraints = cursor.fetchall()
    print("All constraints in public schema:")
    for constraint_name, constraint_type, table_name, referenced_table, definition in constraints:
        type_map = {
            'c': 'CHECK',
            'f': 'FOREIGN KEY', 
            'p': 'PRIMARY KEY',
            'u': 'UNIQUE',
            'x': 'EXCLUDE'
        }
        constraint_type_name = type_map.get(constraint_type, constraint_type)
        print(f"  {table_name}.{constraint_name} ({constraint_type_name})")
        if referenced_table and str(referenced_table) != '-':
            print(f"    -> {referenced_table}")
        print(f"    {definition}")
        print()
    
    # Check if there are any auth-related tables
    cursor.execute("""
        SELECT schemaname, tablename 
        FROM pg_tables 
        WHERE schemaname LIKE '%auth%' OR tablename LIKE '%user%' OR tablename LIKE '%auth%'
        ORDER BY schemaname, tablename;
    """)
    
    auth_tables = cursor.fetchall()
    if auth_tables:
        print("Auth-related tables:")
        for schema, table in auth_tables:
            print(f"  {schema}.{table}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()