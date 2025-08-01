-- ================================================
-- NuestrasRecetas.club - User Follow System ("Cook" Feature)
-- ================================================

-- Create user_follows table for the "cook" (follow) system
create table if not exists public.user_follows (
  id uuid primary key default uuid_generate_v4(),
  follower_id uuid not null references public.profiles(id) on delete cascade,
  following_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamp with time zone default now(),
  
  -- Prevent self-follows and duplicate follows
  constraint no_self_follow check (follower_id != following_id),
  constraint unique_follow unique (follower_id, following_id)
);

-- Enable RLS for user_follows
alter table public.user_follows enable row level security;

-- RLS Policies for user_follows
-- Anyone can see who follows whom (for public profiles)
drop policy if exists "User follows are publicly visible" on public.user_follows;
create policy "User follows are publicly visible" on public.user_follows
  for select using (true);

-- Users can only create follows for themselves  
drop policy if exists "Users can follow others" on public.user_follows;
create policy "Users can follow others" on public.user_follows
  for insert with check (follower_id = auth.uid());

-- Users can only unfollow their own follows
drop policy if exists "Users can unfollow others" on public.user_follows;
create policy "Users can unfollow others" on public.user_follows
  for delete using (follower_id = auth.uid());

-- Create indexes for better performance
create index if not exists idx_user_follows_follower_id on public.user_follows(follower_id);
create index if not exists idx_user_follows_following_id on public.user_follows(following_id);
create index if not exists idx_user_follows_created_at on public.user_follows(created_at desc);

-- Add follower/following counts to profiles table
alter table public.profiles add column if not exists followers_count integer default 0;
alter table public.profiles add column if not exists following_count integer default 0;

-- Create function to update follower counts
create or replace function update_follow_counts()
returns trigger as $$
begin
  if TG_OP = 'INSERT' then
    -- Increment following count for follower
    update public.profiles 
    set following_count = following_count + 1 
    where id = NEW.follower_id;
    
    -- Increment followers count for followed user
    update public.profiles 
    set followers_count = followers_count + 1 
    where id = NEW.following_id;
    
    return NEW;
  elsif TG_OP = 'DELETE' then
    -- Decrement following count for follower
    update public.profiles 
    set following_count = following_count - 1 
    where id = OLD.follower_id;
    
    -- Decrement followers count for followed user
    update public.profiles 
    set followers_count = followers_count - 1 
    where id = OLD.following_id;
    
    return OLD;
  end if;
  return null;
end;
$$ language plpgsql;

-- Create trigger for follow count updates
drop trigger if exists trigger_update_follow_counts on public.user_follows;
create trigger trigger_update_follow_counts
  after insert or delete on public.user_follows
  for each row execute function update_follow_counts();

-- Create view for user search with follow status
create or replace view public.user_search_view as
select 
  p.id,
  p.username,
  p.name,
  p.avatar_url,
  p.bio,
  p.followers_count,
  p.following_count,
  p.created_at,
  -- Check if current user follows this profile
  exists(
    select 1 from public.user_follows uf 
    where uf.follower_id = auth.uid() and uf.following_id = p.id
  ) as is_following,
  -- Check if this profile follows current user back
  exists(
    select 1 from public.user_follows uf 
    where uf.follower_id = p.id and uf.following_id = auth.uid()
  ) as follows_back
from public.profiles p
where p.id != auth.uid(); -- Exclude current user from search results

-- Enable RLS on the view
alter view public.user_search_view set (security_invoker = true);

-- Create function to search users
create or replace function search_users(search_query text, limit_count integer default 20)
returns setof public.user_search_view as $$
begin
  return query
  select * from public.user_search_view
  where 
    username ilike '%' || search_query || '%' or
    name ilike '%' || search_query || '%'
  order by 
    -- Prioritize exact matches
    case when username = search_query then 1 else 2 end,
    followers_count desc,
    created_at desc
  limit limit_count;
end;
$$ language plpgsql security definer;