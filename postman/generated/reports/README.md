# Postman Collection Generation Reports

This directory contains validation reports generated during the Postman collection creation process. These reports help identify missing, unused, or incomplete components in the KDF API documentation and collection generation.

## Report Types

### 1. Missing Responses (`missing_responses.json`)

**Purpose**: Lists API methods that have request examples but are missing corresponding response examples.

**Structure**: 
```json
{
  "method_name": [
    "RequestExampleKey1",
    "RequestExampleKey2"
  ]
}
```

**How to Fix**:
- Add response examples to the corresponding response files in `src/data/responses/kdf/`
- For v2 methods: Add to `src/data/responses/kdf/v2/coin_activation.json`
- For legacy methods: Add to `src/data/responses/kdf/legacy/coin_activation.json`
- For common responses: Add to `src/data/responses/kdf/common.json`

**Example Fix**:
```json
// In src/data/responses/kdf/v2/coin_activation.json
{
  "TaskEnableBchInit": {
    "result": {
      "task_id": 1234567890,
      "status": "InProgress"
    }
  }
}
```

### 2. Missing Tables (`missing_tables.json`)

**Purpose**: Lists API methods that don't have corresponding parameter documentation tables.

**Structure**: Array of method names missing table definitions.

**How to Fix**:
- Add method configuration to `src/data/kdf_methods_v2.json` or `src/data/kdf_methods_legacy.json` with table reference
- Create parameter tables in `src/data/tables/` directories:
  - Common structures: `src/data/tables/common-structures/`
  - V2 methods: `src/data/tables/v2/`
  - Legacy methods: `src/data/tables/legacy/`

**Example Fix**:
```json
// In src/data/kdf_methods_v2.json
{
  "enable_erc20": {
    "table": "EnableErc20Request",
    "examples": {
      "EnableErc20Basic": "Enable ERC-20 Token"
    }
  }
}

// In src/data/tables/v2/coin_activation.json
{
  "EnableErc20Request": {
    "data": [
      {
        "parameter": "coin",
        "type": "string",
        "required": true,
        "description": "The ticker symbol of the ERC-20 token"
      }
    ]
  }
}
```

### 3. Untranslated Keys (`untranslated_keys.json`)

**Purpose**: Lists request example keys that don't have human-readable translations defined.

**Structure**: Array of untranslated request keys.

**How to Fix**:
- Add translations to the `examples` section in `src/data/kdf_methods_v2.json` or `src/data/kdf_methods_legacy.json`
- Use descriptive, user-friendly names that explain what the example demonstrates

**Example Fix**:
```json
// In src/data/kdf_methods_v2.json
{
  "task::enable_utxo::init": {
    "table": "TaskEnableUtxoInitRequest",
    "examples": {
      "TaskEnableUtxoInit": "Initialize UTXO Coin Activation",
      "TaskEnableUtxoInitWithSyncParams": "Initialize UTXO with Sync Parameters"
    }
  }
}
```

### 4. Unused Parameters (`unused_params.json`)

**Purpose**: Lists parameters defined in documentation tables but not used in any request examples.

**Structure**:
```json
{
  "method_name": [
    "unused_param1",
    "unused_param2.nested_param"
  ]
}
```

**How to Fix**:

**Option 1 - Add Missing Parameters to Requests**:
Add the unused parameters to request examples in `src/data/requests/kdf/`:
```json
// In src/data/requests/kdf/v2/coin_activation.json
{
  "TaskEnableUtxoInit": {
    "method": "task::enable_utxo::init",
    "params": {
      "activation_params": {
        "coin": "BTC",
        "required_confirmations": 3,  // Previously unused parameter
        "scan_blocks_per_iteration": 100  // Previously unused parameter
      }
    }
  }
}
```

**Option 2 - Remove Obsolete Parameters from Tables**:
Remove parameters that are no longer valid from table definitions in `src/data/tables/`:
```json
// Remove obsolete parameters from table definitions
{
  "TaskEnableUtxoInitRequest": {
    "data": [
      // Remove entries for parameters that are no longer valid
    ]
  }
}
```

**Option 3 - Mark Parameters as Optional**:
Update table definitions to indicate optional parameters:
```json
{
  "parameter": "scan_blocks_per_iteration",
  "type": "integer",
  "required": false,
  "description": "Optional: Number of blocks to scan per iteration"
}
```

## File Locations Reference

### Request Examples
- **V2 Methods**: `src/data/requests/kdf/v2/coin_activation.json`
- **Legacy Methods**: `src/data/requests/kdf/legacy/coin_activation.json`

### Response Examples
- **V2 Methods**: `src/data/responses/kdf/v2/coin_activation.json`
- **Legacy Methods**: `src/data/responses/kdf/legacy/coin_activation.json`
- **Common Responses**: `src/data/responses/kdf/common.json`

### Documentation Tables
- **Common Structures**: `src/data/tables/common-structures/*.json`
- **V2 Methods**: `src/data/tables/v2/*.json`
- **Legacy Methods**: `src/data/tables/legacy/*.json`

### Method Configuration
- **All Methods**: `src/data/kdf_methods_v2.json` and `src/data/kdf_methods_legacy.json`

## Workflow for Fixing Issues

1. **Start with Missing Tables**: Ensure all methods have proper documentation tables
2. **Add Missing Responses**: Create response examples for better API documentation
3. **Translate Keys**: Add human-readable names for all request examples
4. **Review Unused Parameters**: Determine if parameters should be added to examples or removed from tables

## Regenerating Reports

After making fixes, regenerate the collection and reports:

```bash
# From workspace root
source utils/py/.venv/bin/activate
python utils/py/generate_postman.py --all
```

The reports will be updated to reflect any fixes made.

## Understanding Counts

The counts in `generation_summary.json` represent:
- **missing_responses**: Total number of missing response examples across all methods
- **missing_tables**: Number of methods without documentation tables
- **untranslated_keys**: Number of request keys without human-readable names
- **unused_params**: Total number of documented parameters not used in any examples

Lower counts indicate more complete documentation and better API coverage.
