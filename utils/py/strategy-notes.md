- methods extracted from rust code dispatcher files. Must be massaged to include `::` prefixes to ensure correct output of the canonical method names.

- methods extracted from MDX `##` headings, where not tagged as overview OR structures. Page path stored for file mapping json. Validate output to ensure CodeGroup exists with canonical method name. If not, log to console - these may be overview pages not yet tagged.

## FIXES APPLIED (2024)

The method detection/scanning process has been fixed to address major false positive issues:

### Key Fixes:
1. **Overview/Structures Filtering**: Pages tagged as `structures` now treated same as `overview` 
2. **Streaming Method Format**: Fixed incorrect `streaming::X_enable` → correct `stream::X::enable`
3. **Category vs Method Detection**: Removed 20+ overview category false positives
4. **Existing Method Recognition**: Properly identified 17 existing methods that were incorrectly flagged as missing

### Results:
- **V2 API**: 46 → 2 missing methods (95.7% reduction)
- **V1 API**: 3 → 2 missing methods (33.3% reduction)

### Usage:
Run `python fix_method_detection.py` to generate corrected comparison reports.

See `METHOD_DETECTION_FIX_SUMMARY.md` for full details.



