-- ================================================
-- NuestrasRecetas.club - Supabase Database Setup
-- ================================================

-- Enable necessary extensions
create extension if not exists "uuid-ossp";

-- Create profiles table that references Supabase auth.users
create table if not exists public.profiles (
  id uuid not null references auth.users on delete cascade,
  username text unique not null,
  name text not null,
  bio text default '',
  avatar_url text default '',
  is_public boolean default true,
  created_at timestamp with time zone default now(),
  last_active timestamp with time zone default now(),
  primary key (id)
);

-- Enable Row Level Security
alter table public.profiles enable row level security;

-- Create policies for profiles table
create policy "Profiles are viewable by everyone" on public.profiles
  for select using (true);

create policy "Users can insert their own profile" on public.profiles
  for insert with check (auth.uid() = id);

create policy "Users can update their own profile" on public.profiles
  for update using (auth.uid() = id);

-- Create recipes table
create table if not exists public.recipes (
  id serial primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  description text default '',
  category text default '',
  tags text default '',
  servings integer default 2,
  prep_time integer default 0,
  cook_time integer default 0,
  difficulty text default 'Easy',
  steps text default '',
  ingredients_json text default '[]',
  image_url text default '',
  is_public boolean default true,
  rating_avg float default 0.0,
  rating_count integer default 0,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Enable RLS for recipes
alter table public.recipes enable row level security;

-- Create policies for recipes
create policy "Public recipes are viewable by everyone" on public.recipes
  for select using (is_public = true);

create policy "Users can view their own recipes" on public.recipes
  for select using (auth.uid() = user_id);

create policy "Users can insert their own recipes" on public.recipes
  for insert with check (auth.uid() = user_id);

create policy "Users can update their own recipes" on public.recipes
  for update using (auth.uid() = user_id);

create policy "Users can delete their own recipes" on public.recipes
  for delete using (auth.uid() = user_id);

-- Create comments table
create table if not exists public.comments (
  id serial primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  recipe_id integer not null references public.recipes(id) on delete cascade,
  content text not null,
  created_at timestamp with time zone default now()
);

-- Enable RLS for comments
alter table public.comments enable row level security;

-- Create policies for comments
create policy "Comments are viewable by everyone" on public.comments
  for select using (true);

create policy "Users can insert their own comments" on public.comments
  for insert with check (auth.uid() = user_id);

create policy "Users can update their own comments" on public.comments
  for update using (auth.uid() = user_id);

create policy "Users can delete their own comments" on public.comments
  for delete using (auth.uid() = user_id);

-- Create plans table
create table if not exists public.plans (
  id serial primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  name text default 'Week Plan',
  plan_json text default '{}',
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Enable RLS for plans
alter table public.plans enable row level security;

-- Create policies for plans
create policy "Users can view their own plans" on public.plans
  for select using (auth.uid() = user_id);

create policy "Users can insert their own plans" on public.plans
  for insert with check (auth.uid() = user_id);

create policy "Users can update their own plans" on public.plans
  for update using (auth.uid() = user_id);

create policy "Users can delete their own plans" on public.plans
  for delete using (auth.uid() = user_id);

-- Create user_follows junction table
create table if not exists public.user_follows (
  follower_id uuid not null references public.profiles(id) on delete cascade,
  followed_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamp with time zone default now(),
  primary key (follower_id, followed_id)
);

-- Enable RLS for user_follows
alter table public.user_follows enable row level security;

-- Create policies for user_follows
create policy "Follow relationships are viewable by everyone" on public.user_follows
  for select using (true);

create policy "Users can create their own follows" on public.user_follows
  for insert with check (auth.uid() = follower_id);

create policy "Users can delete their own follows" on public.user_follows
  for delete using (auth.uid() = follower_id);

-- Create recipe_likes junction table
create table if not exists public.recipe_likes (
  user_id uuid not null references public.profiles(id) on delete cascade,
  recipe_id integer not null references public.recipes(id) on delete cascade,
  created_at timestamp with time zone default now(),
  primary key (user_id, recipe_id)
);

-- Enable RLS for recipe_likes
alter table public.recipe_likes enable row level security;

-- Create policies for recipe_likes
create policy "Likes are viewable by everyone" on public.recipe_likes
  for select using (true);

create policy "Users can create their own likes" on public.recipe_likes
  for insert with check (auth.uid() = user_id);

create policy "Users can delete their own likes" on public.recipe_likes
  for delete using (auth.uid() = user_id);

-- Create function to handle new user signup
create or replace function public.handle_new_user()
returns trigger language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, username, name, bio, avatar_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'username', split_part(new.email, '@', 1)),
    coalesce(new.raw_user_meta_data ->> 'name', split_part(new.email, '@', 1)),
    coalesce(new.raw_user_meta_data ->> 'bio', ''),
    coalesce(new.raw_user_meta_data ->> 'avatar_url', '')
  );
  return new;
end;
$$;

-- Create trigger for automatic profile creation
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Create function to update updated_at timestamp
create or replace function public.handle_updated_at()
returns trigger language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Create trigger for recipes updated_at
drop trigger if exists recipes_updated_at on public.recipes;
create trigger recipes_updated_at
  before update on public.recipes
  for each row execute procedure public.handle_updated_at();

-- Create trigger for plans updated_at
drop trigger if exists plans_updated_at on public.plans;
create trigger plans_updated_at
  before update on public.plans
  for each row execute procedure public.handle_updated_at();

-- Create indexes for better performance
create index if not exists idx_recipes_user_id on public.recipes(user_id);
create index if not exists idx_recipes_is_public on public.recipes(is_public);
create index if not exists idx_recipes_created_at on public.recipes(created_at desc);
create index if not exists idx_comments_recipe_id on public.comments(recipe_id);
create index if not exists idx_comments_user_id on public.comments(user_id);
create index if not exists idx_user_follows_follower on public.user_follows(follower_id);
create index if not exists idx_user_follows_followed on public.user_follows(followed_id);
create index if not exists idx_recipe_likes_recipe on public.recipe_likes(recipe_id);
create index if not exists idx_recipe_likes_user on public.recipe_likes(user_id);
create index if not exists idx_profiles_username on public.profiles(username);

-- Grant necessary permissions
grant usage on schema public to anon, authenticated;
grant all on all tables in schema public to anon, authenticated;
grant all on all sequences in schema public to anon, authenticated;

-- Create a view for recipe details with user info and counts
create or replace view public.recipe_details as
select 
  r.*,
  p.username,
  p.name as user_name,
  p.avatar_url as user_avatar,
  coalesce(like_counts.like_count, 0) as like_count,
  coalesce(comment_counts.comment_count, 0) as comment_count
from public.recipes r
join public.profiles p on r.user_id = p.id
left join (
  select recipe_id, count(*) as like_count
  from public.recipe_likes
  group by recipe_id
) like_counts on r.id = like_counts.recipe_id
left join (
  select recipe_id, count(*) as comment_count
  from public.comments
  group by recipe_id
) comment_counts on r.id = comment_counts.recipe_id;

-- Create a view for user stats
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
  select followed_id, count(*) as follower_count
  from public.user_follows
  group by followed_id
) follower_counts on p.id = follower_counts.followed_id
left join (
  select follower_id, count(*) as following_count
  from public.user_follows
  group by follower_id
) following_counts on p.id = following_counts.follower_id;

-- Create function to get user's feed (recipes from followed users)
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
  join public.user_follows uf on rd.user_id = uf.followed_id
  where uf.follower_id = user_id
    and rd.is_public = true
  order by rd.created_at desc
  limit page_limit
  offset page_offset;
$$;

-- Add some sample data (optional - for testing)
-- This will be handled by the application when users sign up