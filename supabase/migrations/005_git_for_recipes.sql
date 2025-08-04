-- Migration: Git for Recipes - Version Control System
-- Created: 2025-08-01
-- Description: Comprehensive Git-like version control system for recipes

-- ================================================
-- Recipe Versions (Commits)
-- ================================================
CREATE TABLE IF NOT EXISTS public.recipe_versions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    commit_message TEXT NOT NULL,
    author_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    parent_version_id UUID REFERENCES public.recipe_versions(id) ON DELETE SET NULL,
    changes_json JSONB NOT NULL DEFAULT '{}', -- Stores what changed (diff)
    snapshot_json JSONB NOT NULL DEFAULT '{}', -- Full recipe state at this version
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure version numbers are sequential per recipe
    UNIQUE(recipe_id, version_number)
);

-- ================================================
-- Recipe Branches
-- ================================================
CREATE TABLE IF NOT EXISTS public.recipe_branches (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    branch_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    parent_branch_id UUID REFERENCES public.recipe_branches(id) ON DELETE SET NULL,
    base_version_id UUID REFERENCES public.recipe_versions(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure branch names are unique per recipe
    UNIQUE(recipe_id, branch_name)
);

-- ================================================
-- Recipe Contributors
-- ================================================
CREATE TABLE IF NOT EXISTS public.recipe_contributors (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    contribution_type VARCHAR(50) DEFAULT 'editor' CHECK (contribution_type IN ('creator', 'editor', 'forker', 'collaborator')),
    first_contributed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_contributed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    commit_count INTEGER DEFAULT 0,
    
    -- Ensure each user is only listed once per recipe
    UNIQUE(recipe_id, contributor_id)
);

-- ================================================
-- Enhanced Recipe Forks (Update existing table)
-- ================================================
ALTER TABLE public.recipe_forks 
ADD COLUMN IF NOT EXISTS branch_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS base_version_id UUID REFERENCES public.recipe_versions(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS fork_reason TEXT;

-- ================================================
-- Recipe Merge Requests (Pull Requests)
-- ================================================
CREATE TABLE IF NOT EXISTS public.recipe_merge_requests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source_recipe_id INTEGER NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    target_recipe_id INTEGER NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    source_branch_id UUID REFERENCES public.recipe_branches(id) ON DELETE SET NULL,
    target_branch_id UUID REFERENCES public.recipe_branches(id) ON DELETE SET NULL,
    created_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'merged', 'closed', 'rejected')),
    merged_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    merged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================================
-- Add Git-related fields to recipes table
-- ================================================
ALTER TABLE public.recipes 
ADD COLUMN IF NOT EXISTS original_recipe_id INTEGER REFERENCES public.recipes(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS current_branch_id UUID REFERENCES public.recipe_branches(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS fork_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS star_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS version_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_fork BOOLEAN DEFAULT false;

-- ================================================
-- Indexes for Performance
-- ================================================
CREATE INDEX IF NOT EXISTS idx_recipe_versions_recipe ON public.recipe_versions(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_versions_author ON public.recipe_versions(author_id);
CREATE INDEX IF NOT EXISTS idx_recipe_versions_created ON public.recipe_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recipe_versions_parent ON public.recipe_versions(parent_version_id);

CREATE INDEX IF NOT EXISTS idx_recipe_branches_recipe ON public.recipe_branches(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_branches_creator ON public.recipe_branches(created_by);
CREATE INDEX IF NOT EXISTS idx_recipe_branches_active ON public.recipe_branches(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_recipe_contributors_recipe ON public.recipe_contributors(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_contributors_user ON public.recipe_contributors(contributor_id);
CREATE INDEX IF NOT EXISTS idx_recipe_contributors_type ON public.recipe_contributors(contribution_type);

CREATE INDEX IF NOT EXISTS idx_recipe_merge_requests_source ON public.recipe_merge_requests(source_recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_merge_requests_target ON public.recipe_merge_requests(target_recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_merge_requests_creator ON public.recipe_merge_requests(created_by);
CREATE INDEX IF NOT EXISTS idx_recipe_merge_requests_status ON public.recipe_merge_requests(status);

-- ================================================
-- Helper Functions
-- ================================================

-- Function to create a new version (commit) for a recipe
CREATE OR REPLACE FUNCTION create_recipe_version(
    p_recipe_id INTEGER,
    p_author_id UUID,
    p_commit_message TEXT,
    p_changes_json JSONB,
    p_snapshot_json JSONB
) RETURNS UUID AS $$
DECLARE
    v_version_number INTEGER;
    v_version_id UUID;
BEGIN
    -- Get the next version number
    SELECT COALESCE(MAX(version_number), 0) + 1 
    INTO v_version_number
    FROM public.recipe_versions
    WHERE recipe_id = p_recipe_id;
    
    -- Create the version
    INSERT INTO public.recipe_versions (
        recipe_id, version_number, commit_message, 
        author_id, changes_json, snapshot_json
    ) VALUES (
        p_recipe_id, v_version_number, p_commit_message,
        p_author_id, p_changes_json, p_snapshot_json
    ) RETURNING id INTO v_version_id;
    
    -- Update recipe version count
    UPDATE public.recipes 
    SET version_count = v_version_number
    WHERE id = p_recipe_id;
    
    -- Update contributor record
    INSERT INTO public.recipe_contributors (
        recipe_id, contributor_id, contribution_type, commit_count
    ) VALUES (
        p_recipe_id, p_author_id, 'editor', 1
    )
    ON CONFLICT (recipe_id, contributor_id) 
    DO UPDATE SET 
        commit_count = recipe_contributors.commit_count + 1,
        last_contributed_at = NOW();
    
    RETURN v_version_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get recipe history with author info
CREATE OR REPLACE FUNCTION get_recipe_history(
    p_recipe_id INTEGER,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
) RETURNS TABLE(
    version_id UUID,
    version_number INTEGER,
    commit_message TEXT,
    author_id UUID,
    author_name TEXT,
    author_username TEXT,
    author_avatar TEXT,
    changes_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rv.id,
        rv.version_number,
        rv.commit_message,
        rv.author_id,
        p.name,
        p.username,
        p.avatar_url,
        rv.changes_json,
        rv.created_at
    FROM public.recipe_versions rv
    JOIN public.profiles p ON rv.author_id = p.id
    WHERE rv.recipe_id = p_recipe_id
    ORDER BY rv.version_number DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get all forks of a recipe with lineage
CREATE OR REPLACE FUNCTION get_recipe_fork_tree(
    p_recipe_id INTEGER
) RETURNS TABLE(
    fork_id UUID,
    forked_recipe_id INTEGER,
    forked_recipe_title TEXT,
    forked_by_id UUID,
    forked_by_name TEXT,
    forked_by_username TEXT,
    fork_depth INTEGER,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
WITH RECURSIVE fork_tree AS (
    -- Base case: direct forks
    SELECT 
        rf.id,
        rf.forked_recipe_id,
        r.title,
        rf.forked_by,
        p.name,
        p.username,
        1 as depth,
        rf.created_at
    FROM public.recipe_forks rf
    JOIN public.recipes r ON rf.forked_recipe_id = r.id
    JOIN public.profiles p ON rf.forked_by = p.id
    WHERE rf.original_recipe_id = p_recipe_id
    
    UNION ALL
    
    -- Recursive case: forks of forks
    SELECT 
        rf.id,
        rf.forked_recipe_id,
        r.title,
        rf.forked_by,
        p.name,
        p.username,
        ft.depth + 1,
        rf.created_at
    FROM public.recipe_forks rf
    JOIN fork_tree ft ON rf.original_recipe_id = ft.forked_recipe_id
    JOIN public.recipes r ON rf.forked_recipe_id = r.id
    JOIN public.profiles p ON rf.forked_by = p.id
)
SELECT * FROM fork_tree
ORDER BY depth, created_at DESC;
$$ LANGUAGE sql SECURITY DEFINER;

-- ================================================
-- Row Level Security Policies
-- ================================================

-- Recipe Versions
ALTER TABLE public.recipe_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Recipe versions are viewable by everyone"
ON public.recipe_versions FOR SELECT
USING (true);

CREATE POLICY "Users can create versions for their recipes"
ON public.recipe_versions FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.recipes r
        WHERE r.id = recipe_id AND r.user_id = auth.uid()
    )
);

-- Recipe Branches
ALTER TABLE public.recipe_branches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Recipe branches are viewable by everyone"
ON public.recipe_branches FOR SELECT
USING (true);

CREATE POLICY "Users can create branches for their recipes"
ON public.recipe_branches FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.recipes r
        WHERE r.id = recipe_id AND r.user_id = auth.uid()
    )
);

CREATE POLICY "Users can update their own branches"
ON public.recipe_branches FOR UPDATE
USING (created_by = auth.uid());

-- Recipe Contributors
ALTER TABLE public.recipe_contributors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Recipe contributors are viewable by everyone"
ON public.recipe_contributors FOR SELECT
USING (true);

-- Recipe Merge Requests
ALTER TABLE public.recipe_merge_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Merge requests are viewable by everyone"
ON public.recipe_merge_requests FOR SELECT
USING (true);

CREATE POLICY "Users can create merge requests"
ON public.recipe_merge_requests FOR INSERT
WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Recipe owners can update merge requests"
ON public.recipe_merge_requests FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.recipes r
        WHERE r.id = target_recipe_id AND r.user_id = auth.uid()
    )
);

-- ================================================
-- Triggers
-- ================================================

-- Trigger to update recipe fork count
CREATE OR REPLACE FUNCTION update_recipe_fork_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.recipes 
        SET fork_count = fork_count + 1
        WHERE id = NEW.original_recipe_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.recipes 
        SET fork_count = fork_count - 1
        WHERE id = OLD.original_recipe_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_fork_count_trigger
AFTER INSERT OR DELETE ON public.recipe_forks
FOR EACH ROW EXECUTE FUNCTION update_recipe_fork_count();

-- Trigger to set recipe as fork when created via forking
CREATE OR REPLACE FUNCTION mark_recipe_as_fork()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.recipes 
    SET is_fork = true,
        original_recipe_id = NEW.original_recipe_id
    WHERE id = NEW.forked_recipe_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER mark_as_fork_trigger
AFTER INSERT ON public.recipe_forks
FOR EACH ROW EXECUTE FUNCTION mark_recipe_as_fork();

-- ================================================
-- Create default main branch for existing recipes
-- ================================================
INSERT INTO public.recipe_branches (recipe_id, branch_name, description, created_by, is_default)
SELECT 
    r.id,
    'main',
    'Main recipe branch',
    r.user_id,
    true
FROM public.recipes r
LEFT JOIN public.recipe_branches b ON r.id = b.recipe_id AND b.branch_name = 'main'
WHERE b.id IS NULL;

-- Update recipes to reference their main branch
UPDATE public.recipes r
SET current_branch_id = b.id
FROM public.recipe_branches b
WHERE r.id = b.recipe_id 
AND b.branch_name = 'main'
AND r.current_branch_id IS NULL;

-- ================================================
-- Grant Permissions
-- ================================================
GRANT ALL ON public.recipe_versions TO authenticated;
GRANT ALL ON public.recipe_branches TO authenticated;
GRANT ALL ON public.recipe_contributors TO authenticated;
GRANT ALL ON public.recipe_merge_requests TO authenticated;
GRANT EXECUTE ON FUNCTION create_recipe_version(INTEGER, UUID, TEXT, JSONB, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION get_recipe_history(INTEGER, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_recipe_fork_tree(INTEGER) TO authenticated;