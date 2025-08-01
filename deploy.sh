#!/bin/bash

# Family Recipe Planner - Deployment Script
# Usage: ./deploy.sh [environment]

set -e  # Exit on any error

ENVIRONMENT=${1:-production}
echo "🚀 Deploying Family Recipe Planner ($ENVIRONMENT)..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📝 Creating .env file from .env.example"
        cp .env.example .env
        echo "⚠️  Please edit .env file with your configuration before continuing."
        echo "   Press Enter to continue after editing .env..."
        read
    else
        echo "⚠️  No .env file found. Creating basic configuration..."
        cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite:///data/gourmet_planner_web.sqlite
PORT=8000
EOF
    fi
fi

# Build and start the application
echo "🐳 Building Docker image..."
docker-compose build --no-cache

echo "🗄️  Initializing database..."
if docker-compose run --rm app python database.py; then
    echo "✅ Database initialized successfully"
else
    echo "⚠️  Database initialization failed, but continuing..."
    echo "   The app will create tables automatically on first run."
fi

echo "🚀 Starting application..."
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f docker-compose.yml --profile with-nginx up -d
    echo "✅ Application started with Nginx reverse proxy"
    echo "🌐 Access your app at: http://localhost"
else
    docker-compose up -d app
    echo "✅ Application started in development mode"
    echo "🌐 Access your app at: http://localhost:8000"
fi

echo ""
echo "📊 Container status:"
docker-compose ps

echo ""
echo "📝 Deployment complete!"
echo ""
echo "📚 Next steps:"
echo "1. Visit your application in a web browser"
echo "2. Start adding your family recipes"
echo "3. Plan your weekly meals"
echo "4. Generate grocery lists"
echo ""
echo "🔧 Management commands:"
echo "  ./deploy.sh logs    - View application logs"
echo "  ./deploy.sh stop    - Stop the application"
echo "  ./deploy.sh restart - Restart the application"
echo "  ./deploy.sh backup  - Backup your data"

# Handle management commands
case "$ENVIRONMENT" in
    logs)
        docker-compose logs -f
        ;;
    stop)
        docker-compose down
        echo "🛑 Application stopped"
        ;;
    restart)
        docker-compose down
        docker-compose up -d
        echo "🔄 Application restarted"
        ;;
    backup)
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp -r data "$BACKUP_DIR/"
        cp .env "$BACKUP_DIR/"
        echo "💾 Backup created in $BACKUP_DIR"
        ;;
esac