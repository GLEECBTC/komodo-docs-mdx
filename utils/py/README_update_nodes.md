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
python utils/py/update_request_nodes.py src/data/requests/v2/coin_activation.json
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
python utils/py/update_request_nodes.py src/data/requests/v2/coin_activation.json
```

#### Batch update multiple files
```bash
find src/data/requests/ -name "*.json" -exec python utils/py/update_request_nodes.py {} \;
```

#### Test mode (save to different file)
```bash
python utils/py/update_request_nodes.py src/data/requests/v2/coin_activation.json /tmp/test_output.json
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
find src/data/requests/ -name "*.json" | while read file; do
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