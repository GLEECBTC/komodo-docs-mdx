# KDF Documentation Auto-Generator

A comprehensive tool that automatically generates documentation for missing KDF API methods by analyzing the KDF repository and populating MDX templates.
https://github.com/KomodoPlatform/komodo-docs-mdx/blob/85064f797d51899ccc33ed9d1193dc83e094ef36/utils/py/kdf_docs_autogen.py
## Features

- 🔍 **Automatic Method Discovery**: Loads missing methods from `unified_method_mapping.json`
- 🤖 **Repository Analysis**: Scans the KDF repository to extract method information
- 📄 **Template Population**: Uses the comprehensive MDX template with intelligent parameter inference
- 📂 **Organized Output**: Saves generated docs to structured directories in `generated_docs/`
- 🚀 **Multiple Generation Modes**: Interactive, single method, or batch generation
- ⚡ **Async Processing**: High-performance async operations for fast generation

## Installation

The tool uses the existing library components in the `utils/py` directory. Make sure you have the required dependencies:

```bash
cd utils/py
pip install -r requirements.txt
```

## Usage

### 1. List Missing Methods

See all methods that need documentation:

```bash
python kdf_docs_autogen.py --list-missing
```

### 2. Interactive Mode (Recommended)

Run the tool interactively to select methods:

```bash
python kdf_docs_autogen.py
```

This will:
- Display all missing methods
- Allow you to select specific methods by number (e.g., `1,3,5` or `1-10`)
- Or select `all` to generate docs for all methods
- Show progress during generation

### 3. Single Method Generation

Generate documentation for a specific method:

```bash
python kdf_docs_autogen.py --method "task::enable_erc20::cancel"
python kdf_docs_autogen.py --method "gui_storage::add_account"
python kdf_docs_autogen.py --method "autoprice"
```

### 4. Generate All Missing Methods

Generate documentation for all missing methods at once:

```bash
python kdf_docs_autogen.py --generate-all
```

### 5. Quiet Mode

Run with minimal output:

```bash
python kdf_docs_autogen.py --quiet --method "task::enable_erc20::cancel"
```

## Generated Documentation

### Output Structure

Generated documentation is saved to:
```
utils/py/data/generated_docs/
├── v1/
│   ├── autoprice/
│   │   └── index.mdx
│   └── fundvalue/
│       └── index.mdx
└── v2/
    ├── task/
    │   ├── enable_erc20/
    │   │   ├── cancel/
    │   │   │   └── index.mdx
    │   │   ├── init/
    │   │   │   └── index.mdx
    │   │   └── status/
    │   │       └── index.mdx
    │   └── enable_lightning/
    │       └── user_action/
    │           └── index.mdx
    ├── gui_storage/
    │   ├── add_account/
    │   │   └── index.mdx
    │   └── activate_coins/
    │       └── index.mdx
    └── account_balance/
        └── index.mdx
```

### Documentation Content

Each generated MDX file includes:

- **Header**: Proper `export const title` and `description` 
- **Human-readable title**: Converted method names (e.g., "Cancel Enable ERC20 Task")
- **Method section**: Exact API method name with appropriate tags
- **Parameter tables**: Inferred request parameters with types and descriptions
- **Response structure**: Expected response parameters based on method analysis
- **Error types**: Common and method-specific error conditions
- **Template structure**: Ready for manual refinement and examples

### What Gets Inferred

The tool automatically infers:

1. **Method Classification**: Task, streaming, lightning, GUI storage, etc.
2. **Parameters**: Based on method patterns:
   - Task methods: `task_id` for status/cancel, `coin` for enable operations
   - Lightning methods: `coin` parameter
   - GUI storage methods: `account_id` for account operations
   - All methods: `userpass` for RPC authorization

3. **Response Structure**: Based on method type:
   - Task init: `task_id` and `result`
   - Task status: `status` and `details`
   - Task cancel: `result`
   - Other methods: Generic `result` object

4. **Error Types**: Common errors plus method-specific ones:
   - All methods: `InvalidRequest`, `InternalError`
   - Coin methods: `NoSuchCoin`
   - Task methods: `NoSuchTask`
   - Lightning methods: `LightningError`

## Review and Integration

### Manual Review Required

Generated documentation serves as a starting point and requires manual review:

1. **Verify Parameters**: Check parameter types and add missing ones
2. **Update Descriptions**: Improve parameter and response descriptions
3. **Add Examples**: Create realistic request/response examples
4. **Fix Placeholders**: Remove template placeholders like `[param1]`
5. **Add Context**: Include method-specific context and usage notes

### Integration Process

1. Review generated files in `generated_docs/`
2. Move completed documentation to appropriate locations in `src/pages/`
3. Update `sidebar.json` with new method entries
4. Test documentation locally before committing

## Tool Architecture

### Components Used

- **KDFRepositoryScanner**: Scans the KDF repository for method information
- **AsyncFileProcessor**: High-performance async file operations
- **Template System**: Uses `komodefi_method_comprehensive.mdx` template
- **Method Analysis**: Intelligent parameter and response inference
- **Progress Tracking**: Real-time progress feedback

### Data Sources

- **Missing Methods**: `data/unified_method_mapping.json`
- **Repository Data**: Live fetch from KDF repository on GitHub
- **Template**: `docs/templates/komodefi_method_comprehensive.mdx`

## Examples

### Example Generated Output

For the method `task::enable_erc20::cancel`, the tool generates:

```mdx
export const title = "Komodo DeFi Framework Method: Cancel Enable ERC20 Task";
export const description = "Cancels the enable ERC20 task operation in the Komodo DeFi Framework.";

# Cancel Enable ERC20 Task

## task::enable_erc20::cancel {{label : 'task::enable_erc20::cancel', tag : 'API-v2'}}

### Request Parameters

| Parameter | Type   | Required | Description                                   |
| --------- | ------ | :------: | --------------------------------------------- |
| userpass  | string |    ✓     | The user's password for RPC authorization.   |
| task_id   | number |    ✓     | The identifier of the task to query or cancel.|

### Response Parameters

| Parameter | Type   | Description                               |
| --------- | ------ | ----------------------------------------- |
| result    | string | Result of the cancellation operation      |
```

## Troubleshooting

### Common Issues

1. **Method not found**: Ensure the method name is exactly as listed in `--list-missing`
2. **Template not found**: Verify `docs/templates/komodefi_method_comprehensive.mdx` exists
3. **Network errors**: Repository scanning requires internet access
4. **Permission errors**: Ensure write permissions to `generated_docs/` directory

### Debug Mode

For debugging, run with verbose logging:

```bash
python kdf_docs_autogen.py --method "your_method" --verbose
```

## Contributing

The tool is designed to be extensible:

- **Parameter Inference**: Add new patterns in `infer_basic_parameters()`
- **Response Analysis**: Extend `infer_basic_response()` for new method types
- **Error Detection**: Add method-specific errors in `infer_basic_errors()`
- **Template Enhancement**: Improve the MDX template population logic

## Future Enhancements

- [ ] Enhanced repository analysis with actual parameter extraction from Rust code
- [ ] Integration with existing documentation for cross-references
- [ ] Automatic example generation from Postman collections
- [ ] Validation of generated documentation against style guide
- [ ] Direct integration with the main documentation build process 