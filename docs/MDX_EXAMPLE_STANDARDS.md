# MDX Example Standards

> **Purpose:** This document defines the standards for creating, naming, and maintaining MDX examples in this repository. All contributors must follow these guidelines to ensure clarity, uniqueness, and maintainability of documentation examples.

## Why Standards Matter
- **Clarity:** Unique, descriptive examples help users understand real-world use cases.
- **Maintainability:** Avoiding duplication and generic names keeps the documentation clean and easy to update.
- **Automation:** Our CI checks rely on these standards to validate contributions.

## Naming Conventions
- **Be Descriptive:** Example filenames and titles must describe the use case, not just the order (e.g., avoid "Example 1").
- **Format:** Use kebab-case for filenames (e.g., `withdraw-example-multiple-assets.json`).
- **Avoid Generic Names:** Do not use names like `basic_request` or `task_operation` unless absolutely necessary and unique.
- **Include Context:** If the example demonstrates a specific scenario (e.g., error, edge case), include that in the name (e.g., `withdraw-example-insufficient-funds.json`).

### Examples
- Good: `orderbook-example-buy-limit-order.json`
- Good: `withdraw-example-multiple-assets.json`
- Bad: `orderbook-example-1-basic_request.json`
- Bad: `withdraw-example-task_operation-2.json`

## What Makes a Good Example?
- **Distinct Use Case:** Each example should demonstrate a unique scenario or feature.
- **Descriptive Name:** The name should make it clear what the example shows.
- **Complete and Minimal:** Include all required parameters, but avoid unnecessary complexity.
- **Follow Style Guide:** All code and documentation must follow the [STYLE_GUIDE.md](STYLE_GUIDE.md).

## Avoiding Duplication
- **Consolidate Identical Examples:** If two examples are identical, keep only one and remove the rest.
- **One Example per Scenario:** Only create multiple examples for genuinely different scenarios.
- **Check Before Adding:** Search for existing examples before creating a new one.
- **Automation:** The CI will fail if more than 10% of examples are duplicates. Run the deduplication script before submitting:

## Removing duplication
Use the script `utils/py/deduplicate_examples.py`

  ```bash
    usage: deduplicate_examples.py [-h] [--dry-run] [--execute] [--versions {v1,v2} [{v1,v2} ...]] [--base-path BASE_PATH] [--verbose] [--quiet]

    Deduplicate JSON example files by content

    options:
    -h, --help            show this help message and exit
    --dry-run             Show what would be done without making changes (default: True)
    --execute             Actually perform the deduplication (overrides --dry-run)
    --versions {v1,v2} [{v1,v2} ...]
                            API versions to process (default: both)
    --base-path BASE_PATH
                            Base path to JSON examples (default: ../../postman/json/kdf)
    --verbose, -v         Enable verbose output (default: True)
    --quiet, -q           Minimal output
  ```

## Contributor Checklist
- [ ] Is my example name descriptive and unique?
- [ ] Does my example demonstrate a distinct use case?
- [ ] Have I checked for and avoided duplication?
- [ ] Does my example follow the [STYLE_GUIDE.md](STYLE_GUIDE.md) and repo rules?
- [ ] Have I updated the sidebar if a new documentation page was added?

## References
- [STYLE_GUIDE.md](STYLE_GUIDE.md)
- [Repo Documentation Rules](../README.md)

---

**Remember:** High-quality, unique examples make the documentation more valuable for everyone. Thank you for contributing! 