#!/bin/bash
# Comprehensive test runner for Rumble plugin

set -e

echo "🧪 RUMBLE PLUGIN TEST SUITE"
echo "============================="

# Change to plugin directory
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PLUGIN_DIR"

echo "📁 Plugin directory: $PLUGIN_DIR"
echo ""

# Function to run a test and capture result
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo "🔍 Running $test_name..."
    if eval "$test_command"; then
        echo "✅ $test_name PASSED"
        return 0
    else
        echo "❌ $test_name FAILED"
        return 1
    fi
}

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0

# Container tests
echo "🐳 CONTAINER TESTS"
echo "=================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test "Container Tests" "python tests/test_container.py"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi
echo ""

# Plugin tests (requires Docker environment)
echo "🔌 PLUGIN TESTS"
echo "==============="
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Check if we're in Docker or have proper Python environment
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo "🐳 Docker available, running plugin tests..."
    
    # Try to run in Docker container if main bot is running
    if docker ps --format "table {{.Names}}" | grep -q "simplex-bot"; then
        echo "📦 Running tests in simplex-bot container..."
        if docker exec simplex-bot python -c "
import sys
sys.path.insert(0, '/app')
exec(open('/app/plugins/external/rumble/tests/test_plugin.py').read())
"; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo "✅ Plugin Tests (Docker) PASSED"
        else
            echo "❌ Plugin Tests (Docker) FAILED"
        fi
    else
        echo "📋 simplex-bot container not running, trying local Python..."
        if python tests/test_plugin.py; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo "✅ Plugin Tests (Local) PASSED"
        else
            echo "❌ Plugin Tests (Local) FAILED"
        fi
    fi
else
    echo "⚠️ Docker not available, skipping plugin tests"
fi

echo ""

# Summary
echo "📊 TEST SUMMARY"
echo "==============="
echo "Tests passed: $PASSED_TESTS/$TOTAL_TESTS"

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo "🎉 ALL TESTS PASSED!"
    exit 0
else
    echo "❌ Some tests failed"
    exit 1
fi