# KDF Tools TUI

A Terminal User Interface (TUI) for the Komodo DeFi Framework Tools, providing an interactive interface for `kdf_tools.py` while maintaining full scriptability.

## Features

- **Interactive Menus**: Browse commands by category with clear descriptions
- **Command Configuration**: Set arguments interactively with defaults and validation
- **Quick Run**: Common commands with default settings for fast execution
- **Search**: Find commands by name, description, or category
- **Scriptability**: All commands can still be run from command line
- **Rich Interface**: Modern terminal UI with colors, tables, and panels

## Installation

1. Install TUI dependencies:
```bash
pip install -r utils/py/requirements-tui.txt
```

2. Run the TUI:
```bash
python utils/py/kdf_tui.py
```

## Usage

### Main Menu
The TUI provides four main options:

1. **Browse by Category** - Navigate through command categories
2. **Search Commands** - Find commands by keyword
3. **Quick Run** - Execute common commands with defaults
4. **Exit** - Close the TUI

### Command Categories

- **Documentation**: `scan-mdx`, `scan-rust`, `gap-analysis`
- **OpenAPI**: `openapi`, `generate-common-schemas`
- **Postman**: `postman`
- **Sync**: `sync-docs-to-postman`, `sync-postman-to-docs`, `sync-bidirectional`
- **Container**: `build-container`, `start-container`, `stop-container`
- **Analysis**: `json-extract`, `get-kdf-responses`, `extract-errors`
- **Utility**: `balances`, `switch-kdf-branch`
- **Workflows**: `walletconnect-workflow`, `trezor-workflow`

### Command Configuration

When selecting a command, the TUI will prompt for:

- **Required Arguments**: Must be provided (e.g., method name for `get-kdf-responses`)
- **Optional Arguments**: Can use defaults or set custom values
- **Boolean Flags**: Toggle on/off (e.g., `--dry-run`, `--clean`)

### Quick Run

The Quick Run menu provides fast access to common commands with sensible defaults:

- `scan-mdx` - Scan MDX documentation
- `scan-rust` - Scan Rust repository  
- `gap-analysis` - Compare Rust vs MDX
- `openapi` - Generate OpenAPI specs
- `postman` - Generate Postman collections
- `sync-bidirectional` - Bidirectional sync
- `build-container` - Build KDF container
- `start-container` - Start KDF container
- `walletconnect-workflow` - Interactive WalletConnect management
- `trezor-workflow` - Interactive Trezor device management

## Examples

### Interactive Sync Configuration
```
1. Browse by Category
2. Search Commands
3. Quick Run
4. Exit

Select an option (1-4): 1

Available Categories:
  1. Documentation
  2. OpenAPI
  3. Postman
  4. Sync
  5. Container
  6. Analysis
  7. Utility
  8. Workflows

Select category (0-8): 4

Commands - Sync
┌─────┬──────────────────────────────┬──────────────────────────────────────────────────┐
│ #   │ Command                      │ Description                                      │
├─────┼──────────────────────────────┼──────────────────────────────────────────────────┤
│ 1   │ sync-docs-to-postman        │ Sync from MDX docs to Postman collection        │
│ 2   │ sync-postman-to-docs        │ Sync from Postman collection to MDX docs        │
│ 3   │ sync-bidirectional          │ Perform bidirectional sync                       │
└─────┴──────────────────────────────┴──────────────────────────────────────────────────┘

Select a command (0-3): 1

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ Command Configuration                                                              │
│                                                                                   │
│ Command: sync                                                                     │
│ Description: Sync from MDX docs to Postman collection                            │
│ Category: Sync                                                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

Enter --method-filter (default: ): task::enable_utxo
Use --dry-run? (default: False) [y/N]: y
Enter --kdf-branch (default: dev): 

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ Command Execution                                                                 │
│                                                                                   │
│ Executing:                                                                        │
│ python utils/py/kdf_tools.py sync docs-to-postman --method-filter task::enable_utxo --dry-run --kdf-branch dev │
└─────────────────────────────────────────────────────────────────────────────────────┘

✅ Command executed successfully!
```

### Search Example
```
Select an option (1-4): 2

Enter search term: sync

Search Results
┌─────┬──────────────────────────────┬────────────┬────────────────────────────────────┐
│ #   │ Command                      │ Category   │ Description                        │
├─────┼──────────────────────────────┼────────────┼────────────────────────────────────┤
│ 1   │ sync-docs-to-postman        │ Sync       │ Sync from MDX docs to Postman     │
│ 2   │ sync-postman-to-docs        │ Sync       │ Sync from Postman to MDX docs     │
│ 3   │ sync-bidirectional          │ Sync       │ Perform bidirectional sync         │
└─────┴──────────────────────────────┴────────────┴────────────────────────────────────┘
```

## Scriptability

The TUI is built on top of the existing CLI, so all commands remain fully scriptable:

```bash
# TUI way
python utils/py/kdf_tui.py

# Direct CLI way (still works)
python utils/py/kdf_tools.py sync docs-to-postman --method-filter "task::enable_utxo" --dry-run

# Workflow commands
python utils/py/kdf_tools.py walletconnect-workflow
python utils/py/kdf_tools.py trezor-workflow
```

## Workflow Commands

The TUI includes specialized workflow commands that launch dedicated interactive interfaces:

### WalletConnect Workflow
Launches an interactive interface for managing WalletConnect sessions:
- Create new connections
- List active sessions
- Get session details
- Ping sessions
- Delete sessions
- Activate coins with WalletConnect
- Make orders and trades

### Trezor Workflow  
Launches an interactive interface for managing Trezor hardware wallets:
- Initialize Trezor devices
- Check connection status
- Activate coins with Trezor
- Create new accounts
- Generate addresses
- Scan addresses
- Withdraw funds
- Send raw transactions

These workflows provide comprehensive interfaces for hardware wallet and WalletConnect integration with the Komodo DeFi Framework.

## Keyboard Shortcuts

- **Ctrl+C**: Exit the TUI
- **Enter**: Confirm selection
- **Arrow Keys**: Navigate menus (in some contexts)
- **Tab**: Move between input fields

## Troubleshooting

### Dependencies Not Found
```
Error importing TUI components: No module named 'textual'
```
**Solution**: Install dependencies with `pip install -r utils/py/requirements-tui.txt`

### Import Errors
```
Error importing TUI components: No module named 'utils.py.lib.tui'
```
**Solution**: Ensure you're running from the project root directory

### Command Execution Errors
If commands fail to execute, check:
1. Python path is correct
2. `kdf_tools.py` is accessible
3. All required dependencies are installed

## Development

The TUI is built using:
- **Textual**: Modern TUI framework for Python
- **Rich**: Rich text and formatting library
- **Asyncio**: For async command execution

### Adding New Commands

To add new commands to the TUI:

1. Update the `_define_commands()` method in `KDFTUI` class
2. Add the command configuration with appropriate arguments
3. Test the command execution

### Customizing the Interface

The TUI can be customized by:
- Modifying the menu layouts in `show_main_menu()`
- Adding new search categories
- Customizing the command configuration interface
- Adding validation rules for arguments

## Benefits

1. **User-Friendly**: No need to remember command syntax
2. **Discoverable**: Browse and search available commands
3. **Configurable**: Interactive argument setting with defaults
4. **Scriptable**: All commands still work from command line
5. **Consistent**: Same underlying CLI, just better interface 