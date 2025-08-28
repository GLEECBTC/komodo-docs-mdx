# Node Update Script

This script addresses [GitHub Issue #360](https://github.com/KomodoPlatform/komodo-docs-mdx/issues/360) by automatically updating server and node values in documentation request examples with the latest data from the [coins repository](https://github.com/KomodoPlatform/coins).

## Overview

The Komodo DeFi Framework documentation includes example request JSON files that show how to interact with various APIs. These examples contain server URLs (electrum servers, RPC nodes, light wallet servers) that can become outdated over time. This script automates the process of keeping those server values synchronized with the authoritative source in the coins repository.

## How It Works

1. **Fetches Latest Data**: Downloads the latest `coins_config.json` from the coins repository
2. **Identifies Tickers**: Scans request JSON files for ticker symbols
3. **Detects Protocol Type**: Automatically determines coin protocol (ETH, Tendermint, UTXO, ZHTLC)
4. **Server Selection**: Selects up to 3 servers, prioritizing domains containing 'cipig' or 'komodo'
5. **Updates Servers**: Replaces server/node arrays with the selected values from the coins configuration
6. **Protocol-Specific Mapping**: Maps different server types based on coin protocol
7. **Preserves Structure**: Maintains the original JSON structure and formatting

## Usage

### Prerequisites

Make sure you have the Python virtual environment activated:

```bash
source utils/py/.venv/bin/activate
```

### Basic Usage

Update a single file in-place:
```bash
python utils/py/update_request_nodes.py src/data/requests/kdf/v2/coin_activation.json
```

Update a file and save to a different location:
```bash
python utils/py/update_request_nodes.py input.json output.json
```

### Command Line Options

- `input_file` (required): Path to the input request JSON file
- `output_file` (optional): Path to save the updated file. If not specified, updates the input file in-place
- `-v, --verbose`: Enable verbose logging for debugging

### Examples

#### Update coin activation examples
```bash
python utils/py/update_request_nodes.py src/data/requests/kdf/v2/coin_activation.json
```

#### Batch update multiple files
```bash
find src/data/requests/kdf/ -name "*.json" -exec python utils/py/update_request_nodes.py {} \;
```

#### Test mode (save to different file)
```bash
python utils/py/update_request_nodes.py src/data/requests/kdf/v2/coin_activation.json /tmp/test_output.json
```

## Supported Coin Protocols

The script automatically detects and handles different coin protocols:

### ETH/EVM Chains (ETH, MATIC, BNB, AVAX, etc.)
- **coins_config field**: `nodes`
- **request field**: `nodes`
- **Example coins**: ETH, MATIC, BNB, AVAX, FTM

### Tendermint/Cosmos Chains
- **coins_config field**: `rpc_urls`
- **request field**: `nodes`
- **Example coins**: ATOM, IRIS, OSMOSIS

### UTXO Chains (Bitcoin-like)
- **coins_config field**: `electrum`
- **request field**: `servers` (nested under `mode.rpc_data.servers`)
- **Example coins**: BTC, LTC, KMD, QTUM, BCH

### ZHTLC Chains (Privacy coins)
- **coins_config fields**: `light_wallet_d_servers` + `electrum`
- **request fields**: `light_wallet_d_servers` + `electrum_servers`
- **Example coins**: ARRR, ZOMBIE

## Supported JSON Formats

The script can handle various JSON structures:

### Single Request Object
```json
{
  "method": "task::enable_eth::init",
  "params": {
    "ticker": "MATIC",
    "nodes": [...]
  }
}
```

### Multiple Request Objects
```json
{
  "Request1": {
    "params": {
      "ticker": "MATIC",
      "nodes": [...]
    }
  },
  "Request2": {
    "params": {
      "ticker": "BTC",
      "nodes": [...]
    }
  }
}
```

### Array of Requests
```json
[
  {
    "params": {
      "ticker": "MATIC",
      "nodes": [...]
    }
  }
]
```

## Server Format Conversion

The script automatically converts between the coins repository format and the documentation format based on protocol type:

### ETH/EVM Nodes
**Coins Repository Format:**
```json
"nodes": [
  {
    "url": "https://example.com:8545",
    "ws_url": "wss://example.com:8546",
    "komodo_proxy": true
  }
]
```

**Documentation Format:**
```json
"nodes": [
  {
    "url": "https://example.com:8545"
  }
]
```

### Tendermint RPC URLs
**Coins Repository Format:**
```json
"rpc_urls": [
  {
    "url": "https://cosmos-rpc.example.com/",
    "api_url": "https://cosmos-api.example.com/",
    "grpc_url": "https://cosmos-grpc.example.com/",
    "ws_url": "wss://cosmos-rpc.example.com/websocket"
  }
]
```

**Documentation Format:**
```json
"nodes": [
  {
    "url": "https://cosmos-rpc.example.com/",
    "api_url": "https://cosmos-api.example.com/",
    "grpc_url": "https://cosmos-grpc.example.com/",
    "ws_url": "wss://cosmos-rpc.example.com/websocket"
  }
]
```

### UTXO Electrum Servers
**Coins Repository Format:**
```json
"electrum": [
  {
    "url": "btc.electrum1.cipig.net:10000",
    "protocol": "TCP",
    "contact": [...]
  }
]
```

**Documentation Format:**
```json
"servers": [
  {
    "url": "btc.electrum1.cipig.net:10000",
    "protocol": "TCP"
  }
]
```

### ZHTLC Light Wallet Servers
**Coins Repository Format:**
```json
"light_wallet_d_servers": [
  "https://piratelightd1.example.com:443"
],
"electrum": [
  {
    "url": "arrr.electrum1.cipig.net:10008",
    "protocol": "TCP"
  }
]
```

**Documentation Format:**
```json
"light_wallet_d_servers": [
  "https://piratelightd1.example.com:443"
],
"electrum_servers": [
  {
    "url": "arrr.electrum1.cipig.net:10008",
    "protocol": "TCP"
  }
]
```

## Automation

For CI/CD integration, you can create a script that updates all request files:

```bash
#!/bin/bash
# Update all request JSON files
find src/data/requests/kdf -name "*.json" | while read file; do
    echo "Updating $file..."
    python utils/py/update_request_nodes.py "$file"
done
```

## Error Handling

The script includes comprehensive error handling:

- **Network Issues**: Graceful handling of connection failures when fetching coins_config.json
- **Invalid JSON**: Clear error messages for malformed JSON files
- **Missing Files**: File existence validation before processing
- **Missing Tickers**: Warnings for tickers not found in the coins configuration
- **Missing Nodes**: Warnings for coins without node configurations

## Logging

The script provides detailed logging:

- **INFO**: Normal operation status and update summaries
- **WARNING**: Non-critical issues like missing tickers
- **ERROR**: Critical failures that prevent execution
- **DEBUG**: Detailed operation information (with `-v` flag)

## Server Selection Logic

To keep JSON payloads lightweight, the script limits server selections to 3 maximum:

1. **Priority Selection**: Servers containing 'cipig' or 'komodo' in their domains are preferred
2. **Random Selection**: If more than 3 servers are available, selection is randomized within priority groups
3. **Fallback**: If fewer than 3 priority servers exist, the remainder is filled from regular servers

## Example Output

```
2025-08-07 15:56:34,085 - INFO - Loaded request file: coin_activation.json
2025-08-07 15:56:34,085 - INFO - Fetching coins configuration from https://raw.githubusercontent.com/...
2025-08-07 15:56:34,521 - INFO - Successfully fetched configuration for 769 coins
2025-08-07 15:56:34,521 - DEBUG - Detected protocol 'UTXO' for ticker 'KMD'
2025-08-07 15:56:34,521 - DEBUG - Selected 3 servers from 9 available (9 priority, 0 regular)
2025-08-07 15:56:34,521 - INFO - Updated UTXO electrum servers for ticker 'KMD': 9 -> 3 servers
2025-08-07 15:56:34,521 - INFO - Updated request object: TaskEnableUtxoInit
2025-08-07 15:56:34,522 - INFO - ✅ Successfully updated 16 request(s) with latest server/node values
2025-08-07 15:56:34,523 - INFO - 🎉 Update completed successfully!
```

## Integration with CI/CD

This script can be integrated into GitHub Actions workflows to automatically keep request examples up-to-date. See the example workflow in `.github/workflows/update-nodes.yml` for a complete CI/CD solution.

## Troubleshooting

### Script shows "No updates were needed"
- Verify that the JSON file contains a `ticker` field
- Check that the ticker exists in the coins repository
- Ensure the request has a `nodes` array to update

### Network errors when fetching coins_config.json
- Check internet connectivity
- Verify that the coins repository URL is accessible
- Consider using a local copy of coins_config.json for testing

### JSON parsing errors
- Validate your input JSON file with a JSON validator
- Check for trailing commas or other syntax issues
- Ensure proper UTF-8 encoding

--------------------------------------------------------------

# Postman Collection Generator

A comprehensive tool for generating Postman collections from Komodo DeFi Framework (KDF) API documentation data.

## Overview

This unified generator replaces three separate scripts and provides comprehensive functionality for creating both standard and environment-specific Postman collections. It combines:

- **Standard Collection Generation**: Creates comprehensive collections with full folder structure and parameter validation
- **Environment-Specific Collections**: Generates collections optimized for different runtime environments (Native, WASM, Trezor)
- **Parameter Validation**: Validates request parameters against table definitions
- **Protocol Filtering**: Automatically adjusts protocol configurations for environment compatibility
- **Comprehensive Reporting**: Generates detailed reports on missing data and validation issues

## Features

### Collection Types

1. **Standard Comprehensive Collection**
   - Full hierarchical folder structure organized by API version and method families
   - Parameter validation against documentation tables
   - Comprehensive parameter documentation in request descriptions
   - Task ID variable management for workflow automation
   - Multiple example variants within single requests

2. **Environment-Specific Collections**
   - **Native + HD**: Native environment with HD wallet support
   - **Native + Iguana**: Native environment with legacy Iguana wallet support  
   - **WASM + HD**: WebAssembly environment with HD wallet support (WSS protocols only)
   - **WASM + Iguana**: WebAssembly environment with Iguana wallet support (WSS protocols only)
   - **Trezor + Native + HD**: Native environment with Trezor hardware wallet support
   - **Trezor + WASM + HD**: WASM environment with Trezor hardware wallet support

### Key Features

- **Protocol Filtering**: Automatically filters electrum servers and WebSocket URLs based on environment capabilities
- **Parameter Validation**: Validates request parameters against documentation tables and reports unused parameters
- **Response Validation**: Checks for corresponding response documentation
- **Translation Support**: Uses human-readable names from method configuration
- **Hardware Compatibility**: Filters requests based on hardware requirements (e.g., Trezor-only methods)
- **Wallet Type Filtering**: Removes incompatible parameters based on wallet type (HD vs Iguana)

## Installation & Setup

### Prerequisites

1. **Python 3.8+** with required dependencies
2. **Virtual Environment** (recommended)

### Environment Setup

The generator requires a virtual environment located at `utils/py/.venv`. Activate it before running:

```bash
# From workspace root
source utils/py/.venv/bin/activate
```

### Dependencies

The script uses the `EnvironmentManager` from the `lib/managers/` directory, which should be available in the same directory structure.

## Usage

### Basic Usage

```bash
# Generate all collections (standard + all environments)
python generate_postman.py --all

# Generate only standard comprehensive collection
python generate_postman.py --standard

# Generate specific environment collection
python generate_postman.py --environment native_hd
```

### Advanced Usage

```bash
# Custom output directory
python generate_postman.py --all --output-dir ./custom_output

# Specific workspace path
python generate_postman.py --all --workspace /path/to/komodo-docs-mdx

# Verbose output for debugging
python generate_postman.py --all --verbose
```

### Command Line Options

| Option | Short | Description |
|--------|--------|-------------|
| `--all` | `-a` | Generate all collections (standard + all environments) |
| `--standard` | `-s` | Generate only the standard comprehensive collection |
| `--environment ENV` | `-e ENV` | Generate specific environment collection |
| `--workspace PATH` | `-w PATH` | Path to workspace root (auto-detected if not provided) |
| `--output-dir PATH` | `-o PATH` | Output directory (default: `postman/generated`) |
| `--verbose` | `-v` | Enable verbose output |

### Available Environments

- `native_hd` - Native environment with HD wallet
- `native_iguana` - Native environment with Iguana wallet
- `wasm_hd` - WASM environment with HD wallet  
- `wasm_iguana` - WASM environment with Iguana wallet
- `trezor_native_hd` - Native + Trezor + HD wallet
- `trezor_wasm_hd` - WASM + Trezor + HD wallet

## Output Structure

```
postman/generated/
├── collections/
│   └── kdf_comprehensive_collection.json    # Standard comprehensive collection
├── environments/
│   ├── kdf_native_hd_collection.json       # Environment-specific collections
│   ├── kdf_wasm_hd_collection.json
│   ├── kdf_trezor_native_hd_collection.json
│   └── ...
├── reports/
│   ├── unused_params.json                   # Parameters not used in examples
│   ├── missing_responses.json               # Methods without response documentation
│   ├── untranslated_keys.json              # Request keys without translations
│   └── missing_tables.json                 # Methods without parameter tables
└── generation_summary.json                 # Overall generation summary
```

## Data Sources

The generator reads from the following data sources in the workspace:

- `src/data/requests/kdf/` - Request examples organized by API version
- `src/data/responses/kdf/` - Response examples and common response templates  
- `src/data/tables/` - Parameter documentation tables
- `src/data/kdf_methods.json` - Method configuration and translations

## Environment-Specific Adaptations

### Protocol Filtering

**Native Environment:**
- Supports TCP, SSL, and WSS protocols for electrum servers
- Prefers TCP and SSL, falls back to WSS
- Supports both `ws://` and `wss://` WebSocket connections

**WASM Environment:**  
- Only supports WSS protocols for electrum servers
- Automatically converts `ws://` to `wss://` in WebSocket URLs
- Filters out non-WSS electrum servers

**Trezor Hardware Wallet:**
- Includes hardware-specific examples and parameters
- Filters out non-Trezor compatible requests
- Adds Trezor-specific documentation notes

### Parameter Filtering

**HD Wallet Support:**
- Includes HD-specific parameters like `gap_limit`, `scan_policy`
- Supports derivation path configurations
- Includes address scanning parameters

**Iguana Wallet Support:**
- Removes HD-only parameters from requests
- Uses legacy wallet parameter sets
- Maintains backward compatibility

## Validation & Reporting

### Parameter Validation
- Compares request examples against documentation tables
- Reports unused parameters that are documented but not demonstrated
- Validates nested parameter structures

### Response Validation  
- Checks for corresponding response examples
- Reports methods missing response documentation
- Resolves common response references

### Translation Validation
- Identifies request keys without human-readable translations
- Reports untranslated keys for documentation improvement

### Table Validation
- Identifies methods without parameter documentation tables
- Reports missing table references

## Migration from Separate Scripts

This unified generator replaces:

- `postman_collection_generator.py` - Standard collection generation
- `generate_environment_postman.py` - Environment-specific generation  
- Direct usage of `environment_manager.py` - Now integrated as a library

### Migration Benefits

1. **Reduced Code Duplication**: Eliminates ~60% code overlap between original scripts
2. **Unified CLI**: Single interface for all collection generation needs
3. **Consistent Output**: Standardized folder structures and naming conventions
4. **Enhanced Validation**: Combined validation logic from all sources
5. **Better Maintainability**: Single codebase to maintain and extend

## Error Handling

The generator includes comprehensive error handling:

- **File Not Found**: Graceful handling of missing data files with warnings
- **JSON Parsing**: Clear error messages for malformed JSON files
- **Environment Validation**: Validates environment compatibility before generation
- **Output Directory**: Automatically creates missing output directories

## Debugging

Use the `--verbose` flag to enable detailed logging:

```bash
python generate_postman.py --all --verbose
```

This provides:
- Detailed processing logs for each file and method
- Parameter validation details
- Environment compatibility checks
- File generation confirmations

## Contributing

When adding new environments or features:

1. Update the `EnvironmentManager` configuration in `lib/managers/environment_manager.py`
2. Add environment choices to the CLI parser
3. Update this README with new environment descriptions
4. Test generation with `--verbose` flag to verify correct filtering

## Troubleshooting

### Common Issues

**Virtual Environment Not Activated:**
```bash
# Error: ModuleNotFoundError: No module named 'managers'
# Solution: Activate the virtual environment
source utils/py/.venv/bin/activate
```

**Missing Data Files:**
```bash
# Error: FileNotFoundError: Request file not found
# Solution: Ensure you're running from the correct workspace root
python generate_postman.py --workspace /path/to/komodo-docs-mdx --all
```

**Empty Collections:**
```bash
# Issue: Generated collections have no requests
# Solution: Check method compatibility and environment filtering with --verbose
python generate_postman.py --environment wasm_hd --verbose
```

For additional support, check the generation reports in the `reports/` directory for detailed validation information.
