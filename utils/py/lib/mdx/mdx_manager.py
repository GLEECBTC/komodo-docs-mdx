#!/usr/bin/env python3
"""
Drafts Manager

Manages the quality analysis workflow for comparing generated documentation drafts
with final live versions to identify areas for improvement in templates, style 
standards, and documentation generation quality.

This manager orchestrates the entire process from file discovery to final reporting,
providing comprehensive analysis and actionable recommendations.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from typing import Dict, List,  Optional, Union
from datetime import datetime

from lib.utils.logging_utils import get_logger
from lib.constants import DocumentDifference, QualityReport
from .mdx_analysis import DocumentAnalyzer
from ..validation.style_validator import StyleValidator
from .mdx_draft_matching import DocumentDiscoveryScanner
from lib.constants.config import get_config


class QualityReportGenerator:
    """Generates a markdown quality analysis report from a list of QualityReport objects."""
    def __init__(self, reports: List[QualityReport]):
        self.reports = reports

    def generate_markdown_report(self) -> str:
        """Generate a comprehensive markdown report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report_lines = [
            "# Documentation Draft Quality Analysis Report",
            f"\n**Generated:** {timestamp}",
            f"**Analyzed:** {len(self.reports)} document pairs\n",
            "## Executive Summary\n"
        ]
        
        if not self.reports:
            report_lines.append("No reports to analyze.")
            return '\n'.join(report_lines)
        
        # Calculate overall statistics
        total_differences = sum(len(report.differences) for report in self.reports)
        avg_similarity = sum(report.overall_similarity for report in self.reports) / len(self.reports)
        
        critical_issues = sum(len([d for d in report.differences if d.severity == "critical"]) for report in self.reports)
        major_issues = sum(len([d for d in report.differences if d.severity == "major"]) for report in self.reports)
        minor_issues = sum(len([d for d in report.differences if d.severity == "minor"]) for report in self.reports)
        
        report_lines.extend([
            f"- **Overall Similarity:** {avg_similarity:.1%}",
            f"- **Total Differences Found:** {total_differences}",
            f"- **Critical Issues:** {critical_issues}",
            f"- **Major Issues:** {major_issues}",
            f"- **Minor Issues:** {minor_issues}\n"
        ])
        
        # Add improvement opportunities, template issues, and detailed analysis
        report_lines.extend(self._generate_report_sections())
        
        return '\n'.join(report_lines)

    def _generate_report_sections(self) -> List[str]:
        """Generate the detailed sections of the markdown report."""
        sections = []
        
        # Top improvement opportunities
        all_opportunities = []
        for report in self.reports:
            all_opportunities.extend(report.improvement_opportunities)
        
        if all_opportunities:
            opportunity_counts = {}
            for opp in all_opportunities:
                opportunity_counts[opp] = opportunity_counts.get(opp, 0) + 1
            
            top_opportunities = sorted(opportunity_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            sections.extend([
                "## Top Improvement Opportunities\n",
                *(f"{i+1}. {opp} (affects {count} documents)" for i, (opp, count) in enumerate(top_opportunities)),
                "\n"
            ])
        
        # Template issues summary
        all_template_issues = []
        for report in self.reports:
            all_template_issues.extend(report.template_issues)
        
        if all_template_issues:
            template_counts = {}
            for issue in all_template_issues:
                template_counts[issue] = template_counts.get(issue, 0) + 1
            
            sections.extend([
                "## Template Issues\n",
                *(f"- {issue} (affects {count} documents)" for issue, count in sorted(template_counts.items(), key=lambda x: x[1], reverse=True)),
                "\n"
            ])
        
        # Style violations summary
        all_violations = []
        for report in self.reports:
            all_violations.extend(report.style_violations)
        
        if all_violations:
            violation_counts = {}
            for violation in all_violations:
                violation_counts[violation] = violation_counts.get(violation, 0) + 1
            
            sections.extend([
                "## Style Guide Violations\n",
                *(f"- {violation} (occurs {count} times)" for violation, count in sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                "\n"
            ])
        
        # Detailed analysis per document
        sections.append("## Detailed Analysis\n")
        
        for report in sorted(self.reports, key=lambda r: r.overall_similarity):
            sections.extend(self._generate_document_section(report))
        
        # Actionable recommendations
        sections.extend(self._generate_recommendations_section())
        
        return sections

    def _generate_document_section(self, report: QualityReport) -> List[str]:
        """Generate the detailed section for a single document."""
        lines = [
            f"### {report.method_name}",
            f"**Similarity:** {report.overall_similarity:.1%} | **Issues:** {len(report.differences)}\n"
        ]
        
        if report.differences:
            # Group by severity
            critical = [d for d in report.differences if d.severity == "critical"]
            major = [d for d in report.differences if d.severity == "major"]
            minor = [d for d in report.differences if d.severity == "minor"]
            
            if critical:
                lines.append("**Critical Issues:**")
                for diff in critical:
                    lines.append(f"- {diff.section}: {diff.description}")
            
            if major:
                lines.append("\n**Major Issues:**" if critical else "**Major Issues:**")
                for diff in major:
                    lines.append(f"- {diff.section}: {diff.description}")
            
            if minor and len(minor) <= 5:  # Only show minor if not too many
                lines.append("\n**Minor Issues:**" if (critical or major) else "**Minor Issues:**")
                for diff in minor:
                    lines.append(f"- {diff.section}: {diff.description}")
            elif minor:
                lines.append(f"\n**Minor Issues:** {len(minor)} issues (details omitted)" if (critical or major) else f"**Minor Issues:** {len(minor)} issues (details omitted)")
        
        lines.append("")
        return lines

    def _generate_recommendations_section(self) -> List[str]:
        """Generate the actionable recommendations section."""
        return [
            "## Actionable Recommendations\n",
            "### Immediate Actions\n",
            "1. **Fix critical issues** - These prevent proper documentation functionality",
            "2. **Review file generation process** - Critical issues suggest fundamental problems\n",
            "### Template Improvements\n",
            "1. **Update base templates** based on common structural differences found",
            "2. **Add validation** for required sections and formats",
            "3. **Enhance metadata generation** to match style guide requirements\n",
            "### Generation Logic Improvements\n",
            "1. **Improve content extraction** from source materials",
            "2. **Enhance example generation** with more realistic data",
            "3. **Add style guide validation** during generation process\n",
            "### Process Improvements\n",
            "1. **Implement automated quality checks** before manual review",
            "2. **Create feedback loop** from manual edits back to generation logic",
            "3. **Establish quality thresholds** for generated documentation\n"
        ]

class DraftsManager:
    """
    Manages the quality analysis of generated documentation drafts by comparing 
    them with manually reviewed live versions.
    """
    
    def __init__(self, 
                 generated_docs_dir: Optional[Path] = None,
                 live_docs_dir: Optional[Path] = None,
                 templates_dir: Optional[Path] = None,
                 style_guide: Optional[Path] = None):
        self.logger = get_logger("drafts-manager")
        self.script_dir = Path(__file__).parent.parent.parent
        
        # Set up directories
        self.generated_docs_dir = generated_docs_dir or (self.script_dir / "data" / "generated_docs")
        self.live_docs_dir = live_docs_dir or (self.script_dir.parent.parent / "src" / "pages" / "komodo-defi-framework" / "api")
        self.templates_dir = templates_dir or (self.script_dir.parent.parent / "docs" / "templates")
        self.style_guide_file = style_guide or (self.script_dir.parent.parent / "docs" / "STYLE_GUIDE.md")
        
        # Output directory for reports
        self.config = get_config()
        self.branched_reports_dir = Path(self.config._resolve_path(self.config.directories.branched_reports_dir))
        
        # Initialize utility components
        self.document_analyzer = DocumentAnalyzer()
        self.style_validator = StyleValidator()
        self.document_scanner = DocumentDiscoveryScanner(self.generated_docs_dir, self.live_docs_dir)
    
    def analyze_structural_differences(self, generated_sections: Dict[str, str], 
                                     live_sections: Dict[str, str]) -> List[DocumentDifference]:
        """Analyze structural differences between documents."""
        differences = []
        
        # Use the utility to find section differences
        missing_in_generated, extra_in_generated = self.document_analyzer.find_section_differences(
            generated_sections, live_sections
        )
        
        for missing in missing_in_generated:
            differences.append(DocumentDifference(
                section="structure",
                type="structure",
                severity="major",
                generated_content="",
                live_content=live_sections[missing][:200] + "...",
                description=f"Section '{missing}' is missing from generated documentation",
                suggestions=[
                    f"Add {missing} section to template",
                    "Update generation logic to include this section"
                ]
            ))
        
        for extra in extra_in_generated:
            differences.append(DocumentDifference(
                section="structure",
                type="structure",
                severity="minor",
                generated_content=generated_sections[extra][:200] + "...",
                live_content="",
                description=f"Extra section '{extra}' in generated documentation",
                suggestions=[
                    "Review if this section adds value",
                    "Consider removing from template if not needed"
                ]
            ))
        
        return differences
    
    def analyze_content_differences(self, generated_sections: Dict[str, str],
                                   live_sections: Dict[str, str]) -> List[DocumentDifference]:
        """Analyze content differences within matching sections."""
        differences = []
        
        common_sections = set(generated_sections.keys()) & set(live_sections.keys())
        
        for section in common_sections:
            gen_content = generated_sections[section]
            live_content = live_sections[section]
            
            if not gen_content and not live_content:
                continue
            
            # Calculate similarity using utility
            similarity = self.document_analyzer.calculate_content_similarity(gen_content, live_content)
            
            if similarity < 0.8:  # Less than 80% similar
                # Analyze the type of difference using utility
                diff_type = self.document_analyzer.classify_content_difference(gen_content, live_content, section)
                severity = self.document_analyzer.assess_difference_severity(similarity, section)
                
                differences.append(DocumentDifference(
                    section=section,
                    type=diff_type,
                    severity=severity,
                    generated_content=gen_content[:500] + "..." if len(gen_content) > 500 else gen_content,
                    live_content=live_content[:500] + "..." if len(live_content) > 500 else live_content,
                    description=f"Content difference in {section} (similarity: {similarity:.2%})",
                    suggestions=self._generate_content_suggestions(gen_content, live_content, section)
                ))
        
        return differences
    
    def _generate_content_suggestions(self, generated: str, live: str, section: str) -> List[str]:
        """Generate suggestions for improving content differences."""
        suggestions = []
        
        if "param" in section.lower():
            suggestions.extend([
                "Review parameter extraction logic",
                "Check if parameter descriptions need enhancement",
                "Verify parameter types and requirements"
            ])
        elif "example" in section.lower():
            suggestions.extend([
                "Update example generation logic",
                "Ensure examples use correct parameter values",
                "Add more realistic example data"
            ])
        elif "title" in section.lower():
            suggestions.extend([
                "Review method name humanization logic",
                "Check title format compliance",
                "Ensure titles are descriptive and consistent"
            ])
        else:
            suggestions.extend([
                "Review content generation logic for this section",
                "Compare with style guide requirements",
                "Consider manual review of generated content"
            ])
        
        return suggestions
    
    def validate_style_compliance(self, content: str) -> List[DocumentDifference]:
        """Validate content against style guide rules using the style validator."""
        differences = []
        
        # Get style violations from utility
        violations = self.style_validator.get_style_violations(content)
        
        for violation in violations:
            differences.append(DocumentDifference(
                section=violation['section'],
                type="style",
                severity="major" if violation['type'] in ['title_format', 'description_format', 'method_heading'] else "minor",
                generated_content=violation['line'],
                live_content=self._get_expected_format(violation['type']),
                description=violation['description'],
                line_numbers=(violation.get('line_number'), violation.get('line_number')) if 'line_number' in violation else None,
                suggestions=self._get_style_suggestions(violation['type'])
            ))
        
        return differences
    
    def _get_expected_format(self, violation_type: str) -> str:
        """Get expected format for a style violation type."""
        formats = {
            'title_format': 'export const title = "Komodo DeFi Framework Method: [Proper Format]";',
            'description_format': 'export const description = "[Proper description format]";',
            'method_heading': '## method_name {{label : \'method_name\', tag : \'API-v2\'}}',
            'table_header': '| Parameter | Type | Required | Default | Description |',
            'userpass_value': f'userpass should be {self.style_validator.style_rules["userpass_value"]}'
        }
        return formats.get(violation_type, "See style guide for proper format")
    
    def _get_style_suggestions(self, violation_type: str) -> List[str]:
        """Get suggestions for fixing a style violation."""
        suggestions = {
            'title_format': ["Use proper title format with 'Komodo DeFi Framework Method:' prefix"],
            'description_format': ["Ensure description is properly quoted and ends with semicolon"],
            'method_heading': ["Include proper label and tag format in method heading"],
            'table_header': ["Use proper parameter table header format"],
            'userpass_value': [f"Use {self.style_validator.style_rules['userpass_value']} for userpass in examples"]
        }
        return suggestions.get(violation_type, ["Review style guide for proper format"])
    
    def _run_all_analyses(self, generated_content: str, live_content: str, generated_sections: Dict[str, str], live_sections: Dict[str, str]) -> List[DocumentDifference]:
        """Run all analysis types and return a list of differences."""
        differences = []
        differences.extend(self.analyze_structural_differences(generated_sections, live_sections))
        differences.extend(self.analyze_content_differences(generated_sections, live_sections))
        differences.extend(self.validate_style_compliance(generated_content))
        return differences

    def _summarize_differences(self, differences: List[DocumentDifference]) -> Dict[str, List[str]]:
        """Summarize differences into categories for the report."""
        return {
            "improvement_opportunities": self._generate_improvement_opportunities(differences),
            "template_issues": self._identify_template_issues(differences),
            "style_violations": self._identify_style_violations(differences),
        }

    def analyze_single_document(self, generated_file: Path, live_file: Path) -> QualityReport:
        """Analyze a single document pair and generate a quality report."""
        self.logger.info(f"Analyzing {generated_file.name} vs {live_file.name}")
        
        # Read files
        try:
            with open(generated_file, 'r', encoding='utf-8') as f:
                generated_content = f.read()
        except Exception as e:
            self.logger.error(f"Error reading generated file {generated_file}: {e}")
            return self._create_error_report(generated_file, live_file, f"Could not read generated file: {e}")
        
        try:
            with open(live_file, 'r', encoding='utf-8') as f:
                live_content = f.read()
        except Exception as e:
            self.logger.error(f"Error reading live file {live_file}: {e}")
            return self._create_error_report(generated_file, live_file, f"Could not read live file: {e}")
        
        # Extract sections using utility
        generated_sections = self.document_analyzer.extract_document_sections(generated_content)
        live_sections = self.document_analyzer.extract_document_sections(live_content)
        
        # Calculate overall similarity using utility
        overall_similarity = self.document_analyzer.calculate_content_similarity(generated_content, live_content)
        
        # Analyze differences
        differences = self._run_all_analyses(generated_content, live_content, generated_sections, live_sections)
        
        # Extract method name
        method_name = generated_sections.get('method_name', generated_file.stem)
        
        # Generate improvement analysis
        summary = self._summarize_differences(differences)

        return QualityReport(
            method_name=method_name,
            generated_file=generated_file,
            live_file=live_file,
            overall_similarity=overall_similarity,
            differences=differences,
            template_issues=summary["template_issues"],
            style_violations=summary["style_violations"],
            improvement_opportunities=summary["improvement_opportunities"]
        )
    
    def _create_error_report(self, generated_file: Path, live_file: Path, error_message: str) -> QualityReport:
        """Create an error report when file reading fails."""
        return QualityReport(
            method_name=generated_file.stem,
            generated_file=generated_file,
            live_file=live_file,
            overall_similarity=0.0,
            differences=[DocumentDifference(
                section="file_access",
                type="critical",
                severity="critical",
                generated_content="",
                live_content="",
                description=error_message
            )]
        )
    
    def _generate_improvement_opportunities(self, differences: List[DocumentDifference]) -> List[str]:
        """Generate high-level improvement opportunities based on differences."""
        opportunities = []
        
        # Group by type
        diff_types = {}
        for diff in differences:
            if diff.type not in diff_types:
                diff_types[diff.type] = []
            diff_types[diff.type].append(diff)
        
        for diff_type, diffs in diff_types.items():
            if len(diffs) >= 3:  # If there are multiple similar issues
                opportunities.append(f"Review {diff_type} handling - {len(diffs)} issues found")
        
        # Severity-based opportunities
        critical_count = len([d for d in differences if d.severity == "critical"])
        major_count = len([d for d in differences if d.severity == "major"])
        
        if critical_count > 0:
            opportunities.append(f"Address {critical_count} critical issues immediately")
        if major_count > 2:
            opportunities.append(f"Focus on {major_count} major improvements")
        
        return opportunities
    
    def _identify_template_issues(self, differences: List[DocumentDifference]) -> List[str]:
        """Identify issues that likely stem from template problems."""
        template_issues = []
        
        structure_diffs = [d for d in differences if d.type == "structure"]
        if structure_diffs:
            template_issues.append("Template structure may need updates")
        
        metadata_diffs = [d for d in differences if d.section in ["title_export", "description_export"]]
        if metadata_diffs:
            template_issues.append("Template metadata format needs review")
        
        return template_issues
    
    def _identify_style_violations(self, differences: List[DocumentDifference]) -> List[str]:
        """Identify style guide violations."""
        violations = []
        
        style_diffs = [d for d in differences if d.type == "style"]
        for diff in style_diffs:
            violations.append(f"{diff.section}: {diff.description}")
        
        return violations
    
    def generate_markdown_report(self, reports: List[QualityReport]) -> str:
        """Generate a comprehensive markdown report."""
        generator = QualityReportGenerator(reports)
        return generator.generate_markdown_report()
    
    def analyze_all_documents(self, output_file: Optional[Path] = None) -> str:
        """Analyze all document pairs and generate a comprehensive report."""
        self.logger.info("Starting comprehensive draft quality analysis")
        
        # Find all document pairs using the scanner
        file_pairs = self.document_scanner.find_corresponding_files()
        
        if not file_pairs:
            self.logger.warning("No document pairs found for analysis")
            return "No document pairs found for analysis."
        
        # Analyze each pair
        reports = []
        for generated_file, live_file in file_pairs:
            try:
                report = self.analyze_single_document(generated_file, live_file)
                reports.append(report)
            except Exception as e:
                self.logger.error(f"Error analyzing {generated_file}: {e}")
        
        # Generate markdown report
        markdown_report = self.generate_markdown_report(reports)
        
        # Save report
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.branched_reports_dir / f"quality_report.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        self.logger.success(f"Generated quality report: {output_file}")
        
        return markdown_report
    
    def review_draft_quality(self, 
                            generated_path: Optional[Union[str, Path]] = None,
                            live_path: Optional[Union[str, Path]] = None,
                            output_file: Optional[Union[str, Path]] = None) -> str:
        """High-level function to review draft quality."""
        
        if generated_path and live_path:
            # Analyze a single pair
            report = self.analyze_single_document(Path(generated_path), Path(live_path))
            markdown_report = self.generate_markdown_report([report])
        else:
            # Analyze all documents
            markdown_report = self.analyze_all_documents(Path(output_file) if output_file else None)
        
        return markdown_report

# Convenience function for external use
def review_draft_quality(generated_path: Optional[Union[str, Path]] = None,
                        live_path: Optional[Union[str, Path]] = None,
                        output_file: Optional[Union[str, Path]] = None) -> str:
    """
    Convenience function to run the draft quality analysis.
    
    Can be used to analyze a single pair of documents or all available pairs.
    """
    manager = DraftsManager()
    return manager.review_draft_quality(generated_path, live_path, output_file)


if __name__ == "__main__":
    # Example usage
    manager = DraftsManager()
    report = manager.analyze_all_documents()
    print("Quality analysis complete. Report generated.") 