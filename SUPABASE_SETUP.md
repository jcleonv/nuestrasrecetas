# 🗄️ Supabase Setup Guide

## Quick Setup (2 minutes)

### Option 1: Use the Setup Helper (Recommended)
```bash
python3 setup_supabase.py
```
This script will guide you through getting the correct connection string.

### Option 2: Manual Setup

1. **Go to your Supabase Dashboard**
   - Visit: https://supabase.com/dashboard
   - Select your project: `egyxcuejvorqlwujsdpp`

2. **Get Connection String**
   - Go to: Settings → Database
   - Scroll down to "Connection string"
   - Click the "URI" tab
   - Copy the connection string

3. **Update your .env file**
   Replace the DATABASE_URL line with your connection string:
   ```bash
   DATABASE_URL=postgresql://postgres.egyxcuejvorqlwujsdpp:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

4. **Find Your Password**
   - In Supabase Dashboard → Settings → Database
   - Look for "Database password" or "Reset database password"
   - Replace `[YOUR-PASSWORD]` with the actual password

## Deploy with Supabase

Once you have the correct connection string:

```bash
./deploy.sh
```

## Fallback to SQLite

If Supabase setup is complex, you can start with SQLite:

1. **Comment out Supabase in .env:**
   ```bash
   # SUPABASE_URL=https://egyxcuejvorqlwujsdpp.supabase.co
   # SUPABASE_KEY=your-key
   DATABASE_URL=sqlite:///data/gourmet_planner_web.sqlite
   ```

2. **Deploy:**
   ```bash
   ./deploy.sh
   ```

3. **Migrate to Supabase later** when ready

## Connection String Format

The correct Supabase connection string looks like:
```
postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
```

Where:
- `PROJECT_REF` = egyxcuejvorqlwujsdpp (your project)
- `PASSWORD` = your database password from Supabase dashboard
- `REGION` = us-east-1 (or your region)

## Troubleshooting

### "Network is unreachable"
- Check your connection string format
- Ensure password is correct
- Try resetting database password in Supabase

### "Connection failed"
- Verify you're using the pooler connection (port 6543)
- Check if your IP is whitelisted (Supabase allows all by default)

### Still having issues?
- Fall back to SQLite temporarily
- Check Supabase status page
- Try the direct connection (port 5432) instead of pooler (port 6543)

## Benefits of Supabase vs SQLite

**SQLite (Local)**
- ✅ Simple setup
- ✅ No internet required
- ❌ Single user
- ❌ No backups
- ❌ Local only

**Supabase (Cloud)**
- ✅ Multi-device access
- ✅ Automatic backups
- ✅ Scalable
- ✅ Real-time features
- ❌ Requires internet
- ❌ Slightly more setup

## Recommendation

**Start with SQLite** to test the app, then **migrate to Supabase** when you're ready for production use with your family.