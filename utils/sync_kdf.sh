#!/bin/bash

# Komodo DeFi Framework Documentation Sync Script

if [ -z "$1" ]; then
    KDF_BRANCH="dev"
else
    KDF_BRANCH=$1
fi

echo "Running sync for KDF branch: $KDF_BRANCH"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the utils directory (where this script should be run from)
cd "$SCRIPT_DIR"

MDX_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Running sync for MDX branch: $MDX_BRANCH"

# Activate Python virtual environment
source py/.venv/bin/activate

echo "==================================================================="
echo "============== 🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀 ============="
echo "============== 🚀 Starting KDF Documentation Sync "
echo "============== 🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀 ============="
echo "==================================================================="
echo "============== 🚀🚀🚀 KDF Branch: $KDF_BRANCH"
echo "============== 🚀🚀🚀 MDX Branch: $MDX_BRANCH"

# Step 0: Show balances
echo "============== 📊 Step 0: Show balances... ==============="
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH balances; then
    echo "❌ Step 0 failed: Show balances"
    exit 1
fi
echo

# Step 1A: Scan KDF Rust Repository
# INPUT: KDF Rust repository
# REPORT: reports/kdf_rust_methods.json
# CONTAINS: All RPC methods found in the Rust codebase, organized by API version (v1/v2)
# PURPOSE: Establishes the "source of truth" for what methods actually exist in the code
echo "============== 📊 Step 1A: Scanning KDF repository... ==============="
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH scan-rust; then
    echo "❌ Step 1A failed: Repository scanning"
    exit 1
fi
echo

# Step 1B: Scan MDX Documentation Files  
# INPUT: KDF MDX documentation files
# REPORT: reports/kdf_mdx_methods.json and reports/kdf_mdx_method_paths.json
# CONTAINS: All methods found in existing MDX documentation files
# PURPOSE: Establishes what methods are currently documented
echo "============== 📊 Step 1B: Scanning MDX files... ==============="
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH scan-mdx; then
    echo "❌ Step 1B failed: MDX documentation scanning"
    exit 1
fi
echo

# Step 2A: Extract JSON Examples
# INPUT: KDF MDX documentation files
# OUTPUT: Extracts KDF RPC request JSON example files in postman/json/kdf/
# REPORT: reports/kdf_json_examples.json
# STRUCTURE: Organized by version and method, with multiple examples per method
# PURPOSE: Provide bidirectional JSON example sharing between Postman collections and MDX documentation
echo "============== 📊 Step 2A: Extracting JSON examples from MDX files... ==============="
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH json-extract; then
    echo "❌ Step 2 failed: JSON example extraction"
    exit 1
fi
echo

# Step 2B: Get KDF Responses
# INPUT: KDF MDX documentation files
# OUTPUT: Gets KDF RPC responses for JSON example files in postman/json/kdf/
# REPORT: reports/kdf_error_responses.json
# STRUCTURE: Organized by version and method, with multiple examples per method
# PURPOSE: Provide bidirectional JSON example sharing between Postman collections and MDX documentation
echo "============== 📊 Step 2B: Getting KDF responses... ==============="
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH get-kdf-responses; then
    echo "❌ Step 2B failed: Getting KDF responses"
    exit 1
fi
echo

# Step 3: Generate OpenAPI Specifications
echo "============== 🔧 Step 3: Generating OpenAPI specifications... ==============="
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH openapi; then
    echo "❌ Step 3 failed: OpenAPI specification generation"
    exit 1
fi
echo

# Step 4: Generate Postman Collections
# OUTPUT: Creates/updates Postman collection JSON files in postman/collections/
# CONTAINS: Complete Postman collections with requests, examples, and organization
# PURPOSE: Provides ready-to-import Postman collections for API testing
echo "============== 📮 Step 4: Generating Postman collections... ==============="
echo "# This step creates Postman collections and produces:"
echo "#   - postman/collections/KDF_API_V1_Collection.postman_collection.json"
echo "#   - postman/collections/KDF_API_V2_Collection.postman_collection.json"
echo "#   - postman/environments/KDF_API_V1_Environment.postman_environment.json"
echo "#   - postman/environments/KDF_API_V2_Environment.postman_environment.json"
echo "#   - Complete collections with organized folders"
echo "#   - All request/response examples included"
echo "#   - Ready for direct import into Postman"
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH postman; then
    echo "❌ Step 4 failed: Postman collection generation"
    exit 1
fi
echo

# Step 5: Create comprehensive mappings and reports
echo "============== 🗺️ Step 5: Creating unified mapping & comprehensive analysis... ==============="
echo "# This step creates comprehensive mappings and produces:"
echo "#   - Unified mapping files showing relationships between:"
echo "#     * MDX documentation files"
echo "#     * OpenAPI specification files"
echo "#     * JSON example files"
echo "#     * Postman collection entries"
echo "#   - Comprehensive coverage analysis and gap identification:"
echo "#     * Repository vs documentation comparison"
echo "#     * Missing methods identification"
echo "#     * Coverage percentages and statistics"
echo "#     * File path mapping for all methods"
echo "#   - Enables cross-referencing and consistency checking"
echo "#   - Powers advanced tooling and automation"
echo "#   - Includes hotlinks to specific Postman collection requests"
echo "#   - Maps method names to collection folder paths and request IDs"
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH map_methods; then
    echo "❌ Step 5A failed: Unified mapping generation"
    exit 1
fi
echo

# Step 5B: Perform Gap Analysis
echo "============== 🗺️ Step 5B: Performing Gap Analysis... ================"
echo "# This step compares Rust methods against documented methods and reports:"
echo "#   - Undocumented methods (in Rust but not in docs)"
echo "#   - Extra methods (in docs but not in Rust)"
if ! python py/kdf_tools.py --kdf-branch $KDF_BRANCH gap-analysis; then
    echo "❌ Step 5B failed: Gap analysis"
    exit 1
fi
echo
echo "===================================================================="
echo "==  ✅ KDF Documentation Sync completed successfully at $(date)"  ==
echo "===================================================================="
