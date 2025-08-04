#!/bin/bash

# Script to run Flask server and tests concurrently

# Function to cleanup background processes
cleanup() {
    echo "Cleaning up..."
    kill $(jobs -p) 2>/dev/null
    exit
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Activate virtual environment
source test_venv/bin/activate

# Start Flask server in background
echo "🚀 Starting Flask server..."
python app.py &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 5

# Check if server is running
if ! curl -s http://localhost:8000 > /dev/null; then
    echo "❌ Server failed to start"
    exit 1
fi

echo "✅ Server is running"

# Run the tests
echo "🧪 Running production issues test..."
python test_production_issues.py

# Keep script running until user interrupts
echo "✅ Test completed. Press Ctrl+C to stop the server."
wait $SERVER_PID