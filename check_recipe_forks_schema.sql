-- Quick check of existing recipe_forks table structure
-- Run this in Supabase SQL Editor to see what columns exist

SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'recipe_forks' 
    AND table_schema = 'public'
ORDER BY ordinal_position;

-- Also check if table exists at all
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'recipe_forks' 
    AND table_schema = 'public'
) as table_exists;