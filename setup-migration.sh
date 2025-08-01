#!/bin/bash

# Setup script to apply Supabase migrations on DigitalOcean
echo "🚀 Setting up Supabase CLI and applying migrations..."

# Install Supabase CLI
echo "📦 Installing Supabase CLI..."
curl -sL https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz | tar -xz
sudo mv supabase /usr/local/bin/

# Verify installation
supabase --version

# Source environment variables
source .env

# Extract project reference from Supabase URL
PROJECT_REF=$(echo $SUPABASE_URL | sed 's/https:\/\/\([^.]*\).*/\1/')
echo "📋 Project reference: $PROJECT_REF"

# Link to Supabase project
echo "🔗 Linking to Supabase project..."
echo $SUPABASE_KEY | supabase link --project-ref $PROJECT_REF

# Apply migrations
echo "🔄 Applying database migrations..."
supabase db push

# Check migration status
echo "✅ Checking migration status..."
supabase migration list

echo "🎉 Migration setup complete!"
echo "🌐 Test your groups feature at: http://64.23.143.68/groups"