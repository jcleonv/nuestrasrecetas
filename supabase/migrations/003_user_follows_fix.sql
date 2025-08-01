-- ================================================
-- Fix user_follows table and add follow counts
-- ================================================

-- Add missing columns to profiles table for follow counts
alter table public.profiles add column if not exists followers_count integer default 0;
alter table public.profiles add column if not exists following_count integer default 0;

-- Rename followed_id to following_id in user_follows table
alter table public.user_follows rename column followed_id to following_id;

-- Drop existing indexes and recreate with new column name
drop index if exists idx_user_follows_followed;
create index if not exists idx_user_follows_following_id on public.user_follows(following_id);

-- Update the user_stats view to use new column name
create or replace view public.user_stats as
select 
  p.id,
  p.username,
  p.name,
  p.avatar_url,
  p.bio,
  p.is_public,
  p.created_at,
  coalesce(recipe_counts.recipe_count, 0) as recipe_count,
  coalesce(follower_counts.follower_count, 0) as follower_count,
  coalesce(following_counts.following_count, 0) as following_count
from public.profiles p
left join (
  select user_id, count(*) as recipe_count
  from public.recipes
  where is_public = true
  group by user_id
) recipe_counts on p.id = recipe_counts.user_id
left join (
  select following_id, count(*) as follower_count
  from public.user_follows
  group by following_id
) follower_counts on p.id = follower_counts.following_id
left join (
  select follower_id, count(*) as following_count
  from public.user_follows
  group by follower_id
) following_counts on p.id = following_counts.follower_id;

-- Update the get_user_feed function to use new column name
create or replace function public.get_user_feed(user_id uuid, page_limit integer default 20, page_offset integer default 0)
returns table(
  id integer,
  title text,
  description text,
  image_url text,
  created_at timestamp with time zone,
  username text,
  user_name text,
  user_avatar text,
  like_count bigint,
  comment_count bigint
)
language sql
security definer
as $$
  select 
    rd.id,
    rd.title,
    rd.description,
    rd.image_url,
    rd.created_at,
    rd.username,
    rd.user_name,
    rd.user_avatar,
    rd.like_count,
    rd.comment_count
  from public.recipe_details rd
  join public.user_follows uf on rd.user_id::uuid = uf.following_id
  where uf.follower_id = user_id
    and rd.is_public = true
  order by rd.created_at desc
  limit page_limit
  offset page_offset;
$$;

-- Create function to update follow counts
create or replace function public.update_follow_counts()
returns trigger language plpgsql
as $$
begin
  if tg_op = 'INSERT' then
    -- Increment follower count for the person being followed
    update public.profiles 
    set followers_count = followers_count + 1
    where id = new.following_id;
    
    -- Increment following count for the person doing the following
    update public.profiles 
    set following_count = following_count + 1
    where id = new.follower_id;
    
    return new;
  elsif tg_op = 'DELETE' then
    -- Decrement follower count for the person being unfollowed
    update public.profiles 
    set followers_count = followers_count - 1
    where id = old.following_id;
    
    -- Decrement following count for the person doing the unfollowing
    update public.profiles 
    set following_count = following_count - 1
    where id = old.follower_id;
    
    return old;
  end if;
  return null;
end;
$$;

-- Create trigger for follow count updates
drop trigger if exists trigger_update_follow_counts on public.user_follows;
create trigger trigger_update_follow_counts
  after insert or delete on public.user_follows
  for each row execute procedure public.update_follow_counts();

-- Create user search view and function
create or replace view public.user_search_view as
select 
  p.id,
  p.username,
  p.name,
  p.avatar_url,
  p.bio,
  p.followers_count,
  p.following_count,
  coalesce(recipe_counts.recipe_count, 0) as recipe_count
from public.profiles p
left join (
  select user_id, count(*) as recipe_count
  from public.recipes
  where is_public = true
  group by user_id
) recipe_counts on p.id = recipe_counts.user_id
where p.is_public = true;

-- Create search function
create or replace function public.search_users(search_term text, current_user_id uuid default null)
returns table(
  id uuid,
  username text,
  name text,
  avatar_url text,
  bio text,
  followers_count integer,
  following_count integer,
  recipe_count bigint,
  is_following boolean,
  follows_back boolean
)
language sql
security definer
as $$
  select 
    u.id,
    u.username,
    u.name,
    u.avatar_url,
    u.bio,
    u.followers_count,
    u.following_count,
    u.recipe_count,
    case when current_user_id is not null then
      exists(select 1 from public.user_follows where follower_id = current_user_id and following_id = u.id)
    else false end as is_following,
    case when current_user_id is not null then
      exists(select 1 from public.user_follows where follower_id = u.id and following_id = current_user_id)
    else false end as follows_back
  from public.user_search_view u
  where 
    (search_term = '' or search_term is null) or
    (u.username ilike '%' || search_term || '%' or u.name ilike '%' || search_term || '%')
  order by 
    case when u.username ilike search_term || '%' then 1
         when u.name ilike search_term || '%' then 2
         when u.username ilike '%' || search_term || '%' then 3
         when u.name ilike '%' || search_term || '%' then 4
         else 5 end,
    u.followers_count desc
  limit 50;
$$;

-- Initialize follow counts for existing users
update public.profiles 
set followers_count = (
  select coalesce(count(*), 0) 
  from public.user_follows 
  where following_id = profiles.id
),
following_count = (
  select coalesce(count(*), 0) 
  from public.user_follows 
  where follower_id = profiles.id
);

-- Grant permissions
grant all on public.user_search_view to anon, authenticated;