-- ================================================
-- NuestrasRecetas.club - Community Groups Migration
-- ================================================

-- Create groups table
create table if not exists public.groups (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  description text default '',
  avatar_url text default '',
  is_public boolean default true,
  is_private boolean default false,
  owner_id uuid not null references public.profiles(id) on delete cascade,
  member_count integer default 0,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Create group_members junction table FIRST (needed for policies)
create table if not exists public.group_members (
  group_id uuid not null references public.groups(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text default 'member' check (role in ('owner', 'admin', 'moderator', 'member')),
  joined_at timestamp with time zone default now(),
  primary key (group_id, user_id)
);

-- Enable RLS for both tables
alter table public.groups enable row level security;
alter table public.group_members enable row level security;

-- Create policies for groups
drop policy if exists "Public groups are viewable by everyone" on public.groups;
create policy "Public groups are viewable by everyone" on public.groups
  for select using (is_public = true);

drop policy if exists "Private groups are viewable by members" on public.groups;
create policy "Private groups are viewable by members" on public.groups
  for select using (
    is_private = true and 
    exists (
      select 1 from public.group_members 
      where group_id = id and user_id = auth.uid()
    )
  );

drop policy if exists "Group owners can view their groups" on public.groups;
create policy "Group owners can view their groups" on public.groups
  for select using (owner_id = auth.uid());

drop policy if exists "Users can create groups" on public.groups;
create policy "Users can create groups" on public.groups
  for insert with check (owner_id = auth.uid());

drop policy if exists "Group owners can update their groups" on public.groups;
create policy "Group owners can update their groups" on public.groups
  for update using (owner_id = auth.uid());

drop policy if exists "Group owners can delete their groups" on public.groups;
create policy "Group owners can delete their groups" on public.groups
  for delete using (owner_id = auth.uid());

-- group_members table already created above

-- Create policies for group_members
drop policy if exists "Group memberships are viewable by group members" on public.group_members;
create policy "Group memberships are viewable by group members" on public.group_members
  for select using (
    exists (
      select 1 from public.group_members gm2
      where gm2.group_id = group_id and gm2.user_id = auth.uid()
    )
  );

drop policy if exists "Group owners can manage members" on public.group_members;
create policy "Group owners can manage members" on public.group_members
  for all using (
    exists (
      select 1 from public.groups g
      where g.id = group_id and g.owner_id = auth.uid()
    )
  );

drop policy if exists "Users can join public groups" on public.group_members;
create policy "Users can join public groups" on public.group_members
  for insert with check (
    exists (
      select 1 from public.groups g
      where g.id = group_id and g.is_public = true
    ) and user_id = auth.uid()
  );

drop policy if exists "Users can leave groups" on public.group_members;
create policy "Users can leave groups" on public.group_members
  for delete using (user_id = auth.uid());

-- Create group_posts table for group discussions
create table if not exists public.group_posts (
  id uuid primary key default uuid_generate_v4(),
  group_id uuid not null references public.groups(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  content text not null,
  post_type text default 'discussion' check (post_type in ('discussion', 'recipe', 'announcement')),
  recipe_id integer references public.recipes(id) on delete set null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Enable RLS for group_posts
alter table public.group_posts enable row level security;

-- Create policies for group_posts
drop policy if exists "Group posts are viewable by group members" on public.group_posts;
create policy "Group posts are viewable by group members" on public.group_posts
  for select using (
    exists (
      select 1 from public.group_members gm
      where gm.group_id = group_id and gm.user_id = auth.uid()
    )
  );

drop policy if exists "Group members can create posts" on public.group_posts;
create policy "Group members can create posts" on public.group_posts
  for insert with check (
    exists (
      select 1 from public.group_members gm
      where gm.group_id = group_id and gm.user_id = auth.uid()
    ) and user_id = auth.uid()
  );

drop policy if exists "Users can update their own posts" on public.group_posts;
create policy "Users can update their own posts" on public.group_posts
  for update using (user_id = auth.uid());

drop policy if exists "Users can delete their own posts" on public.group_posts;
create policy "Users can delete their own posts" on public.group_posts
  for delete using (user_id = auth.uid());

-- Create group_post_comments table
create table if not exists public.group_post_comments (
  id uuid primary key default uuid_generate_v4(),
  post_id uuid not null references public.group_posts(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  content text not null,
  created_at timestamp with time zone default now()
);

-- Enable RLS for group_post_comments
alter table public.group_post_comments enable row level security;

-- Create policies for group_post_comments
drop policy if exists "Group post comments are viewable by group members" on public.group_post_comments;
create policy "Group post comments are viewable by group members" on public.group_post_comments
  for select using (
    exists (
      select 1 from public.group_posts gp
      join public.group_members gm on gp.group_id = gm.group_id
      where gp.id = post_id and gm.user_id = auth.uid()
    )
  );

drop policy if exists "Group members can create comments" on public.group_post_comments;
create policy "Group members can create comments" on public.group_post_comments
  for insert with check (
    exists (
      select 1 from public.group_posts gp
      join public.group_members gm on gp.group_id = gm.group_id
      where gp.id = post_id and gm.user_id = auth.uid()
    ) and user_id = auth.uid()
  );

drop policy if exists "Users can update their own comments" on public.group_post_comments;
create policy "Users can update their own comments" on public.group_post_comments
  for update using (user_id = auth.uid());

drop policy if exists "Users can delete their own comments" on public.group_post_comments;
create policy "Users can delete their own comments" on public.group_post_comments
  for delete using (user_id = auth.uid());

-- Add group_id to recipes table for group recipes
alter table public.recipes add column if not exists group_id uuid references public.groups(id) on delete set null;

-- Create indexes for better performance
create index if not exists idx_groups_owner_id on public.groups(owner_id);
create index if not exists idx_groups_is_public on public.groups(is_public);
create index if not exists idx_groups_created_at on public.groups(created_at desc);
create index if not exists idx_group_members_group_id on public.group_members(group_id);
create index if not exists idx_group_members_user_id on public.group_members(user_id);
create index if not exists idx_group_posts_group_id on public.group_posts(group_id);
create index if not exists idx_group_posts_user_id on public.group_posts(user_id);
create index if not exists idx_group_posts_created_at on public.group_posts(created_at desc);
create index if not exists idx_group_post_comments_post_id on public.group_post_comments(post_id);
create index if not exists idx_group_post_comments_user_id on public.group_post_comments(user_id);
create index if not exists idx_recipes_group_id on public.recipes(group_id);

-- Create function to update group member count
create or replace function public.update_group_member_count()
returns trigger language plpgsql
as $$
begin
  if tg_op = 'INSERT' then
    update public.groups 
    set member_count = member_count + 1
    where id = new.group_id;
    return new;
  elsif tg_op = 'DELETE' then
    update public.groups 
    set member_count = member_count - 1
    where id = old.group_id;
    return old;
  end if;
  return null;
end;
$$;

-- Create trigger for group member count
drop trigger if exists update_group_member_count_trigger on public.group_members;
create trigger update_group_member_count_trigger
  after insert or delete on public.group_members
  for each row execute procedure public.update_group_member_count();

-- Create function to handle group updated_at
create or replace function public.handle_group_updated_at()
returns trigger language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Create trigger for groups updated_at
drop trigger if exists groups_updated_at on public.groups;
create trigger groups_updated_at
  before update on public.groups
  for each row execute procedure public.handle_group_updated_at();

-- Create trigger for group_posts updated_at
drop trigger if exists group_posts_updated_at on public.group_posts;
create trigger group_posts_updated_at
  before update on public.group_posts
  for each row execute procedure public.handle_updated_at();

-- Create view for group details with member count
create or replace view public.group_details as
select 
  g.*,
  p.username as owner_username,
  p.name as owner_name,
  p.avatar_url as owner_avatar,
  coalesce(post_counts.post_count, 0) as post_count
from public.groups g
join public.profiles p on g.owner_id = p.id
left join (
  select group_id, count(*) as post_count
  from public.group_posts
  group by group_id
) post_counts on g.id = post_counts.group_id;

-- Create view for group posts with user info
create or replace view public.group_post_details as
select 
  gp.*,
  p.username,
  p.name as user_name,
  p.avatar_url as user_avatar,
  coalesce(comment_counts.comment_count, 0) as comment_count
from public.group_posts gp
join public.profiles p on gp.user_id = p.id
left join (
  select post_id, count(*) as comment_count
  from public.group_post_comments
  group by post_id
) comment_counts on gp.id = comment_counts.post_id;

-- Grant necessary permissions
grant all on public.groups to anon, authenticated;
grant all on public.group_members to anon, authenticated;
grant all on public.group_posts to anon, authenticated;
grant all on public.group_post_comments to anon, authenticated;
grant all on public.group_details to anon, authenticated;
grant all on public.group_post_details to anon, authenticated; 