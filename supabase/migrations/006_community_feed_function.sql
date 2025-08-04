-- ================================================
-- Community Feed Function Migration
-- ================================================
-- Creates get_community_feed() function for the community activity feed
-- and associated performance indexes

-- Create performance indexes for community feed queries
CREATE INDEX IF NOT EXISTS idx_recipes_public_created_at 
ON public.recipes(created_at DESC) 
WHERE is_public = true;

CREATE INDEX IF NOT EXISTS idx_recipe_forks_created_at 
ON public.recipe_forks(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_posts_public_created_at 
ON public.user_posts(created_at DESC) 
WHERE is_public = true;

CREATE INDEX IF NOT EXISTS idx_user_follows_created_at 
ON public.user_follows(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_profiles_public_status 
ON public.profiles(is_public) 
WHERE is_public = true;

-- Main community feed function
CREATE OR REPLACE FUNCTION public.get_community_feed(
    input_user_id UUID DEFAULT NULL,
    page_limit INTEGER DEFAULT 20,
    page_offset INTEGER DEFAULT 0
)
RETURNS TABLE(
    activity_id TEXT,
    activity_type TEXT,
    title TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    user_id UUID,
    username TEXT,
    user_name TEXT,
    user_avatar TEXT,
    recipe_id INTEGER,
    recipe_title TEXT,
    original_recipe_id INTEGER,
    original_recipe_title TEXT,
    followed_user_id UUID,
    followed_username TEXT,
    followed_user_name TEXT,
    metadata JSONB
) 
LANGUAGE SQL
SECURITY DEFINER
AS $$
WITH community_activities AS (
    -- New public recipes
    SELECT 
        'recipe_' || r.id::TEXT as activity_id,
        'new_recipe' as activity_type,
        '📝 ' || p.name || ' shared a new recipe' as title,
        r.description as description,
        r.created_at,
        p.id as user_id,
        p.username,
        p.name as user_name,
        p.avatar_url as user_avatar,
        r.id as recipe_id,
        r.title as recipe_title,
        NULL::INTEGER as original_recipe_id,
        NULL::TEXT as original_recipe_title,
        NULL::UUID as followed_user_id,
        NULL::TEXT as followed_username,
        NULL::TEXT as followed_user_name,
        jsonb_build_object(
            'category', r.category,
            'difficulty', r.difficulty,
            'prep_time', r.prep_time,
            'cook_time', r.cook_time,
            'servings', r.servings
        ) as metadata
    FROM public.recipes r
    JOIN public.profiles p ON r.user_id = p.id
    WHERE r.is_public = true 
      AND p.is_public = true
      AND r.created_at >= NOW() - INTERVAL '30 days'

    UNION ALL

    -- Recipe forks
    SELECT 
        'fork_' || rf.id::TEXT as activity_id,
        'recipe_fork' as activity_type,
        '🍴 ' || p.name || ' forked ' || orig_author.name || '''s recipe' as title,
        'Forked: ' || orig_recipe.title as description,
        rf.created_at,
        p.id as user_id,
        p.username,
        p.name as user_name,
        p.avatar_url as user_avatar,
        rf.forked_recipe_id as recipe_id,
        forked_recipe.title as recipe_title,
        rf.original_recipe_id,
        orig_recipe.title as original_recipe_title,
        NULL::UUID as followed_user_id,
        NULL::TEXT as followed_username,
        NULL::TEXT as followed_user_name,
        jsonb_build_object(
            'fork_reason', rf.fork_reason,
            'branch_name', rf.branch_name,
            'original_author', orig_author.name,
            'original_author_username', orig_author.username
        ) as metadata
    FROM public.recipe_forks rf
    JOIN public.profiles p ON rf.forked_by = p.id
    JOIN public.recipes orig_recipe ON rf.original_recipe_id = orig_recipe.id
    JOIN public.profiles orig_author ON orig_recipe.user_id = orig_author.id
    JOIN public.recipes forked_recipe ON rf.forked_recipe_id = forked_recipe.id
    WHERE p.is_public = true 
      AND orig_recipe.is_public = true
      AND forked_recipe.is_public = true
      AND rf.created_at >= NOW() - INTERVAL '30 days'

    UNION ALL

    -- Public user posts (excluding group posts)
    SELECT 
        'post_' || up.id::TEXT as activity_id,
        'user_post' as activity_type,
        CASE 
            WHEN up.post_type = 'recipe_share' THEN '📋 ' || p.name || ' shared thoughts about a recipe'
            WHEN up.post_type = 'achievement' THEN '🏆 ' || p.name || ' achieved something!'
            WHEN up.post_type = 'recipe_fork' THEN '🍴 ' || p.name || ' forked a recipe'
            ELSE '💬 ' || p.name || ' shared an update'
        END as title,
        up.content as description,
        up.created_at,
        p.id as user_id,
        p.username,
        p.name as user_name,
        p.avatar_url as user_avatar,
        up.recipe_id,
        r.title as recipe_title,
        NULL::INTEGER as original_recipe_id,
        NULL::TEXT as original_recipe_title,
        NULL::UUID as followed_user_id,
        NULL::TEXT as followed_username,
        NULL::TEXT as followed_user_name,
        jsonb_build_object(
            'post_type', up.post_type,
            'metadata', up.metadata
        ) as metadata
    FROM public.user_posts up
    JOIN public.profiles p ON up.user_id = p.id
    LEFT JOIN public.recipes r ON up.recipe_id = r.id
    WHERE up.is_public = true 
      AND p.is_public = true
      AND up.group_id IS NULL  -- Only public posts, not group posts
      AND up.created_at >= NOW() - INTERVAL '30 days'

    UNION ALL

    -- New follow relationships (optional - only if both users are public)
    SELECT 
        'follow_' || uf.id::TEXT as activity_id,
        'new_follow' as activity_type,
        '👥 ' || follower.name || ' started following ' || following.name as title,
        'New connection in the community' as description,
        uf.created_at,
        follower.id as user_id,
        follower.username,
        follower.name as user_name,
        follower.avatar_url as user_avatar,
        NULL::INTEGER as recipe_id,
        NULL::TEXT as recipe_title,
        NULL::INTEGER as original_recipe_id,
        NULL::TEXT as original_recipe_title,
        following.id as followed_user_id,
        following.username as followed_username,
        following.name as followed_user_name,
        jsonb_build_object(
            'follower_id', follower.id,
            'following_id', following.id
        ) as metadata
    FROM public.user_follows uf
    JOIN public.profiles follower ON uf.follower_id = follower.id
    JOIN public.profiles following ON uf.following_id = following.id
    WHERE follower.is_public = true 
      AND following.is_public = true
      AND uf.created_at >= NOW() - INTERVAL '7 days'  -- Only recent follows to avoid spam
)
SELECT *
FROM community_activities
ORDER BY created_at DESC
LIMIT page_limit
OFFSET page_offset;
$$;

-- Helper function to get community activity statistics
CREATE OR REPLACE FUNCTION public.get_community_activity_stats(
    days_back INTEGER DEFAULT 7
)
RETURNS TABLE(
    activity_type TEXT,
    activity_count BIGINT,
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE
)
LANGUAGE SQL
SECURITY DEFINER
AS $$
SELECT 
    activity_type,
    COUNT(*) as activity_count,
    NOW() - (days_back || ' days')::INTERVAL as period_start,
    NOW() as period_end
FROM (
    SELECT 'new_recipe' as activity_type, r.created_at
    FROM public.recipes r
    JOIN public.profiles p ON r.user_id = p.id
    WHERE r.is_public = true 
      AND p.is_public = true
      AND r.created_at >= NOW() - (days_back || ' days')::INTERVAL

    UNION ALL

    SELECT 'recipe_fork' as activity_type, rf.created_at
    FROM public.recipe_forks rf
    JOIN public.profiles p ON rf.forked_by = p.id
    WHERE p.is_public = true
      AND rf.created_at >= NOW() - (days_back || ' days')::INTERVAL

    UNION ALL

    SELECT 'user_post' as activity_type, up.created_at
    FROM public.user_posts up
    JOIN public.profiles p ON up.user_id = p.id
    WHERE up.is_public = true 
      AND p.is_public = true
      AND up.group_id IS NULL
      AND up.created_at >= NOW() - (days_back || ' days')::INTERVAL

    UNION ALL

    SELECT 'new_follow' as activity_type, uf.created_at
    FROM public.user_follows uf
    JOIN public.profiles follower ON uf.follower_id = follower.id
    JOIN public.profiles following ON uf.following_id = following.id
    WHERE follower.is_public = true 
      AND following.is_public = true
      AND uf.created_at >= NOW() - (days_back || ' days')::INTERVAL
) activities
GROUP BY activity_type
ORDER BY activity_count DESC;
$$;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION public.get_community_feed(UUID, INTEGER, INTEGER) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_community_activity_stats(INTEGER) TO anon, authenticated;