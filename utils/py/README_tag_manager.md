# KDF Method TagManager

The TagManager provides automatic tag derivation and application for KDF methods based on their defining characteristics.

## Features

The TagManager applies the following tagging rules:

1. **v2 tag**: Applied if the method's request(s) contain `"mmrpc": "2.0"`
2. **task-based tag**: Applied if the method name starts with `"task::"`
3. **Wallet type tags**: Applied if the `wallet_types` has a single value (e.g., "hd", "iguana")
4. **Environment tags**: Applied if the `environments` has a single value (e.g., "native", "wasm")
5. **trezor tag**: Applied if the method name, examples, or request data includes "trezor"
6. **metamask tag**: Applied if the method name, examples, or request data includes "metamask"

## Usage

### Command Line Interface

Use the `manage_kdf_tags.py` script for easy tag management:

```bash
# Show current tag statistics
python utils/py/manage_kdf_tags.py stats

# Analyze tagging rules in detail
python utils/py/manage_kdf_tags.py analyze --detailed

# Preview what changes would be made
python utils/py/manage_kdf_tags.py preview

# Preview changes for a specific method
python utils/py/manage_kdf_tags.py preview --method "task::enable_eth::init"

# Apply all derived tags (creates backup)
python utils/py/manage_kdf_tags.py apply --confirm
```

### Programmatic Usage

```python
from lib.managers.tag_manager import TagManager

# Initialize
tag_manager = TagManager(
    kdf_methods_path="src/data",  # will read kdf_methods_v2.json and kdf_methods_legacy.json
    requests_base_path="src/data/requests/kdf"
)

# Get statistics
stats = tag_manager.get_tag_statistics()

# Derive tags for all methods
derived_tags = tag_manager.derive_tags_for_all_methods()

# Preview changes without applying
changes = tag_manager.apply_derived_tags(dry_run=True)

# Apply changes (creates backup)
changes = tag_manager.apply_derived_tags(dry_run=False)
```

## Implementation Details

### Data Sources

- **KDF Methods**: `src/data/kdf_methods_v2.json` and `src/data/kdf_methods_legacy.json` - Method definitions split by version
- **Request Examples**: `src/data/requests/kdf/` - Contains actual request examples referenced by methods

### Tag Detection Logic

- **mmrpc v2**: Searches all request examples for `"mmrpc": "2.0"`
- **Trezor/MetaMask**: Recursively searches method names, example names, descriptions, and request data
- **Wallet/Environment singularity**: Checks if exactly one value exists in the requirements

### Safety Features

- **Dry run mode**: Preview changes before applying
- **Automatic backups**: Creates `.backup` files before modifying data
- **Non-destructive**: Only adds tags, doesn't remove existing ones
- **Validation**: Checks file existence and data integrity

## Example Output

```json
{
  "total_methods": 32,
  "current_tags": {
    "deprecated": 5,
    "legacy": 2,
    "v2": 30
  },
  "derived_tags": {
    "iguana": 5,
    "native": 4,
    "task-based": 24,
    "trezor": 8,
    "v2": 30
  }
}
```

## Architecture

```
TagManager
├── Data Loading
│   ├── KDF methods JSON
│   └── Request examples (all .json files)
├── Tag Derivation Rules
│   ├── mmrpc version detection
│   ├── Method name pattern matching
│   ├── Requirement singularity checks
│   └── Content-based searches
└── Application & Safety
    ├── Dry run preview
    ├── Backup creation
    └── Safe file updates
```
