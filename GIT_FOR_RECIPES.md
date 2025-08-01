# Git for Recipes - Implementation Documentation

## Overview

This document describes the comprehensive Git-like version control system implemented for NuestrasRecetas.club, allowing users to fork, branch, commit, and track changes to recipes in a manner similar to Git repositories.

## 🏗️ Architecture

### Database Schema

The system adds several new tables to support Git-like functionality:

#### 1. Recipe Versions (Commits)
```sql
recipe_versions (
    id UUID PRIMARY KEY,
    recipe_id INTEGER REFERENCES recipes(id),
    version_number INTEGER,
    commit_message TEXT,
    author_id UUID REFERENCES profiles(id),
    parent_version_id UUID REFERENCES recipe_versions(id),
    changes_json JSONB,  -- What changed
    snapshot_json JSONB, -- Full recipe state
    created_at TIMESTAMP
)
```

#### 2. Recipe Branches
```sql
recipe_branches (
    id UUID PRIMARY KEY,
    recipe_id INTEGER REFERENCES recipes(id),
    branch_name VARCHAR(100),
    description TEXT,
    created_by UUID REFERENCES profiles(id),
    is_default BOOLEAN,
    created_at TIMESTAMP
)
```

#### 3. Recipe Contributors
```sql
recipe_contributors (
    id UUID PRIMARY KEY,
    recipe_id INTEGER REFERENCES recipes(id),
    contributor_id UUID REFERENCES profiles(id),
    contribution_type VARCHAR(50), -- creator, editor, forker, collaborator
    commit_count INTEGER,
    first_contributed_at TIMESTAMP,
    last_contributed_at TIMESTAMP
)
```

#### 4. Enhanced Recipe Forks
```sql
recipe_forks (
    -- Existing fields plus:
    branch_name VARCHAR(100),
    base_version_id UUID REFERENCES recipe_versions(id),
    fork_reason TEXT
)
```

#### 5. Enhanced Recipes Table
```sql
recipes (
    -- Existing fields plus:
    original_recipe_id INTEGER REFERENCES recipes(id),
    current_branch_id UUID REFERENCES recipe_branches(id),
    fork_count INTEGER DEFAULT 0,
    star_count INTEGER DEFAULT 0,
    version_count INTEGER DEFAULT 0,
    is_fork BOOLEAN DEFAULT false
)
```

## 🚀 API Endpoints

### Recipe History & Versioning

#### `GET /api/recipes/{id}/history`
Get full commit history of a recipe
```json
{
  "commits": [
    {
      "version": "v1.2",
      "version_id": "uuid",
      "message": "Added gluten-free flour option",
      "author": {
        "id": "uuid",
        "name": "Maria Garcia",
        "username": "maria_chef",
        "avatar_url": "..."
      },
      "date": "2025-01-01T10:00:00Z",
      "changes": {
        "ingredients": true,
        "servings": {"from": 4, "to": 6}
      }
    }
  ]
}
```

#### `POST /api/recipes/{id}/commit`
Create a new version (commit) for a recipe
```json
// Request
{
  "message": "Updated cooking instructions",
  "changes": {
    "steps": true,
    "cook_time": {"from": 30, "to": 45}
  },
  "auto_commit": true
}

// Response
{
  "ok": true,
  "message": "Changes committed successfully!",
  "version_id": "uuid"
}
```

### Recipe Branching

#### `GET /api/recipes/{id}/branches`
Get all branches for a recipe
```json
{
  "branches": [
    {
      "id": "uuid",
      "name": "main",
      "description": "Main recipe branch",
      "is_default": true,
      "creator": {
        "name": "John Chef",
        "username": "johnchef",
        "avatar_url": "..."
      },
      "created_at": "2025-01-01T10:00:00Z"
    },
    {
      "id": "uuid",
      "name": "gluten-free-version",
      "description": "Gluten-free adaptation",
      "is_default": false,
      "creator": {...},
      "created_at": "2025-01-15T14:30:00Z"
    }
  ]
}
```

#### `POST /api/recipes/{id}/branch`
Create a new branch (variation) for a recipe
```json
// Request
{
  "name": "spicy-version",
  "description": "Spicy adaptation with jalapeños"
}

// Response
{
  "ok": true,
  "message": "Branch 'spicy-version' created successfully!",
  "branch": {
    "id": "uuid",
    "name": "spicy-version",
    "description": "Spicy adaptation with jalapeños"
  }
}
```

### Enhanced Forking

#### `POST /api/recipes/{id}/fork`
Fork a recipe with Git-like tracking
```json
// Request
{
  "fork_reason": "Want to make a vegan version",
  "branch_name": "main",
  "is_public": true
}

// Response
{
  "ok": true,
  "message": "Recipe forked successfully! 🍴",
  "forked_recipe_id": 123
}
```

#### `GET /api/recipes/{id}/forks`
Get all forks with lineage tracking
```json
{
  "forks": [
    {
      "id": "uuid",
      "recipe_id": 124,
      "title": "Vegan Chocolate Cake (Fork)",
      "forked_by": {
        "id": "uuid",
        "name": "Alice Green",
        "username": "alicegreen"
      },
      "fork_depth": 1,
      "created_at": "2025-01-10T12:00:00Z"
    }
  ]
}
```

### Contributors & Attribution

#### `GET /api/recipes/{id}/contributors`
Get all contributors to a recipe
```json
{
  "contributors": [
    {
      "id": "uuid",
      "name": "John Chef",
      "username": "johnchef",
      "avatar_url": "...",
      "contribution_type": "creator",
      "commit_count": 5,
      "first_contributed_at": "2025-01-01T10:00:00Z",
      "last_contributed_at": "2025-01-20T15:30:00Z"
    },
    {
      "id": "uuid",
      "name": "Maria Helper",
      "username": "mariahelper",
      "contribution_type": "editor",
      "commit_count": 2,
      "first_contributed_at": "2025-01-05T14:00:00Z",
      "last_contributed_at": "2025-01-15T09:45:00Z"
    }
  ]
}
```

### Repository-Style Interface

#### `GET /api/recipes/{id}/stats`
Get Git-style statistics for a recipe
```json
{
  "recipe_id": 123,
  "title": "Chocolate Cake",
  "is_fork": false,
  "original_recipe_id": null,
  "stats": {
    "forks": 5,
    "stars": 23,
    "versions": 8,
    "contributors": 3,
    "branches": 2
  },
  "latest_commit": {
    "version": "v8",
    "message": "Fixed baking temperature",
    "author": {
      "name": "John Chef",
      "username": "johnchef",
      "avatar_url": "..."
    },
    "date": "2025-01-20T15:30:00Z"
  },
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-20T15:30:00Z"
}
```

#### `GET /api/recipes/{id}/network`
Get fork network graph
```json
{
  "root": {
    "id": 123,
    "title": "Original Chocolate Cake",
    "owner": "johnchef"
  },
  "nodes": [
    {
      "id": 124,
      "title": "Vegan Chocolate Cake",
      "owner": "alicegreen",
      "depth": 1,
      "created_at": "2025-01-10T12:00:00Z"
    }
  ],
  "edges": [
    {
      "from": 123,
      "to": 124,
      "type": "fork"
    }
  ]
}
```

#### `GET /api/recipes/{id}/compare/{other_id}`
Compare two recipes (like GitHub compare)
```json
{
  "base_recipe": {
    "id": 123,
    "title": "Original Chocolate Cake"
  },
  "compare_recipe": {
    "id": 124,
    "title": "Vegan Chocolate Cake"
  },
  "differences": {
    "title": {
      "base": "Original Chocolate Cake",
      "compare": "Vegan Chocolate Cake"
    },
    "ingredients": {
      "base_count": 8,
      "compare_count": 9,
      "added": [],
      "removed": [],
      "modified": []
    },
    "servings": {
      "base": 8,
      "compare": 6
    }
  },
  "has_changes": true
}
```

## 🔄 Automatic Version Tracking

### Recipe Updates
When a recipe is updated via `PUT /api/recipe/{id}`, the system automatically:

1. **Detects Changes**: Compares old vs new recipe data
2. **Creates Version**: Automatically commits changes if `auto_commit: true`
3. **Updates Contributors**: Increments commit count for the author
4. **Stores Snapshot**: Keeps full recipe state at each version

### Forking Process
When a recipe is forked:

1. **Creates Fork**: New recipe with `is_fork: true`
2. **Establishes Lineage**: Links to original via `original_recipe_id`
3. **Initial Commit**: Creates v1 with "Initial fork" message
4. **Branch Creation**: Sets up main branch
5. **Attribution**: Adds forker to contributors

## 🛡️ Security & Permissions

### Row Level Security (RLS)
All new tables have RLS enabled with appropriate policies:

- **Recipe Versions**: Viewable by everyone, creatable by recipe owners
- **Recipe Branches**: Viewable by everyone, manageable by recipe owners
- **Recipe Contributors**: Viewable by everyone, auto-managed by system
- **Recipe Merge Requests**: Viewable by everyone, manageable by owners

### Access Control
- Users can only create versions for their own recipes
- Users can only create branches for their own recipes
- Fork relationships are public for discovery
- Version history is public for transparency

## 🧪 Testing

### Test Script
A test script is provided at `test_git_features.py`:

```bash
python test_git_features.py
```

### Manual Testing Steps

1. **Apply Migration**:
   ```sql
   -- Run supabase/migrations/005_git_for_recipes.sql
   ```

2. **Create Recipe**: Standard recipe creation now includes version tracking

3. **Fork Recipe**:
   ```bash
   curl -X POST /api/recipes/1/fork \
     -H "Content-Type: application/json" \
     -d '{"fork_reason": "Testing fork"}'
   ```

4. **View History**:
   ```bash
   curl /api/recipes/1/history
   ```

5. **Create Branch**:
   ```bash
   curl -X POST /api/recipes/1/branch \
     -H "Content-Type: application/json" \
     -d '{"name": "test-branch", "description": "Test branch"}'
   ```

## 🚀 Frontend Integration

### Repository-Style Dashboard
The frontend can now display:

- **Recipe Stats**: Fork count, star count, version count
- **Commit History**: Timeline of all changes with authors
- **Fork Network**: Visual graph of all forks and their relationships
- **Branch Selector**: Switch between different recipe variations
- **Contributor List**: All users who have contributed to the recipe

### GitHub-Style Interface Elements
- Commit messages and history
- Fork button with lineage tracking
- Branch creation and switching
- Contributor attribution
- Version comparison tools

## 📈 Future Enhancements

### Merge Requests (Pull Requests)
- Allow users to propose changes to original recipes
- Review system for recipe owners
- Merge conflict resolution for recipe changes

### Advanced Diffing
- Ingredient-level change tracking
- Step-by-step modification history
- Visual diff display for recipe changes

### Collaboration Features
- Recipe co-ownership
- Permission levels (read, write, admin)
- Team recipe development

## 🎯 Success Criteria Met

✅ **Recipe Forking**: Full Git-like fork relationships with lineage tracking  
✅ **Version History**: Complete commit-style change tracking with messages  
✅ **Branching System**: Support for recipe variations and experimental branches  
✅ **Attribution System**: Full contributor tracking with commit counts  
✅ **Repository Interface**: GitHub-style stats, network graphs, and comparison tools  
✅ **API Endpoints**: Comprehensive REST API supporting all Git-like operations  
✅ **Database Schema**: Robust schema supporting version control requirements  
✅ **Security**: Proper RLS policies and access control  

The Git for Recipes system is now fully implemented and ready for frontend integration!