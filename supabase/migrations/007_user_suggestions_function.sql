-- ================================================
-- User Suggestions Algorithm Migration (Simplified)
-- ================================================
-- Creates intelligent user suggestion system for community discovery

-- Create performance indexes for user suggestions
CREATE INDEX IF NOT EXISTS idx_user_follows_follower_following 
ON public.user_follows(follower_id, following_id);

CREATE INDEX IF NOT EXISTS idx_profiles_followers_count_public 
ON public.profiles(followers_count DESC, is_public) 
WHERE is_public = true;

CREATE INDEX IF NOT EXISTS idx_profiles_created_at_public 
ON public.profiles(created_at DESC, is_public) 
WHERE is_public = true;

CREATE INDEX IF NOT EXISTS idx_recipes_user_category_public 
ON public.recipes(user_id, category) 
WHERE is_public = true;

CREATE INDEX IF NOT EXISTS idx_user_posts_user_created_public 
ON public.user_posts(user_id, created_at DESC) 
WHERE is_public = true;

-- Main user suggestions function with intelligent recommendation algorithm
CREATE OR REPLACE FUNCTION public.get_suggested_users(
    input_user_id UUID,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE(
    id UUID,
    username TEXT,
    name TEXT,
    avatar_url TEXT,
    bio TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    recipe_count BIGINT,
    suggestion_reason TEXT,
    relevance_score NUMERIC,
    mutual_connections INTEGER,
    activity_score NUMERIC,
    is_new_user BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE SQL
SECURITY DEFINER
AS $$
WITH user_following AS (
    -- Get users that the input user is already following
    SELECT following_id
    FROM public.user_follows
    WHERE follower_id = input_user_id
),
mutual_connections AS (
    -- Find users followed by people the input user follows (friends of friends)
    SELECT 
        uf2.following_id as suggested_user_id,
        COUNT(DISTINCT uf2.follower_id) as mutual_count,
        STRING_AGG(DISTINCT p.name, ', ' ORDER BY p.name) as mutual_names
    FROM public.user_follows uf1  -- Users input_user follows
    JOIN public.user_follows uf2 ON uf1.following_id = uf2.follower_id  -- Who they follow
    JOIN public.profiles p ON uf2.follower_id = p.id  -- Names of mutual connections
    WHERE uf1.follower_id = input_user_id
      AND uf2.following_id != input_user_id  -- Don't suggest the input user
      AND uf2.following_id NOT IN (SELECT following_id FROM user_following)  -- Not already following
    GROUP BY uf2.following_id
),
user_categories AS (
    -- Get input user's recipe categories for interest matching
    SELECT DISTINCT category
    FROM public.recipes
    WHERE user_id = input_user_id AND is_public = true AND category IS NOT NULL
),
similar_interests AS (
    -- Find users with similar cooking interests (simplified)
    SELECT 
        r.user_id as suggested_user_id,
        COUNT(DISTINCT r.category) as matching_categories
    FROM public.recipes r
    WHERE r.is_public = true
      AND r.user_id != input_user_id
      AND r.user_id NOT IN (SELECT following_id FROM user_following)
      AND r.category IN (SELECT category FROM user_categories)
    GROUP BY r.user_id
),
active_users AS (
    -- Find recently active users
    SELECT 
        p.id as suggested_user_id,
        COUNT(DISTINCT r.id) as recent_recipes,
        COUNT(DISTINCT up.id) as recent_posts,
        GREATEST(
            EXTRACT(EPOCH FROM (NOW() - MAX(r.created_at))) / 86400.0,
            EXTRACT(EPOCH FROM (NOW() - MAX(up.created_at))) / 86400.0
        ) as days_since_activity
    FROM public.profiles p
    LEFT JOIN public.recipes r ON p.id = r.user_id 
        AND r.created_at >= NOW() - INTERVAL '30 days' 
        AND r.is_public = true
    LEFT JOIN public.user_posts up ON p.id = up.user_id 
        AND up.created_at >= NOW() - INTERVAL '30 days' 
        AND up.is_public = true
    WHERE p.is_public = true
      AND p.id != input_user_id
      AND p.id NOT IN (SELECT following_id FROM user_following)
    GROUP BY p.id
    HAVING COUNT(DISTINCT r.id) > 0 OR COUNT(DISTINCT up.id) > 0
),
popular_users AS (
    -- Find popular users (high follower count)
    SELECT 
        id as suggested_user_id,
        followers_count
    FROM public.profiles
    WHERE is_public = true
      AND id != input_user_id
      AND id NOT IN (SELECT following_id FROM user_following)
      AND followers_count > 0
),
new_users AS (
    -- Find recently joined users
    SELECT 
        id as suggested_user_id,
        EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 as days_old
    FROM public.profiles
    WHERE is_public = true
      AND id != input_user_id  
      AND id NOT IN (SELECT following_id FROM user_following)
      AND created_at >= NOW() - INTERVAL '14 days'  -- Users who joined in last 2 weeks
),
all_suggestions AS (
    -- Combine all suggestion types with scoring
    SELECT DISTINCT
        p.id,
        p.username,
        p.name,
        p.avatar_url,
        p.bio,
        p.followers_count,
        p.following_count,
        COALESCE(recipe_counts.recipe_count, 0) as recipe_count,
        CASE 
            WHEN mc.suggested_user_id IS NOT NULL THEN 
                'Followed by ' || 
                CASE 
                    WHEN mc.mutual_count = 1 THEN SUBSTRING(mc.mutual_names, 1, 50) || ' (1 mutual connection)'
                    WHEN mc.mutual_count <= 3 THEN mc.mutual_names || ' (' || mc.mutual_count || ' mutual connections)'
                    ELSE SUBSTRING(mc.mutual_names, 1, 30) || '... (' || mc.mutual_count || ' mutual connections)'
                END
            WHEN si.suggested_user_id IS NOT NULL THEN 
                'Cooks similar recipes (' || si.matching_categories || ' shared categories)'
            WHEN au.suggested_user_id IS NOT NULL THEN 
                'Recently active (' || au.recent_recipes + au.recent_posts || ' recent activities)'
            WHEN pu.suggested_user_id IS NOT NULL THEN 
                'Popular chef (' || pu.followers_count || ' followers)'
            WHEN nu.suggested_user_id IS NOT NULL THEN 
                'New community member (joined ' || ROUND(nu.days_old) || ' days ago)'
            ELSE 'Recommended for you'
        END as suggestion_reason,
        -- Calculate relevance score
        COALESCE(mc.mutual_count * 10, 0) +  -- Mutual connections are highest priority
        COALESCE(si.matching_categories * 3, 0) +  -- Similar interests
        CASE WHEN au.suggested_user_id IS NOT NULL THEN 
            GREATEST(5 - COALESCE(au.days_since_activity, 30), 0) 
        ELSE 0 END +  -- Recent activity bonus
        CASE WHEN pu.followers_count > 50 THEN 3
             WHEN pu.followers_count > 10 THEN 2  
             WHEN pu.followers_count > 0 THEN 1
             ELSE 0 END +  -- Popularity bonus
        CASE WHEN nu.suggested_user_id IS NOT NULL THEN 2 ELSE 0 END as relevance_score,  -- New user bonus
        COALESCE(mc.mutual_count, 0) as mutual_connections,
        COALESCE(au.recent_recipes + au.recent_posts, 0) as activity_score,
        (nu.suggested_user_id IS NOT NULL) as is_new_user,
        p.created_at
    FROM public.profiles p
    LEFT JOIN mutual_connections mc ON p.id = mc.suggested_user_id
    LEFT JOIN similar_interests si ON p.id = si.suggested_user_id  
    LEFT JOIN active_users au ON p.id = au.suggested_user_id
    LEFT JOIN popular_users pu ON p.id = pu.suggested_user_id
    LEFT JOIN new_users nu ON p.id = nu.suggested_user_id
    LEFT JOIN (
        SELECT user_id, COUNT(*) as recipe_count
        FROM public.recipes
        WHERE is_public = true
        GROUP BY user_id
    ) recipe_counts ON p.id = recipe_counts.user_id
    WHERE p.is_public = true
      AND p.id != input_user_id
      AND p.id NOT IN (SELECT following_id FROM user_following)
      AND (mc.suggested_user_id IS NOT NULL 
           OR si.suggested_user_id IS NOT NULL 
           OR au.suggested_user_id IS NOT NULL 
           OR pu.suggested_user_id IS NOT NULL 
           OR nu.suggested_user_id IS NOT NULL)
)
SELECT *
FROM all_suggestions
ORDER BY relevance_score DESC, followers_count DESC, created_at DESC
LIMIT limit_count;
$$;

-- Helper function to get user suggestion analytics
CREATE OR REPLACE FUNCTION public.get_user_suggestion_stats(
    input_user_id UUID
)
RETURNS TABLE(
    total_available_users INTEGER,
    mutual_connection_suggestions INTEGER,
    similar_interest_suggestions INTEGER,
    active_user_suggestions INTEGER,
    popular_user_suggestions INTEGER,
    new_user_suggestions INTEGER,
    already_following_count INTEGER
)
LANGUAGE SQL
SECURITY DEFINER
AS $$
WITH stats AS (
    SELECT
        COUNT(*) FILTER (WHERE p.is_public = true AND p.id != input_user_id) as total_available,
        COUNT(*) FILTER (WHERE uf_check.following_id IS NOT NULL) as already_following,
        COUNT(DISTINCT mc.suggested_user_id) as mutual_connections,
        COUNT(DISTINCT si.suggested_user_id) as similar_interests,
        COUNT(DISTINCT au.suggested_user_id) as active_users,
        COUNT(DISTINCT pu.suggested_user_id) as popular_users,
        COUNT(DISTINCT nu.suggested_user_id) as new_users
    FROM public.profiles p
    LEFT JOIN public.user_follows uf_check ON uf_check.follower_id = input_user_id AND uf_check.following_id = p.id
    LEFT JOIN (
        SELECT DISTINCT uf2.following_id as suggested_user_id
        FROM public.user_follows uf1
        JOIN public.user_follows uf2 ON uf1.following_id = uf2.follower_id
        WHERE uf1.follower_id = input_user_id
          AND uf2.following_id != input_user_id
    ) mc ON p.id = mc.suggested_user_id
    LEFT JOIN (
        SELECT DISTINCT r.user_id as suggested_user_id
        FROM public.recipes r
        WHERE r.is_public = true AND r.user_id != input_user_id
    ) si ON p.id = si.suggested_user_id
    LEFT JOIN (
        SELECT DISTINCT p2.id as suggested_user_id
        FROM public.profiles p2
        LEFT JOIN public.recipes r ON p2.id = r.user_id AND r.created_at >= NOW() - INTERVAL '30 days'
        LEFT JOIN public.user_posts up ON p2.id = up.user_id AND up.created_at >= NOW() - INTERVAL '30 days'
        WHERE p2.is_public = true AND (r.id IS NOT NULL OR up.id IS NOT NULL)
    ) au ON p.id = au.suggested_user_id
    LEFT JOIN (
        SELECT id as suggested_user_id
        FROM public.profiles
        WHERE followers_count > 0
    ) pu ON p.id = pu.suggested_user_id
    LEFT JOIN (
        SELECT id as suggested_user_id
        FROM public.profiles
        WHERE created_at >= NOW() - INTERVAL '14 days'
    ) nu ON p.id = nu.suggested_user_id
)
SELECT 
    total_available::INTEGER,
    mutual_connections::INTEGER,
    similar_interests::INTEGER,
    active_users::INTEGER,
    popular_users::INTEGER,
    new_users::INTEGER,
    already_following::INTEGER
FROM stats;
$$;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION public.get_suggested_users(UUID, INTEGER) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_suggestion_stats(UUID) TO anon, authenticated;