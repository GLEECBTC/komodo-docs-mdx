# Komodo DeFi Framework OpenAPI Specification

This directory contains the OpenAPI specification for the Komodo DeFi Framework API, organized in a modular and maintainable structure.

## File Structure

```
postman/openapi/
├── openapi.yaml                    # Main OpenAPI specification file
├── activation_postman.yaml         # Focused activation-only specification
├── components/
│   └── schemas/                    # Reusable schema definitions
│       ├── Activation.yaml
│       ├── Lightning.yaml
│       ├── Nfts.yaml
│       ├── Orders.yaml
│       ├── Swaps.yaml
│       ├── Wallet.yaml
│       ├── BotConfig.yaml
│       ├── Enums.yaml
│       └── Common.yaml
└── paths/
    ├── v1/                        # Legacy v1 endpoint definitions
    └── v2/                        # Current v2 endpoint definitions
```

## Main Files

### `openapi.yaml`
The primary OpenAPI specification file that includes all available endpoints. This file serves as the complete API reference and is automatically maintained by the mapping script.

### `activation_postman.yaml`
A focused specification containing only coin and token activation endpoints. This is useful for tools or documentation that only need activation-related functionality.

## Maintenance

The OpenAPI specification is automatically maintained using the mapping script located at `utils/py/mapping.py`. This script:

1. Scans MDX documentation files to discover API methods
2. Scans YAML path definitions to find available endpoints
3. Updates the main `openapi.yaml` file with any new or changed paths
4. Generates unified mapping files for cross-referencing

### Running the Update Script

To update the OpenAPI specification:

```bash
# From the utils/py directory
python mapping.py --update-openapi

# Or use the convenience script
./update_openapi.sh
```

### Available Options

```bash
python mapping.py --help
```

Options include:
- `--update-openapi`: Update the main OpenAPI specification file
- `--dry-run`: Show what would be changed without making changes
- `--mapping-only`: Only generate mapping files, skip OpenAPI update
- `--verbose`: Enable verbose output
- `--quiet`: Minimal output

## Best Practices

1. **Always run the mapping script** after adding new endpoint YAML files
2. **Review changes** before committing updated OpenAPI files
3. **Test the specification** with OpenAPI tools after updates
4. **Keep schemas modular** by using the `components/schemas/` directory
5. **Use consistent naming** for YAML files following the established patterns

## File Naming Conventions

YAML files in the `paths/` directory follow these patterns:

- **Task-managed endpoints**: `task-{action}-{operation}.yaml`
  - Example: `task-enable_utxo-init.yaml`
- **Lightning endpoints**: `lightning-{category}-{action}.yaml`
  - Example: `lightning-channels-open_channel.yaml`
- **Streaming endpoints**: `stream-{type}-{action}.yaml`
  - Example: `stream-balance-enable.yaml`
- **Utility endpoints**: `utils_{action}.yaml` or simple names
  - Example: `utils_get_mnemonic.yaml`, `approve_token.yaml`

## Integration

The OpenAPI specification can be used with various tools:

- **Postman**: Import `openapi.yaml` for complete API testing
- **Swagger UI**: Host the specification for interactive documentation
- **Code Generation**: Generate client libraries in various languages
- **API Testing**: Validate requests and responses against the schema

## Troubleshooting

If you encounter issues with the mapping script:

1. Check that all required Python dependencies are installed
2. Ensure you're running from the correct directory (`utils/py/`)
3. Verify that YAML files are properly formatted
4. Check the console output for specific error messages

For questions or issues, refer to the main project documentation or create an issue in the repository. 