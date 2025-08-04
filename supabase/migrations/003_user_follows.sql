-- ================================================
-- NuestrasRecetas.club - User Follow System (Consolidated Migration)
-- ================================================

-- Drop existing user_follows table if it exists (to handle schema conflicts)
DROP TABLE IF EXISTS public.user_follows CASCADE;

-- Create user_follows table with correct schema
CREATE TABLE public.user_follows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  follower_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  following_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Prevent self-follows and duplicate follows
  CONSTRAINT no_self_follow CHECK (follower_id != following_id),
  CONSTRAINT unique_follow UNIQUE (follower_id, following_id)
);

-- Enable RLS for user_follows
ALTER TABLE public.user_follows ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_follows
-- Anyone can see who follows whom (for public profiles)
CREATE POLICY "User follows are publicly visible" ON public.user_follows
  FOR SELECT USING (true);

-- Users can only create follows for themselves  
CREATE POLICY "Users can follow others" ON public.user_follows
  FOR INSERT WITH CHECK (follower_id = auth.uid());

-- Users can only unfollow their own follows
CREATE POLICY "Users can unfollow others" ON public.user_follows
  FOR DELETE USING (follower_id = auth.uid());

-- Create indexes for better performance
CREATE INDEX idx_user_follows_follower_id ON public.user_follows(follower_id);
CREATE INDEX idx_user_follows_following_id ON public.user_follows(following_id);
CREATE INDEX idx_user_follows_created_at ON public.user_follows(created_at DESC);

-- Add follower/following counts to profiles table
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS followers_count INTEGER DEFAULT 0;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS following_count INTEGER DEFAULT 0;

-- Create function to update follower counts
CREATE OR REPLACE FUNCTION public.update_follow_counts()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    -- Increment following count for follower
    UPDATE public.profiles 
    SET following_count = following_count + 1 
    WHERE id = NEW.follower_id;
    
    -- Increment followers count for followed user
    UPDATE public.profiles 
    SET followers_count = followers_count + 1 
    WHERE id = NEW.following_id;
    
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    -- Decrement following count for follower
    UPDATE public.profiles 
    SET following_count = following_count - 1 
    WHERE id = OLD.follower_id;
    
    -- Decrement followers count for followed user
    UPDATE public.profiles 
    SET followers_count = followers_count - 1 
    WHERE id = OLD.following_id;
    
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$;

-- Create trigger for follow count updates
CREATE TRIGGER trigger_update_follow_counts
  AFTER INSERT OR DELETE ON public.user_follows
  FOR EACH ROW EXECUTE FUNCTION public.update_follow_counts();

-- Create view for user search with follow status
CREATE OR REPLACE VIEW public.user_search_view AS
SELECT 
  p.id,
  p.username,
  p.name,
  p.avatar_url,
  p.bio,
  p.followers_count,
  p.following_count,
  p.created_at,
  COALESCE(recipe_counts.recipe_count, 0) as recipe_count
FROM public.profiles p
LEFT JOIN (
  SELECT user_id, COUNT(*) as recipe_count
  FROM public.recipes
  WHERE is_public = true
  GROUP BY user_id
) recipe_counts ON p.id = recipe_counts.user_id
WHERE p.is_public = true;

-- Enable RLS on the view
ALTER VIEW public.user_search_view SET (security_invoker = true);

-- Create function to search users
CREATE OR REPLACE FUNCTION public.search_users(search_query TEXT, current_user_id UUID DEFAULT NULL, limit_count INTEGER DEFAULT 20)
RETURNS TABLE(
  id UUID,
  username TEXT,
  name TEXT,
  avatar_url TEXT,
  bio TEXT,
  followers_count INTEGER,
  following_count INTEGER,
  recipe_count BIGINT,
  is_following BOOLEAN,
  follows_back BOOLEAN
) LANGUAGE SQL SECURITY DEFINER AS $$
  SELECT 
    u.id,
    u.username,
    u.name,
    u.avatar_url,
    u.bio,
    u.followers_count,
    u.following_count,
    u.recipe_count,
    CASE WHEN current_user_id IS NOT NULL THEN
      EXISTS(SELECT 1 FROM public.user_follows WHERE follower_id = current_user_id AND following_id = u.id)
    ELSE false END as is_following,
    CASE WHEN current_user_id IS NOT NULL THEN
      EXISTS(SELECT 1 FROM public.user_follows WHERE follower_id = u.id AND following_id = current_user_id)
    ELSE false END as follows_back
  FROM public.user_search_view u
  WHERE 
    (search_query IS NULL OR search_query = '' OR
     u.username ILIKE '%' || search_query || '%' OR
     u.name ILIKE '%' || search_query || '%')
    AND (current_user_id IS NULL OR u.id != current_user_id) -- Exclude current user from search results
  ORDER BY 
    -- Prioritize exact matches
    CASE WHEN u.username = search_query THEN 1 ELSE 2 END,
    u.followers_count DESC,
    u.created_at DESC
  LIMIT limit_count;
$$;

-- Create user stats view for better performance
CREATE OR REPLACE VIEW public.user_stats AS
SELECT 
  p.id,
  p.username,
  p.name,
  p.avatar_url,
  p.bio,
  p.is_public,
  p.created_at,
  p.followers_count,
  p.following_count,
  COALESCE(recipe_counts.recipe_count, 0) as recipe_count
FROM public.profiles p
LEFT JOIN (
  SELECT user_id, COUNT(*) as recipe_count
  FROM public.recipes
  WHERE is_public = true
  GROUP BY user_id
) recipe_counts ON p.id = recipe_counts.user_id;

-- Create function to get user feed
CREATE OR REPLACE FUNCTION public.get_user_feed(user_id UUID, page_limit INTEGER DEFAULT 20, page_offset INTEGER DEFAULT 0)
RETURNS TABLE(
  id INTEGER,
  title TEXT,
  description TEXT,
  image_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  username TEXT,
  user_name TEXT,
  user_avatar TEXT,
  like_count BIGINT,
  comment_count BIGINT
) LANGUAGE SQL SECURITY DEFINER AS $$
  SELECT 
    r.id,
    r.title,
    r.description,
    r.image_url,
    r.created_at,
    p.username,
    p.name as user_name,
    p.avatar_url as user_avatar,
    COALESCE(like_counts.like_count, 0) as like_count,
    COALESCE(comment_counts.comment_count, 0) as comment_count
  FROM public.recipes r
  JOIN public.profiles p ON r.user_id = p.id
  JOIN public.user_follows uf ON p.id = uf.following_id
  LEFT JOIN (
    SELECT recipe_id, COUNT(*) as like_count
    FROM public.recipe_likes
    GROUP BY recipe_id
  ) like_counts ON r.id = like_counts.recipe_id
  LEFT JOIN (
    SELECT recipe_id, COUNT(*) as comment_count
    FROM public.comments
    GROUP BY recipe_id
  ) comment_counts ON r.id = comment_counts.recipe_id
  WHERE uf.follower_id = user_id
    AND r.is_public = true
  ORDER BY r.created_at DESC
  LIMIT page_limit
  OFFSET page_offset;
$$;

-- Grant permissions
GRANT ALL ON public.user_follows TO anon, authenticated;
GRANT ALL ON public.user_search_view TO anon, authenticated;
GRANT ALL ON public.user_stats TO anon, authenticated;