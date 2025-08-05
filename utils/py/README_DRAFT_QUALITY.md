# Draft Quality Analysis

This module provides comprehensive analysis of generated documentation drafts by comparing them with manually reviewed live versions. It helps identify areas for improvement in templates, style standards, and documentation generation quality.

## Overview

The Draft Quality Analyzer compares generated documentation with final live versions to:

- **Identify structural differences** between generated and live documents
- **Analyze content variations** and their impact on documentation quality
- **Validate style guide compliance** across all generated documents
- **Generate actionable recommendations** for improving the generation process
- **Track template effectiveness** and suggest improvements
- **Provide quality metrics** to measure generation success

## Key Features

### 🔍 **Comprehensive Analysis**
- Document structure comparison
- Content similarity analysis
- Style guide compliance validation
- Template usage evaluation
- Error pattern identification

### 📊 **Quality Metrics**
- Overall similarity scores
- Issue categorization (critical, major, minor)
- Template effectiveness ratings
- Style compliance percentages
- Improvement opportunity identification

### 📋 **Detailed Reporting**
- Markdown reports with executive summaries
- Per-document analysis breakdown
- Actionable improvement recommendations
- Template and style violation summaries
- Progress tracking over time

### 🛠️ **Integration Ready**
- Command-line interface
- Programmatic API access
- Makefile targets for easy execution
- Flexible configuration options
- Automated report generation

## Usage

### Command Line Interface

```bash
# Basic usage - analyze all document pairs
python kdf_tools.py review-draft-quality

# Analyze specific document pair
python kdf_tools.py review-draft-quality \
  --generated data/generated_docs/v2/task/enable_bch/init/index.mdx \
  --live src/pages/komodo-defi-framework/api/v20/coin_activation/task_managed/enable_bch/init/index.mdx

# Custom output file
python kdf_tools.py review-draft-quality --output my_quality_report.md

# Verbose analysis
python kdf_tools.py review-draft-quality --verbose

# Dry run to see what would be analyzed
python kdf_tools.py review-draft-quality --dry-run

# Show help for all options
python kdf_tools.py review-draft-quality --help
```

### Makefile Targets

```bash
# Review draft quality
make review-draft-quality

# Verbose review
make review-draft-quality-verbose

# Review specific document pair
make review-draft-quality-specific GENERATED=path/to/gen.mdx LIVE=path/to/live.mdx

# Dry run
make dry-run-quality-review
```

### Programmatic Usage

```python
from lib import DraftQualityAnalyzer, review_draft_quality

# Quick analysis of all documents
report = review_draft_quality()
print(report)

# Analyze specific files
report = review_draft_quality(
    generated_path="path/to/generated.mdx",
    live_path="path/to/live.mdx"
)

# Advanced usage with custom analyzer
analyzer = DraftQualityAnalyzer(
    generated_docs_dir=Path("custom/generated"),
    live_docs_dir=Path("custom/live")
)
report = analyzer.analyze_all_documents()
```

## Analysis Categories

### 1. **Structural Analysis**
Compares document organization and section hierarchy:
- Missing or extra sections
- Heading structure variations
- Component usage differences
- Content organization patterns

### 2. **Content Analysis**
Examines content quality and accuracy:
- Parameter table completeness
- Example accuracy and relevance
- Description quality and clarity
- Error handling coverage

### 3. **Style Compliance**
Validates adherence to style guide rules:
- Title and description formats
- Method heading patterns
- Parameter table formatting
- Required value standards (e.g., userpass)

### 4. **Template Effectiveness**
Evaluates how well templates serve their purpose:
- Template coverage of live document features
- Missing template sections
- Template customization needs
- Generation logic gaps

## Report Structure

### Executive Summary
- Overall similarity metrics
- Total issues by severity
- Top improvement opportunities
- Key recommendations

### Template Issues
- Common structural problems
- Missing template sections
- Format inconsistencies
- Generation logic gaps

### Style Guide Violations
- Format compliance issues
- Required value problems
- Naming convention violations
- Component usage errors

### Detailed Analysis
Per-document breakdown including:
- Similarity scores
- Issue categorization
- Specific recommendations
- Priority rankings

### Actionable Recommendations
- Immediate action items
- Template improvements
- Generation logic enhancements
- Process improvements

## Configuration

### Directory Paths
```python
# Default paths (can be customized)
generated_docs_dir = "utils/py/data/generated_docs"
live_docs_dir = "src/pages/komodo-defi-framework/api"
templates_dir = "docs/templates"
style_guide = "docs/STYLE_GUIDE.md"
```

### Analysis Parameters
```python
# Similarity thresholds
similarity_threshold = 0.8  # Flag differences below 80% similarity
critical_threshold = 0.3    # Critical issues below 30% similarity
major_threshold = 0.6       # Major issues below 60% similarity
```

### Style Rules
The analyzer validates against comprehensive style rules:
- Title format: `"Komodo DeFi Framework Method: ..."`
- Method headings: `## method_name {{label : 'method_name', tag : 'API-v2'}}`
- Parameter tables: Proper column formats and content
- Required values: Standard userpass, default formatting
- Component usage: Proper MDX component syntax

## Integration Workflow

### 1. **Generation Phase**
Generate documentation using existing tools:
```bash
# Generate docs using existing tools
make generate-docs
```

### 2. **Quality Analysis**
Run quality analysis on generated drafts:
```bash
# Analyze draft quality
make review-draft-quality
```

### 3. **Review Reports**
Examine generated quality reports:
- Executive summary for quick overview
- Detailed analysis for specific issues
- Actionable recommendations for improvements

### 4. **Implement Improvements**
Based on report recommendations:
- Update templates for structural issues
- Enhance generation logic for content problems
- Fix style guide compliance issues
- Improve example generation

### 5. **Re-generate and Validate**
Test improvements:
```bash
# Re-generate with improvements
make generate-docs

# Validate improvements
make review-draft-quality
```

## Benefits

### 📈 **Continuous Improvement**
- Track quality metrics over time
- Identify trending issues
- Measure improvement effectiveness
- Guide development priorities

### ⚡ **Efficiency Gains**
- Reduce manual review time
- Focus effort on high-impact issues
- Automate quality validation
- Streamline documentation workflow

### 🎯 **Quality Assurance**
- Ensure consistent documentation quality
- Validate style guide compliance
- Catch issues before manual review
- Maintain documentation standards

### 🔧 **Development Insights**
- Understand template effectiveness
- Identify generation logic gaps
- Guide tool improvements
- Inform best practices

## Future Enhancements

### Planned Features
- **JSON output format** for programmatic processing
- **Historical analysis** to track quality trends over time
- **Template suggestion engine** based on analysis patterns
- **Automated fix suggestions** for common issues
- **Integration with CI/CD pipelines** for continuous quality monitoring

### Potential Improvements
- Machine learning-based content quality scoring
- Automated template updates based on live document patterns
- Real-time quality feedback during generation
- Advanced diff visualization
- Quality trend dashboards

## Contributing

To enhance the draft quality analyzer:

1. **Add new analysis patterns** in `_init_analysis_patterns()`
2. **Extend style rule validation** in `_load_style_rules()`
3. **Improve content classification** in `_classify_content_difference()`
4. **Add new report sections** in `generate_markdown_report()`
5. **Enhance CLI options** in `review_draft_quality.py`

## Examples

### Sample Report Output

```markdown
# Documentation Draft Quality Analysis Report

**Generated:** 2025-01-17 10:30:00
**Analyzed:** 12 document pairs

## Executive Summary

- **Overall Similarity:** 72.3%
- **Total Differences Found:** 45
- **Critical Issues:** 3
- **Major Issues:** 18
- **Minor Issues:** 24

## Top Improvement Opportunities

1. Review parameter table formatting - affects 8 documents
2. Enhance example generation logic - affects 6 documents
3. Fix template metadata format - affects 5 documents
4. Address style guide compliance - affects 9 documents

## Template Issues

- Template structure may need updates (affects 7 documents)
- Template metadata format needs review (affects 5 documents)

## Actionable Recommendations

### Immediate Actions
1. **Fix 3 critical issues** - These prevent proper documentation functionality
2. **Review file generation process** - Critical issues suggest fundamental problems

### Template Improvements
1. **Update base templates** based on common structural differences found
2. **Add validation** for required sections and formats
3. **Enhance metadata generation** to match style guide requirements
```

This tool provides the feedback loop needed to continuously improve documentation generation quality, ensuring that generated drafts require minimal manual review and consistently meet documentation standards. 