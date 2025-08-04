# Development Workflow

This guide explains how to work on NuestrasRecetas.club locally before deploying to production.

## Quick Start

### 1. Start Development Environment
```bash
# Run the development server
./run-dev.sh
```

### 2. Make Changes
- Edit files in `templates/`, `static/`, `app.py`, etc.
- Changes are automatically reflected (volume mounts)
- No need to rebuild for template/static changes

### 3. Test Locally
- Visit `http://localhost:8000`
- Test all functionality before deploying

### 4. Deploy to Production
```bash
# Switch to main branch
git checkout main

# Merge your dev changes
git merge dev

# Push to trigger auto-deployment
git push origin main
```

## Development vs Production

### Development Environment
- **URL**: `http://localhost:8000` 
- **Hot Reload**: Template/static changes reflect immediately
- **Debug Mode**: Detailed error messages
- **Docker Compose**: `docker-compose.dev.yml`
- **Command**: Flask dev server (`python app.py`)

### Production Environment  
- **URL**: `https://nuestrasrecetas.club`
- **Optimized**: Gunicorn + Nginx reverse proxy
- **Security**: Error details hidden from users
- **Docker Compose**: `docker-compose.yml`
- **Auto-Deploy**: GitHub Actions on `main` branch push

## Branch Strategy

### `dev` Branch
- **Purpose**: Development and testing
- **Safety**: Test locally before production
- **Workflow**: Make changes → Test → Merge to main

### `main` Branch  
- **Purpose**: Production releases
- **Auto-Deploy**: Pushes trigger deployment
- **Stability**: Only merge tested code

## Common Commands

### Development
```bash
# Start dev environment
./run-dev.sh

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Stop dev environment
docker compose -f docker-compose.dev.yml down

# Rebuild if dependencies changed
docker compose -f docker-compose.dev.yml build --no-cache
```

### Git Workflow
```bash
# Start working on feature
git checkout dev
git pull origin dev

# Make changes and test
# ... edit files ...
./run-dev.sh

# Commit changes
git add .
git commit -m "feat: add new functionality"

# Deploy to production when ready
git checkout main
git merge dev
git push origin main
```

## Environment Setup

### Required Files
- `.env` - Environment variables (copy from `.env.example`)
- Supabase credentials must be configured

### Database Tables
Make sure these tables exist in Supabase:
- `profiles` - User profiles
- `recipes` - Recipe data  
- `recipe_forks` - Fork relationships
- `recipe_likes` - Star/like data
- `user_posts` - Activity feed posts

## Testing Checklist

Before deploying to production, test:

### ✅ Basic Functionality
- [ ] User login/logout
- [ ] Create new recipe
- [ ] Edit existing recipe  
- [ ] Delete recipe
- [ ] View other user profiles

### ✅ Git-for-Recipes Features
- [ ] Fork recipe functionality
- [ ] Star/unstar recipes
- [ ] Dashboard statistics load properly
- [ ] Repository tabs work (My Recipes, Starred, Forks)
- [ ] Activity feed displays correctly

### ✅ UI/UX  
- [ ] Mobile responsive design
- [ ] All buttons functional
- [ ] No JavaScript console errors
- [ ] Loading states work properly
- [ ] Error messages display correctly

## Troubleshooting

### Port Already in Use
```bash
# Stop existing containers
docker compose -f docker-compose.dev.yml down
docker compose down
```

### Database Connection Issues
- Check `.env` file has correct Supabase credentials
- Verify Supabase project is active
- Check network connectivity

### Container Build Issues
```bash
# Clean rebuild
docker compose -f docker-compose.dev.yml down
docker system prune -f  
docker compose -f docker-compose.dev.yml build --no-cache
```

This workflow ensures you can develop safely without breaking production! 🚀