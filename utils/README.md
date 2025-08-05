# Komodo Docs Utility Scripts

This directory contains utility scripts and tools for maintaining, validating, and generating documentation and data for the Komodo documentation project. Scripts are organized by language:

- [`js/`](./js): Node.js scripts for documentation validation, data extraction, and migration.
- [`py/`](./py): Python scripts for API mapping, OpenAPI conversion, example management, and Postman collection generation.

## Table of Contents

- [General Usage](#general-usage)
- [JavaScript Utilities (`js/`)](#javascript-utilities-js)
- [Python Utilities (`py/`)](#python-utilities-py)
- [Data Subfolders](#data-subfolders)
- [Dependencies](#dependencies)

---

## General Usage

- Most scripts are intended to be run from the `utils` directory.
- The `run_tests.sh` script provides a typical validation workflow for documentation changes.
- Some scripts require environment variables (e.g., GitHub tokens) for API access.

### Example: Run all main checks

```bash
cd utils
bash run_tests.sh
```

---

## JavaScript Utilities (`js/`)

Install dependencies with:

```bash
cd js
npm ci
```

### Script Index

| Script                                         | Purpose & Usage                                                                                      |
|------------------------------------------------|------------------------------------------------------------------------------------------------------|
| `create_search_index.js`                       | Builds a search index from all MDX files for fast documentation search.                              |
| `get_file_author_data.js`                      | Fetches and updates author/contributor data for documentation files using the GitHub API.            |
| `ensure_changelog_update.js`                   | Checks if changelogs are up to date with the latest Komodo and KDF releases.                         |
| `file_presence_structure_checker.js`           | Validates that all documentation directories have an `index.mdx` and that sidebar/navbar are in sync.|
| `findMissingRedirects.js`                      | Identifies missing redirects from old documentation URLs to new ones.                                |
| `h1_presence_format_checker.js`                | Ensures every MDX file has exactly one `<h1>` heading and that it is properly formatted.             |
| `validate_update_internal_links_userpass.js`   | Validates and updates internal links in MDX files, ensuring correct slugs and userpass values.       |
| `createRedirectMap.js`                         | Generates a mapping of old documentation URLs to new ones for redirect purposes.                     |
| `create_author_data_for_renamed_paths.js`      | Updates author/contributor data and redirect maps for files that have been renamed.                  |
| `create_data_for_gpts.js`                      | Aggregates and converts MDX content for use in GPT-based tools or search.                            |
| `_removed_search_words.js`                     | Contains a list of common words to exclude from search indexing.                                     |
| `constants.js`                                 | Stores project-wide constants (URLs, org info, etc.) for use in scripts.                             |

#### Data Subfolder (`js/data/`)

Contains generated and reference data files such as redirect maps, file path slugs, and sidebar structures.

---

## Python Utilities (`py/`)

Install dependencies with:

```bash
cd py
pip install -r requirements.txt
```

### Script Index

| Script                            | Purpose & Usage                                                                                                 |
|-----------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `pretty_print_md_table.py`        | Reformats markdown tables for consistent column alignment.                                                      |
| `deduplicate_examples.py`         | Finds and removes duplicate JSON example files in the Postman examples directory.                               |
| `gen_api_methods_table.py`        | Generates a markdown table of all API methods, linking to their documentation.                                  |
| `mapping.py`                      | Provides classes for mapping API methods to MDX and OpenAPI files, and for generating unified mappings.         |
| `postman_collection_generator.py` | Generates Postman collections from JSON examples, organizing them by method and category.                       |
| `api_example_manager.py`          | Extracts, deduplicates, and manages JSON API examples from MDX files and generates additional test cases.       |
| `converter.py`                    | Converts MDX documentation to OpenAPI YAML specifications using mapping and parsing classes.                    |


#### Data Subfolder (`py/data/`)

Contains mapping and metadata files for API methods, such as `unified_method_mapping.json` and `method_pages.json`.

---

## Data Subfolders

- `js/data/`: Redirect maps, file path slugs, and other JSON/TXT data for JS scripts.
- `py/data/`: Mapping and metadata for API methods, used by Python scripts.

---

## Dependencies

### JavaScript

See [`js/package.json`](./js/package.json) for a full list. Main dependencies include:

- `@mdx-js/mdx`
- `remark`, `remark-gfm`, `remark-mdx`
- `unist-util-visit`, `unist-util-is`
- `@sindresorhus/slugify`
- `axios`
- `dotenv`

Install with:

```bash
cd js
npm ci
```

### Python

See [`py/requirements.txt`](./py/requirements.txt):

- `PyYAML>=6.0`

Install with:

```bash
cd py
pip install -r requirements.txt
```

---

## Example: Running Validation and Generation

```bash
# From the utils directory
bash run_tests.sh
```

This will:
- Generate the API methods table.
- Install JS dependencies.
- Run all main JS validation and mapping scripts.

---

## Contributing

- Please ensure all scripts are well-documented and follow best practices.
- Update this README if you add or change scripts.

---

## License

See the root project license. 