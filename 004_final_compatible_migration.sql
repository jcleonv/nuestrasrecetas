-- Migration: Final Compatible Version
-- Works with your existing complete database schema

-- ================================================
-- ADD MISSING INDEXES FOR PERFORMANCE
-- ================================================

-- Recipe_forks indexes (if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_recipe_forks_original') THEN
        CREATE INDEX idx_recipe_forks_original ON public.recipe_forks(original_recipe_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_recipe_forks_forked') THEN
        CREATE INDEX idx_recipe_forks_forked ON public.recipe_forks(forked_recipe_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_recipe_forks_user') THEN
        CREATE INDEX idx_recipe_forks_user ON public.recipe_forks(forked_by_user_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_recipe_forks_created_at') THEN
        CREATE INDEX idx_recipe_forks_created_at ON public.recipe_forks(created_at);
    END IF;
END
$$;

-- User_posts indexes (if they don't exist)
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

-- Recipe activity indexes for performance
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_recipe_activity_recipe') THEN
        CREATE INDEX idx_recipe_activity_recipe ON public.recipe_activity(recipe_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_recipe_activity_user') THEN
        CREATE INDEX idx_recipe_activity_user ON public.recipe_activity(user_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_recipe_activity_created_at') THEN
        CREATE INDEX idx_recipe_activity_created_at ON public.recipe_activity(created_at);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_recipe_activity_type') THEN
        CREATE INDEX idx_recipe_activity_type ON public.recipe_activity(activity_type);
    END IF;
END
$$;

-- ================================================
-- ADD MISSING COLUMNS TO EXISTING TABLES
-- ================================================

-- Add group_id to user_posts if it doesn't exist (since your existing table doesn't have it)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'user_posts' AND column_name = 'group_id') THEN
        ALTER TABLE public.user_posts ADD COLUMN group_id UUID REFERENCES public.groups(id) ON DELETE CASCADE;
        
        -- Add index for the new column
        CREATE INDEX idx_user_posts_group ON public.user_posts(group_id) WHERE group_id IS NOT NULL;
    END IF;
END
$$;

-- Add metadata column to user_posts if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'user_posts' AND column_name = 'metadata') THEN
        ALTER TABLE public.user_posts ADD COLUMN metadata JSONB DEFAULT '{}';
    END IF;
END
$$;

-- Update user_posts post_type check to include new types
DO $$
BEGIN
    -- Drop existing constraint
    ALTER TABLE public.user_posts DROP CONSTRAINT IF EXISTS user_posts_post_type_check;
    
    -- Add new constraint with extended types
    ALTER TABLE public.user_posts ADD CONSTRAINT user_posts_post_type_check 
    CHECK (post_type = ANY (ARRAY['general'::text, 'update'::text, 'announcement'::text, 'recipe_share'::text, 'recipe_fork'::text, 'meal_plan'::text, 'achievement'::text]));
END
$$;

-- ================================================
-- ROW LEVEL SECURITY POLICIES
-- ================================================

-- Enable RLS on tables that need it
ALTER TABLE public.recipe_forks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recipe_activity ENABLE ROW LEVEL SECURITY;

-- Drop any existing policies first
DROP POLICY IF EXISTS "Public recipe forks are viewable by everyone" ON public.recipe_forks;
DROP POLICY IF EXISTS "Users can create their own recipe forks" ON public.recipe_forks;
DROP POLICY IF EXISTS "Users can delete their own recipe forks" ON public.recipe_forks;

DROP POLICY IF EXISTS "Users can view public posts and their own posts" ON public.user_posts;
DROP POLICY IF EXISTS "Users can create their own posts" ON public.user_posts;
DROP POLICY IF EXISTS "Users can update their own posts" ON public.user_posts;
DROP POLICY IF EXISTS "Users can delete their own posts" ON public.user_posts;

DROP POLICY IF EXISTS "Users can view recipe activity" ON public.recipe_activity;
DROP POLICY IF EXISTS "Users can create recipe activity" ON public.recipe_activity;

-- Create policies for recipe_forks
CREATE POLICY "Public recipe forks are viewable by everyone"
ON public.recipe_forks FOR SELECT
USING (true);

CREATE POLICY "Users can create their own recipe forks"
ON public.recipe_forks FOR INSERT
WITH CHECK (auth.uid() = forked_by_user_id);

CREATE POLICY "Users can delete their own recipe forks"
ON public.recipe_forks FOR DELETE
USING (auth.uid() = forked_by_user_id);

-- Create policies for user_posts
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

-- Create policies for recipe_activity
CREATE POLICY "Users can view recipe activity"
ON public.recipe_activity FOR SELECT
USING (true);

CREATE POLICY "Users can create recipe activity"
ON public.recipe_activity FOR INSERT
WITH CHECK (auth.uid() = user_id);

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
        AND forked_by_user_id = user_uuid
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to create recipe activity entry
CREATE OR REPLACE FUNCTION create_recipe_activity(
    p_recipe_id INTEGER,
    p_user_id UUID,
    p_activity_type TEXT,
    p_original_recipe_id INTEGER DEFAULT NULL,
    p_description TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    activity_id UUID;
BEGIN
    INSERT INTO public.recipe_activity (
        recipe_id,
        user_id,
        activity_type,
        original_recipe_id,
        description
    ) VALUES (
        p_recipe_id,
        p_user_id,
        p_activity_type,
        p_original_recipe_id,
        p_description
    ) RETURNING id INTO activity_id;
    
    RETURN activity_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ================================================
-- TRIGGERS FOR AUTOMATIC ACTIVITY TRACKING
-- ================================================

-- Function to automatically create activity when recipes are forked
CREATE OR REPLACE FUNCTION trigger_recipe_fork_activity()
RETURNS TRIGGER AS $$
BEGIN
    -- Create activity entry for the fork
    INSERT INTO public.recipe_activity (
        recipe_id,
        user_id,
        activity_type,
        original_recipe_id,
        description
    ) VALUES (
        NEW.forked_recipe_id,
        NEW.forked_by_user_id,
        'forked',
        NEW.original_recipe_id,
        COALESCE(NEW.fork_reason, 'Forked this recipe')
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for recipe forks
DROP TRIGGER IF EXISTS trigger_recipe_fork_activity ON public.recipe_forks;
CREATE TRIGGER trigger_recipe_fork_activity
    AFTER INSERT ON public.recipe_forks
    FOR EACH ROW
    EXECUTE FUNCTION trigger_recipe_fork_activity();

-- ================================================
-- GRANT PERMISSIONS
-- ================================================

-- Grant necessary permissions
GRANT ALL ON public.recipe_forks TO authenticated;
GRANT ALL ON public.user_posts TO authenticated;
GRANT ALL ON public.recipe_activity TO authenticated;

GRANT EXECUTE ON FUNCTION get_recipe_fork_count(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION is_recipe_forked_by_user(INTEGER, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION create_recipe_activity(INTEGER, UUID, TEXT, INTEGER, TEXT) TO authenticated;

-- ================================================
-- VERIFICATION
-- ================================================

-- Verify everything was set up correctly
SELECT 
    table_name,
    COUNT(*) as column_count
FROM information_schema.columns 
WHERE table_name IN ('recipe_forks', 'user_posts', 'recipe_activity') 
    AND table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;

-- Success message
SELECT 'Migration 004 completed successfully! All tables updated and Git-for-Recipes ready!' as status;