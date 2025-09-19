#!/bin/bash

set -e  # Exit on any error

echo "🚀 Starting KDF Response Harvesting Workflow"
echo "============================================="

# Navigate to workspace root if needed
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📁 Changing to workspace root: $WORKSPACE_ROOT"
cd "$WORKSPACE_ROOT"

# Check if we're in the correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Could not find docker-compose.yml in workspace root"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating Python virtual environment..."
source utils/py/.venv/bin/activate

# Set KDF branch
export KDF_BRANCH="dev"

# Start KDF Docker services
echo "🐳 Starting KDF Docker services..."
docker compose up kdf-native-hd kdf-native-nonhd -d

# Wait for services to be ready
echo "⏳ Waiting for KDF services to be ready..."
sleep 10

# Clean slate - disable all enabled coins for fresh start
echo "🧹 Preparing clean slate (disabling all enabled coins)..."
python utils/py/clean_slate.py

# Generate Postman collections
echo "📋 Generating Postman collections..."
python utils/py/generate_postman.py --all

# Run comprehensive response collection (includes address collection)
echo "🔍 Collecting responses with sequence-based processing..."
cd utils/py && python lib/managers/sequence_responses_manager.py --update-files && cd ../..
echo "🏦 Address collection integrated into sequence-based response harvesting"

# Clean up old reports in postman/reports/ (if they exist)
echo "🧹 Cleaning up old Newman reports..."
if [ -d "postman/reports" ]; then
    find postman/reports -name "postman_test_results_*.json" -type f | sort -r | tail -n +3 | xargs -r rm -f
    find postman/reports -name "test_summary_*.json" -type f | sort -r | tail -n +3 | xargs -r rm -f
    echo "   Cleaned up old reports, keeping 2 most recent"
fi

# Stop KDF services
echo "🛑 Stopping KDF Docker services..."
docker compose down

echo ""
echo "✅ Response harvesting completed successfully!"
echo "📊 Check these directories for results:"
echo "   - postman/generated/reports/ (unified response manager output)"
echo "   - postman/reports/ (Newman test results)"
echo "   - src/data/responses/ (updated response files)"
