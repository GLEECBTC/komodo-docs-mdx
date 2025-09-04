# KDF Responses Manager

## Features

### 🔄 **Unified Collection**
- Single script handles all collection scenarios (wasm/native, hd/non-hd)
- Supports regular methods, task lifecycle methods, and platform coin dependencies

### 🎯 **Comprehensive Collection**
- **All-in-One**: Includes platform coin dependency handling, regular methods, and full task lifecycle management (init → status → cancel)

### 📊 **Comprehensive Output**
- Detailed metadata and collection statistics
- Automatic categorization of responses (auto-updatable vs manual review needed)

### 🤖 **Automated Response File Updates**
- Automatic detection of consistently successful responses across all instances
- Optional self-repairing automated updates to existing response component json files

### ✅ **Validation**
- Comprehensive response file structure validation
- JSON syntax and format checking
- Request/response alignment verification
- Common response reference resolution
- Collected response validation
- Automatic alphabetical sorting of all JSON data file keys (requests, responses, tables, methods)
- Empty template creation for missing response entries
- Deprecated method exclusion from collection and processing
- Prerequisite method execution for method dependencies

## Usage

### Basic Usage

```bash
# Activate virtual environment
source utils/py/.venv/bin/activate

# Run with default settings (enhanced mode)
python utils/py/kdf_responses_manager.py

# Run with automatic file updates
python utils/py/kdf_responses_manager.py --update-files

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--update-files` | Automatically update response files | `false` |

**Note**: Validation always runs on both existing and collected responses. Debug logging is always enabled for comprehensive output.

## Output Format

Results are automatically saved to `postman/generated/reports/kdf_postman_responses.json`.

The output file contains:

```json
{
  "metadata": {
    "collection_timestamp": "2024-01-15 14:30:00 UTC",
    "total_responses_collected": 25,
    "auto_updatable_count": 15,
    "collection_summary": {
      "regular_methods": 20,
      "task_lifecycle_methods": 5
    }
  },
  "responses": {
    "ResponseName": {
      "instances": {
        "native-hd": { "mmrpc": "2.0", "result": {...} },
        "native-nonhd": { "mmrpc": "2.0", "result": {...} }
      },
      "all_successful": true,
      "consistent_structure": true,
      "collection_method": "regular",
      "notes": "Method: enable_coin"
    }
  },
  "auto_updatable": {
    "ResponseName": { "mmrpc": "2.0", "result": {...} }
  },
  "manual_review_needed": {
    "ProblemResponse": {
      "reasons": ["contains_errors", "inconsistent_structure"],
      "instances": {...},
      "collection_method": "task_lifecycle",
      "notes": "Task method: task::enable_utxo::init"
    }
  },
  "validation": {
    "existing_files": {
      "success": true,
      "errors": [],
      "warnings": ["[EMPTY_RESPONSE_LIST] ..."],
      "error_count": 0,
      "warning_count": 5
    },
    "collected_responses": {
      "errors": [],
      "warnings": [],
      "error_count": 0,
      "warning_count": 0
    }
  }
}
```

## Collection Methods

### Regular Methods
- Standard API method calls
- Basic error handling and retry logic
- Platform coin dependency checking

### Task Lifecycle Methods
- Complete task workflow: `init` → `status` (polling) → `cancel`
- Automatic task ID extraction and management
- Status polling with configurable timeout
- Captures all intermediate states

### Platform Coin Dependencies
- Automatic detection of methods requiring platform coins
- Platform coin enablement before method execution
- Support for ETH and IRIS platform coins
- Graceful handling of already-enabled coins

## Error Handling

The tool categorizes failures into specific reasons:

- **contains_errors**: One or more instances returned error responses
- **inconsistent_structure**: Different instances returned structurally different responses
- **response_too_long**: Response size exceeds 10KB limit
- **unknown**: Other unspecified issues

## Integration with Existing Workflow

The unified manager integrates seamlessly with existing processes:

1. **Input**: Uses existing `missing_responses.json` and request data files
2. **Processing**: Handles all collection scenarios in a single run
3. **Output**: Produces unified results for analysis and processing
4. **Updates**: Can automatically update response files when `--update-files` is used

## Prerequisites

- Docker containers running KDF instances on ports 7783 (native-hd) and 7784 (native-nonhd)
- Valid `missing_responses.json` file in `postman/generated/reports/`
- Request data files in `src/data/requests/kdf/`
- Python virtual environment with required dependencies

## Validation Features

### Response File Validation
- **JSON Structure**: Validates JSON syntax and format
- **Required Fields**: Ensures `title` and `json` fields are present
- **Response Types**: Validates `success` and `error` categories
- **Naming Conventions**: Checks PascalCase/camelCase patterns
- **Common References**: Resolves and validates common response references
- **Automatic Sorting**: Sorts all JSON data files alphabetically by keys for consistency (requests, responses, tables, methods)
- **Empty Templates**: Creates `{"success": [], "error": []}` templates for requests missing response entries
- **Deprecated Method Filtering**: Automatically excludes methods marked with `"deprecated": true` from processing

### Request/Response Alignment
- **Missing Responses**: Identifies requests without corresponding responses
- **Missing Requests**: Identifies responses without corresponding requests
- **Version Consistency**: Validates alignment across legacy and v2 APIs

### Collected Response Validation
- **Format Checking**: Validates collected response structure
- **API Version**: Checks mmrpc version compliance
- **Error Detection**: Identifies malformed or incomplete responses
- **Structure Consistency**: Normalizes address and wallet-specific fields for accurate comparison

## Logging and Monitoring

- Configurable log levels for different verbosity needs
- Structured logging with timestamps and level indicators
- Progress tracking for long-running collection operations
- Detailed error reporting with context

## Performance Considerations

- **Configurable timeouts**: 30s default, or custom timeout from `kdf_methods.json` (e.g., `enable_eth_with_tokens: 300s`)
- **Status polling**: 2-second intervals with 20-check limit for task lifecycle
- **Automatic coin disabling**: Prevents conflicts between collection attempts
- **Efficient structure comparison**: Optimized for consistency checking

## Deprecated Method Handling

Methods marked with `"deprecated": true` in `src/data/kdf_methods.json` are automatically excluded from:
- Postman collection generation
- Missing responses reports  
- Response collection attempts
- Template creation
- All validation processes

## Manual Method Exclusion

Methods requiring external services or manual intervention are automatically excluded from missing response reports:

### Excluded Method Types:
- **WalletConnect**: Requires external wallet connection
- **Trezor**: Requires hardware wallet interaction
- **Metamask**: Requires browser extension
- **PIN/UserAction**: Requires user input

These methods are identified by keywords in their names and filtered out since they cannot be automated in a headless environment.

### Currently Deprecated Methods:
- `enable_bch_with_tokens` - Legacy BCH token activation
- `task::enable_bch::init` - BCH task initialization
- `task::enable_bch::status` - BCH task status checking
- `task::enable_bch::cancel` - BCH task cancellation
- `task::enable_bch::user_action` - BCH task user interaction

## Prerequisite Method Handling

Some methods require other methods to be executed first. The system automatically handles these dependencies:

### Method Dependencies:
- `enable_tendermint_token` requires `enable_tendermint_with_assets` to be called first

Dependencies are defined in `src/data/kdf_methods.json` using the `prerequisite_methods` array:
```json
{
  "enable_tendermint_token": {
    "requirements": {
      "prerequisite_methods": ["enable_tendermint_with_assets"]
    }
  }
}
```

The response manager automatically executes prerequisite methods before running the target method.

## Smart Structure Comparison

The system uses intelligent structure comparison to determine response consistency across different wallet types:

### Normalized Fields:
- **Address keys**: Different addresses (e.g., `iaa1hkg6...` vs `iaa1xt2ru7...`) are normalized to `<address>`
- **Wallet-specific fields**: `address`, `pubkey`, `derivation_path`, `account_index` are normalized
- **Address patterns**: Supports Cosmos (`iaa`, `cosmos`), Ethereum (`0x`), Bitcoin (`1`, `3`, `bc1`), and generic long addresses

This ensures that responses with structurally identical data but different addresses/keys are correctly identified as having consistent structure for auto-updating.

## Response Delay Tracking

The system automatically tracks response times for all method calls across different KDF environments to identify performance characteristics and optimization opportunities.

### Output Files
- **`kdf_postman_responses.json`**: Complete response collection results and validation data
- **`kdf_response_delays.json`**: Response timing data across KDF environments
- **`missing_responses.json`**: Methods requiring response documentation

### Delay Report Structure
```json
{
  "metadata": {
    "generated_at": "2025-01-01 12:00:00 UTC",
    "total_methods": 5,
    "total_requests": 12,
    "description": "Response timing data for KDF methods across different environments"
  },
  "delays": {
    "method_name": {
      "exampleKey": {
        "native_hd": {
          "status_code": 200,
          "delay": 24.8
        },
        "native_nonhd": {
          "status_code": 200, 
          "delay": 18.5
        }
      }
    }
  }
}
```

### Status Codes
- **200**: Successful response
- **408**: Request timeout (exceeds method-specific timeout or 30s default)  
- **503**: Connection failed/service unavailable
- **500**: Internal server error or unexpected error

### Performance Analysis Use Cases
- **Performance comparison**: HD vs non-HD wallet performance
- **Timeout optimization**: Identify methods needing longer timeouts
- **Environment analysis**: Compare native vs WASM performance
- **Bottleneck identification**: Find slowest operations for optimization

## Timeout Configuration

Method timeouts are configured in `src/data/kdf_methods.json` using the `timeout` field:

```json
{
  "enable_eth_with_tokens": {
    "table": "EnableEthWithTokensArguments",
    "examples": { ... },
    "requirements": { ... },
    "timeout": 300
  }
}
```

### Timeout Behavior
- **Default**: 30 seconds for all methods
- **Custom**: Specify `"timeout": <seconds>` in method configuration
- **Application**: Used for all HTTP requests to KDF instances for that method
- **Inheritance**: Prerequisite methods use their own configured timeouts

### Configuration Examples
```json
{
  "enable_eth_with_tokens": {
    "timeout": 300
  },
  "enable_tendermint_with_assets": {
    "timeout": 180
  },
  "task::enable_eth::init": {
    "timeout": 240
  }
}
```
