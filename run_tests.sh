#!/bin/bash
# NuestrasRecetas Test Runner
# Runs comprehensive tests after starting the dev environment

echo "🧪 NuestrasRecetas Test Suite"
echo "============================="

# Kill existing processes first
echo "🔪 Killing existing processes..."
pkill -f "python.*app.py" 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Create test virtual environment if it doesn't exist
if [ ! -d "test_venv" ]; then
    echo "🐍 Creating test virtual environment..."
    python3 -m venv test_venv
fi

# Activate test virtual environment
echo "🔌 Activating test environment..."
source test_venv/bin/activate

# Install test dependencies
echo "📚 Installing test dependencies..."
pip install -q -r test_requirements.txt

# Start Flask application in background
echo "🚀 Starting Flask application for testing..."
nohup python3 app.py > flask_test.log 2>&1 &
FLASK_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 5

# Check if server is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Server is running"
    
    # Run comprehensive tests
    echo "🧪 Running comprehensive test suite..."
    python3 test_runner_final.py
    TEST_EXIT_CODE=$?
    
    echo ""
    echo "📊 Test Results Summary:"
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo "✅ All tests passed!"
    else
        echo "❌ Some tests failed"
    fi
    
else
    echo "❌ Server failed to start"
    TEST_EXIT_CODE=1
fi

# Cleanup
echo "🧹 Cleaning up..."
kill $FLASK_PID 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

exit $TEST_EXIT_CODE