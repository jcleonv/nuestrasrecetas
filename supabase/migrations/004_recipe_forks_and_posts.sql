-- Migration: Add recipe forks and user posts tables
-- Created: 2025-01-01
-- Description: Add tables for recipe forking functionality and user posts/activity feed

-- Create recipe_forks table for tracking recipe forking relationships
CREATE TABLE public.recipe_forks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    original_recipe_id UUID NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    forked_recipe_id UUID NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
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

-- Create user_posts table for activity feed and community posts
CREATE TABLE public.user_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    post_type VARCHAR(50) DEFAULT 'general' CHECK (post_type IN ('general', 'recipe_share', 'recipe_fork', 'meal_plan', 'achievement')),
    recipe_id UUID REFERENCES public.recipes(id) ON DELETE SET NULL,
    group_id UUID REFERENCES public.groups(id) ON DELETE CASCADE,
    metadata JSONB DEFAULT '{}',
    is_public BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for user_posts
CREATE INDEX idx_user_posts_user ON public.user_posts(user_id);
CREATE INDEX idx_user_posts_type ON public.user_posts(post_type);
CREATE INDEX idx_user_posts_recipe ON public.user_posts(recipe_id) WHERE recipe_id IS NOT NULL;
CREATE INDEX idx_user_posts_group ON public.user_posts(group_id) WHERE group_id IS NOT NULL;
CREATE INDEX idx_user_posts_created_at ON public.user_posts(created_at);
CREATE INDEX idx_user_posts_public_feed ON public.user_posts(created_at, is_public) WHERE is_public = true;

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_posts_updated_at BEFORE UPDATE ON public.user_posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security Policies

-- Recipe forks policies
ALTER TABLE public.recipe_forks ENABLE ROW LEVEL SECURITY;

-- Users can view all public recipe forks
CREATE POLICY "Public recipe forks are viewable by everyone"
ON public.recipe_forks FOR SELECT
USING (true);

-- Users can only create forks for themselves
CREATE POLICY "Users can create their own recipe forks"
ON public.recipe_forks FOR INSERT
WITH CHECK (auth.uid() = forked_by);

-- Users can delete their own forks
CREATE POLICY "Users can delete their own recipe forks"
ON public.recipe_forks FOR DELETE
USING (auth.uid() = forked_by);

-- User posts policies
ALTER TABLE public.user_posts ENABLE ROW LEVEL SECURITY;

-- Users can view public posts and their own posts
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

-- Users can create their own posts
CREATE POLICY "Users can create their own posts"
ON public.user_posts FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own posts
CREATE POLICY "Users can update their own posts"
ON public.user_posts FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can delete their own posts
CREATE POLICY "Users can delete their own posts"
ON public.user_posts FOR DELETE
USING (auth.uid() = user_id);

-- Add fork count to recipes (computed field)
-- This will be calculated dynamically in the application

-- Create a function to get fork count for a recipe
CREATE OR REPLACE FUNCTION get_recipe_fork_count(recipe_uuid UUID)
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
CREATE OR REPLACE FUNCTION is_recipe_forked_by_user(recipe_uuid UUID, user_uuid UUID)
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
GRANT EXECUTE ON FUNCTION get_recipe_fork_count(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION is_recipe_forked_by_user(UUID, UUID) TO authenticated;

-- Add some sample data for testing (optional)
-- This would be added by the application, not in migration