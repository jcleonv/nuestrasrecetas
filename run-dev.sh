#!/bin/bash

# Development runner script
echo "🚀 Starting NuestrasRecetas.club in development mode..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Copying from example..."
    cp .env.example .env
    echo "✏️  Please edit .env with your Supabase credentials"
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose -f docker-compose.dev.yml down

# Build and start development environment
echo "🔨 Building development containers..."
docker compose -f docker-compose.dev.yml build

echo "▶️  Starting development server..."
docker compose -f docker-compose.dev.yml up

echo "🌐 Development server should be available at http://localhost:8000"