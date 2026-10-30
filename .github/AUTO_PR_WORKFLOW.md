# Auto PR from Issues Workflow

## Overview

This workflow automatically scans open issues labeled with "auto PR" and creates pull requests with the required documentation updates for KDF (Komodo DeFi Framework) methods.

## How It Works

### 1. Issue Scanning
- Runs daily at 4:30 AM UTC
- Can be triggered manually via GitHub Actions UI
- Scans for open issues with the "auto PR" label

### 2. Content Parsing
The script parses issue content to extract:
- **Method names**: KDF method names (e.g., `task::enable_utxo::init`)
- **File paths**: Specific documentation paths if mentioned
- **Categories**: Method categories (lightning, wallet, swap, etc.)

### 3. Documentation Generation
- Converts KDF method names to filesystem paths following the naming convention
- Determines appropriate API version directory (legacy, v20, v20-dev)
- Generates MDX documentation using:
  - AI-powered content generation (if OpenAI API key is available)
  - Template-based generation (fallback)

### 4. PR Creation
- Creates a new branch: `auto-pr/issue-{number}`
- Commits generated documentation files
- Creates pull request targeting the `dev` branch
- Adds appropriate labels and links back to the original issue

## Issue Format Requirements

For the workflow to process an issue correctly, include:

```markdown
**Method**: `task::enable_utxo::init`
**Type**: wallet activation
**Description**: Enable UTXO coin activation method

Additional details about the method functionality...
```

### Supported Patterns

The script recognizes these patterns in issue content:
- `method: method_name`
- `function: function_name`
- `rpc: rpc_name`
- `path: file/path`
- `type: category`

## Naming Conventions

The workflow follows the KDF naming conventions:

- **Canonical form**: `task::enable_utxo::init`
- **File/folder name**: `task-enable_utxo-init` (:: → -, underscores preserved)
- **API versioning**:
  - Methods with `::` → `v20-dev`
  - Lightning/task methods → `v20`
  - Other methods → `legacy`

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub Actions token | Yes |
| `OPENAI_API_KEY` | OpenAI API key for AI generation | No |
| `TARGET_OWNER` | Repository owner | Yes |
| `TARGET_REPO` | Repository name | Yes |
| `AUTO_PR_LABEL` | Label to scan for | Yes |

### Manual Execution

```bash
# Dry run mode
DRY_RUN=true node scripts/auto-pr-from-issues.js

# Process specific issues
SPECIFIC_ISSUES="123,456" node scripts/auto-pr-from-issues.js

# Normal execution
node scripts/auto-pr-from-issues.js
```

## Generated Documentation Structure

The workflow creates documentation files following this structure:

```
src/pages/komodo-defi-framework/api/
├── legacy/
├── v20/
│   ├── lightning/
│   ├── wallet/
│   ├── task_managed/
│   └── ...
└── v20-dev/
    ├── lightning/
    ├── wallet/
    └── ...
```

## Example Workflow

1. **Issue Created**: Developer creates issue with "auto PR" label
2. **Daily Scan**: Workflow runs and detects the issue
3. **Parsing**: Extracts method `lightning::channels::open_channel`
4. **Generation**: Creates documentation in `v20-dev/lightning/`
5. **PR Creation**: Creates PR with generated documentation
6. **Review**: Team reviews and merges the PR
7. **Issue Closure**: PR merge automatically closes the issue

## Features

### AI-Powered Generation
- Uses OpenAI GPT-4o-mini for comprehensive documentation
- Generates request/response tables, examples, and descriptions
- Falls back to template generation if API unavailable

### Error Handling
- Robust error handling with detailed logging
- Automatic cleanup of failed branches
- Comprehensive statistics reporting

### Repository Integration
- Follows existing Git flow (targets `dev` branch)
- Uses established labeling conventions
- Integrates with existing Python virtual environment

## Monitoring

The workflow provides detailed logs and summaries:
- Issues processed/skipped/errored
- Generated files and their locations
- PR creation status and links

## Troubleshooting

### Common Issues

1. **No methods detected**: Ensure issue content follows the expected patterns
2. **Git conflicts**: Workflow automatically pulls latest `dev` branch
3. **API rate limits**: Built-in throttling and retry mechanisms
4. **File permissions**: Workflow runs with appropriate GitHub permissions

### Debug Mode

Enable debug output by setting environment variables:
```bash
DEBUG=true DRY_RUN=true node scripts/auto-pr-from-issues.js
```
