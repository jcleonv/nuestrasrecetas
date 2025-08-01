-- Migration: Bulletproof Recipe Forks and User Posts
-- This will work regardless of current table state

-- ================================================
-- SAFE RECIPE_FORKS TABLE SETUP
-- ================================================

-- Drop and recreate recipe_forks table to ensure clean state
DROP TABLE IF EXISTS public.recipe_forks CASCADE;

-- Create recipe_forks table with correct structure
CREATE TABLE public.recipe_forks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    original_recipe_id INTEGER NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    forked_recipe_id INTEGER NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    forked_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure a recipe can't be forked multiple times by the same user from the same original
    UNIQUE(original_recipe_id, forked_by)
);

-- Create indexes for performance
CREATE INDEX idx_recipe_forks_original ON public.recipe_forks(original_recipe_id);
CREATE INDEX idx_recipe_forks_forked ON public.recipe_forks(forked_recipe_id);
CREATE INDEX idx_recipe_forks_user ON public.recipe_forks(forked_by);
CREATE INDEX idx_recipe_forks_created_at ON public.recipe_forks(created_at);

-- ================================================
-- USER_POSTS TABLE SETUP
-- ================================================

-- Create user_posts table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.user_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    post_type VARCHAR(50) DEFAULT 'general' CHECK (post_type IN ('general', 'recipe_share', 'recipe_fork', 'meal_plan', 'achievement')),
    recipe_id INTEGER REFERENCES public.recipes(id) ON DELETE SET NULL,
    group_id UUID REFERENCES public.groups(id) ON DELETE CASCADE,
    metadata JSONB DEFAULT '{}',
    is_public BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for user_posts (with safety checks)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_posts_user') THEN
        CREATE INDEX idx_user_posts_user ON public.user_posts(user_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_posts_type') THEN
        CREATE INDEX idx_user_posts_type ON public.user_posts(post_type);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_posts_recipe') THEN
        CREATE INDEX idx_user_posts_recipe ON public.user_posts(recipe_id) WHERE recipe_id IS NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_posts_created_at') THEN
        CREATE INDEX idx_user_posts_created_at ON public.user_posts(created_at);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_posts_public_feed') THEN
        CREATE INDEX idx_user_posts_public_feed ON public.user_posts(created_at, is_public) WHERE is_public = true;
    END IF;
END
$$;

-- ================================================
-- TRIGGERS AND FUNCTIONS
-- ================================================

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_posts_updated_at') THEN
        CREATE TRIGGER update_user_posts_updated_at 
        BEFORE UPDATE ON public.user_posts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- ================================================
-- ROW LEVEL SECURITY POLICIES
-- ================================================

-- Enable RLS on both tables
ALTER TABLE public.recipe_forks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_posts ENABLE ROW LEVEL SECURITY;

-- Drop any existing policies first
DROP POLICY IF EXISTS "Public recipe forks are viewable by everyone" ON public.recipe_forks;
DROP POLICY IF EXISTS "Users can create their own recipe forks" ON public.recipe_forks;
DROP POLICY IF EXISTS "Users can delete their own recipe forks" ON public.recipe_forks;

DROP POLICY IF EXISTS "Users can view public posts and their own posts" ON public.user_posts;
DROP POLICY IF EXISTS "Users can create their own posts" ON public.user_posts;
DROP POLICY IF EXISTS "Users can update their own posts" ON public.user_posts;
DROP POLICY IF EXISTS "Users can delete their own posts" ON public.user_posts;

-- Create fresh policies for recipe_forks
CREATE POLICY "Public recipe forks are viewable by everyone"
ON public.recipe_forks FOR SELECT
USING (true);

CREATE POLICY "Users can create their own recipe forks"
ON public.recipe_forks FOR INSERT
WITH CHECK (auth.uid() = forked_by);

CREATE POLICY "Users can delete their own recipe forks"
ON public.recipe_forks FOR DELETE
USING (auth.uid() = forked_by);

-- Create fresh policies for user_posts
CREATE POLICY "Users can view public posts and their own posts"
ON public.user_posts FOR SELECT
USING (
    is_public = true 
    OR auth.uid() = user_id
    OR (
        group_id IS NOT NULL 
        AND EXISTS (
            SELECT 1 FROM public.group_members gm 
            WHERE gm.group_id = user_posts.group_id 
            AND gm.user_id = auth.uid()
        )
    )
);

CREATE POLICY "Users can create their own posts"
ON public.user_posts FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own posts"
ON public.user_posts FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own posts"
ON public.user_posts FOR DELETE
USING (auth.uid() = user_id);

-- ================================================
-- HELPER FUNCTIONS
-- ================================================

-- Create a function to get fork count for a recipe
CREATE OR REPLACE FUNCTION get_recipe_fork_count(recipe_uuid INTEGER)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)::INTEGER 
        FROM public.recipe_forks 
        WHERE original_recipe_id = recipe_uuid
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a function to check if a recipe is forked by a user
CREATE OR REPLACE FUNCTION is_recipe_forked_by_user(recipe_uuid INTEGER, user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM public.recipe_forks 
        WHERE original_recipe_id = recipe_uuid 
        AND forked_by = user_uuid
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions
GRANT ALL ON public.recipe_forks TO authenticated;
GRANT ALL ON public.user_posts TO authenticated;
GRANT EXECUTE ON FUNCTION get_recipe_fork_count(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION is_recipe_forked_by_user(INTEGER, UUID) TO authenticated;

-- ================================================
-- VERIFICATION
-- ================================================

-- Verify tables were created correctly
SELECT 
    'recipe_forks' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns 
WHERE table_name = 'recipe_forks' AND table_schema = 'public'

UNION ALL

SELECT 
    'user_posts' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns 
WHERE table_name = 'user_posts' AND table_schema = 'public';

-- Show success message
SELECT 'Migration 004 completed successfully! Tables created with proper structure.' as status;