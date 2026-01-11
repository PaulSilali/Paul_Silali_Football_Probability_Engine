#!/bin/bash
# Test Runner Script for Frontend Tests

echo "=========================================="
echo "Football Probability Engine - Test Suite"
echo "=========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

# Navigate to frontend directory
cd "../1_Frontend_Football_Probability_Engine" || exit 1

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Check if backend is running
echo "🔍 Checking if backend is running..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running"
else
    echo "⚠️  Backend is not running. Some tests may fail."
    echo "   Start backend with: cd 2_Backend_Football_Probability_Engine && python run.py"
fi

echo ""
echo "🧪 Running tests..."
echo ""

# Run tests
npm test -- --coverage

echo ""
echo "=========================================="
echo "Test execution complete"
echo "=========================================="

