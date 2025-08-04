-- Comprehensive diagnostic for existing tables
-- Run this in Supabase SQL Editor to get complete picture

-- 1. Check recipe_forks table structure with more detail
SELECT 
    'recipe_forks' as table_name,
    column_name, 
    data_type, 
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_schema = 'public' 
    AND table_name = 'recipe_forks'
ORDER BY ordinal_position;

-- 2. Try direct table description (alternative method)
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'recipe_forks';

-- 3. Check what other recipe-related tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name LIKE '%recipe%'
ORDER BY table_name;

-- 4. Check if we can see the table structure directly
\d recipe_forks;

-- 5. Try to see sample data (if any exists)
SELECT COUNT(*) as row_count FROM public.recipe_forks;

-- 6. Check table owner and permissions
SELECT 
    schemaname,
    tablename,
    tableowner,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables 
WHERE tablename = 'recipe_forks';