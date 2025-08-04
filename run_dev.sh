#!/bin/bash
# NuestrasRecetas Development Environment Launcher
# This script kills existing processes and starts a fresh development environment

echo "🚀 NuestrasRecetas Development Environment Setup"
echo "=============================================="

# Kill existing processes
echo "🔪 Killing existing processes..."
pkill -f "python.*app.py" 2>/dev/null || true
pkill -f "flask run" 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Check if Supabase is needed
echo "📦 Checking Supabase status..."
if command -v supabase &> /dev/null; then
    # Stop and restart Supabase
    echo "🛑 Stopping Supabase..."
    supabase stop 2>/dev/null || true
    sleep 2
    
    # Only start if we're using local Supabase
    if [ -z "$SUPABASE_URL" ] || [[ "$SUPABASE_URL" == *"localhost"* ]]; then
        echo "🚀 Starting local Supabase..."
        supabase start
    else
        echo "✅ Using remote Supabase: $SUPABASE_URL"
    fi
else
    echo "ℹ️  Supabase CLI not found, using remote instance"
fi

# Set development environment variables
echo "🔧 Setting development environment..."
export FLASK_ENV=development
export FLASK_DEBUG=1
export DEV_MODE=true

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt 2>/dev/null || {
    echo "⚠️  No requirements.txt found, installing core dependencies..."
    pip install -q flask flask-cors supabase python-dotenv sentry-sdk
}

# Clear Flask cache
echo "🧹 Clearing Flask cache..."
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true

# Start Flask application
echo "🌟 Starting Flask application..."
echo "=============================================="
echo "📍 Access the application at: http://localhost:8000"
echo "📧 Dev login: dev@test.com / dev123"
echo "📧 Dev login 2: dev2@test.com / dev456"
echo "🛑 Press Ctrl+C to stop"
echo "=============================================="

# Run Flask with auto-reload
python3 app.py