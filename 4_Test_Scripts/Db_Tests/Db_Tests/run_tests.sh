#!/bin/bash
# Run all tests script for Unix/Linux/Mac

echo "=========================================="
echo "Football Probability Engine - Test Suite"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "test_database_schema.py" ]; then
    echo "Error: Please run this script from the Db_Tests directory"
    exit 1
fi

# Run Python tests
echo "Running Python tests..."
echo "----------------------------------------"
python -m pytest . -v --tb=short

# Check if frontend tests exist
if [ -f "test_frontend_logic.test.ts" ]; then
    echo ""
    echo "Running TypeScript tests..."
    echo "----------------------------------------"
    # Check if vitest is available
    if command -v npx &> /dev/null; then
        npx vitest run test_frontend_logic.test.ts
    else
        echo "⚠ Skipping TypeScript tests (npx not available)"
    fi
fi

echo ""
echo "=========================================="
echo "Tests complete!"
echo "=========================================="

