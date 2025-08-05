#!/usr/bin/env python3
"""
Mapping Reporter

Handles detailed reporting and statistics for mapping operations.
Provides formatted summaries and analysis reports for method mappings.
"""

from typing import Dict, List, Optional
from datetime import datetime
from .base_reporter import BaseReporter
from ..constants import MethodMapping


class MappingReporter(BaseReporter):
    """
    Generates detailed reports and statistics for mapping operations.
    Provides comprehensive analysis of method coverage and file associations.
    """
    
    def generate_summary_report(self, unified: Dict[str, Dict[str, 'MethodMapping']]) -> str:
        """Generate a comprehensive mapping statistics report."""
        return self.generate_detailed_mapping_stats(unified)
    
    def generate_detailed_mapping_stats(self, unified: Dict[str, Dict[str, 'MethodMapping']]) -> str:
        """Generate a comprehensive mapping statistics report."""
        lines = self._build_summary_header(unified)
        
        # Generate detailed version-specific stats
        for version in ["v1", "v2"]:
            lines.extend(self._generate_version_stats(version, unified[version]))
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def _build_summary_header(self, unified: Dict[str, Dict[str, 'MethodMapping']]) -> List[str]:
        """Build the summary header section."""
        # Consolidate v2-dev with v2 for statistics (v2-dev is just an alias of v2)
        consolidated_unified = {}
        
        for version, methods in unified.items():
            if version == "v2-dev":
                # Merge v2-dev methods with v2
                if "v2" not in consolidated_unified:
                    consolidated_unified["v2"] = {}
                consolidated_unified["v2"].update(methods)
            else:
                consolidated_unified[version] = methods
        
        total_methods = sum(len(methods) for methods in consolidated_unified.values())
        v1_methods = len(consolidated_unified.get("v1", {}))
        v2_methods = len(consolidated_unified.get("v2", {}))
        
        return [
            f"\n{'=' * 60}",
            f"MAPPING SUMMARY",
            f"{'=' * 60}",
            f"Total methods: {total_methods}",
            f"  v1: {v1_methods} methods",
            f"  v2: {v2_methods} methods"
        ]
    
    def _generate_version_stats(self, version: str, mappings: Dict[str, 'MethodMapping']) -> List[str]:
        """Generate detailed statistics for a specific version."""
        lines = []
        
        # Calculate coverage statistics
        coverage_stats = self._calculate_coverage_stats(mappings.values())
        total_methods = len(mappings)
        
        # Helper function using base class method
        def calc_pct(count: int) -> str:
            return self.format_percentage(count, total_methods)
        
        lines.extend([
            f"\n{version.upper()} Coverage:",
            f"  ✅ Complete (JSON, MDX & YAML): {coverage_stats['all_three']} {calc_pct(coverage_stats['all_three'])}",
            f"  📚 MDX + YAML (missing JSON): {coverage_stats['mdx_yaml_only']} {calc_pct(coverage_stats['mdx_yaml_only'])}",
            f"  🔬 MDX + JSON (missing YAML): {coverage_stats['mdx_json_only']} {calc_pct(coverage_stats['mdx_json_only'])}",
            f"  📊 YAML + JSON (missing MDX): {coverage_stats['yaml_json_only']} {calc_pct(coverage_stats['yaml_json_only'])}",
            f"  📄 MDX only (missing YAML & JSON): {coverage_stats['mdx_only']} {calc_pct(coverage_stats['mdx_only'])}",
            f"  📋 YAML only (missing MDX & JSON): {coverage_stats['yaml_only']} {calc_pct(coverage_stats['yaml_only'])}",
            f"  🧪 JSON only (missing MDX & YAML): {coverage_stats['json_only']} {calc_pct(coverage_stats['json_only'])}",
            f"  ❌ Missing all three: {coverage_stats['missing_all']} {calc_pct(coverage_stats['missing_all'])}",
        ])
        
        # Enhanced example statistics breakdown
        example_stats = self._calculate_detailed_example_stats(mappings.values())
        lines.extend([
            f"  🧪 Postman JSON Examples: {example_stats['with_examples']}/{len(mappings)} "
            f"({example_stats['coverage_pct']:.1f}%) - {example_stats['total_examples']} total examples"
        ])
        
        # Add detailed coverage breakdown
        if example_stats['methods_with_examples']:
            lines.append(f"      📄 Methods with documentation: {example_stats['with_mdx']}")
            lines.append(f"      📋 Methods with YAML specs: {example_stats['with_yaml']}")
            lines.append(f"      🔗 Methods with both MDX + JSON: {example_stats['mdx_and_examples']}")
            lines.append(f"      ⚠️  Methods with only JSON examples: {example_stats['examples_only']}")
        
        # Detailed breakdowns for missing items
        if coverage_stats['mdx_yaml_only_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods with MDX + YAML (missing JSON) ({version}):",
                coverage_stats['mdx_yaml_only_list']
            ))
        
        if coverage_stats['mdx_only_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods with MDX only (missing YAML & JSON) ({version}):",
                coverage_stats['mdx_only_list']
            ))
        
        if coverage_stats['yaml_only_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods with YAML only (missing MDX & JSON) ({version}):",
                coverage_stats['yaml_only_list']
            ))
        
        if coverage_stats['json_only_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods with JSON only (missing MDX & YAML) ({version}):",
                coverage_stats['json_only_list']
            ))
        
        if coverage_stats['missing_all_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods missing all three ({version}):",
                coverage_stats['missing_all_list']
            ))
        
        return lines
    
    def _calculate_coverage_stats(self, mappings) -> Dict:
        """Calculate coverage statistics for a set of mappings."""
        mappings_list = list(mappings)
        
        # All 8 possible combinations
        all_three_list = [m for m in mappings_list if m.has_mdx and m.has_yaml and m.has_examples]
        mdx_yaml_only_list = [m for m in mappings_list if m.has_mdx and m.has_yaml and not m.has_examples]
        mdx_json_only_list = [m for m in mappings_list if m.has_mdx and not m.has_yaml and m.has_examples]
        yaml_json_only_list = [m for m in mappings_list if not m.has_mdx and m.has_yaml and m.has_examples]
        mdx_only_list = [m for m in mappings_list if m.has_mdx and not m.has_yaml and not m.has_examples]
        yaml_only_list = [m for m in mappings_list if not m.has_mdx and m.has_yaml and not m.has_examples]
        json_only_list = [m for m in mappings_list if not m.has_mdx and not m.has_yaml and m.has_examples]
        missing_all_list = [m for m in mappings_list if not m.has_mdx and not m.has_yaml and not m.has_examples]
        
        return {
            'all_three': len(all_three_list),
            'mdx_yaml_only': len(mdx_yaml_only_list),
            'mdx_json_only': len(mdx_json_only_list),
            'yaml_json_only': len(yaml_json_only_list),
            'mdx_only': len(mdx_only_list),
            'yaml_only': len(yaml_only_list),
            'json_only': len(json_only_list),
            'missing_all': len(missing_all_list),
            'all_three_list': all_three_list,
            'mdx_yaml_only_list': mdx_yaml_only_list,
            'mdx_json_only_list': mdx_json_only_list,
            'yaml_json_only_list': yaml_json_only_list,
            'mdx_only_list': mdx_only_list,
            'yaml_only_list': yaml_only_list,
            'json_only_list': json_only_list,
            'missing_all_list': missing_all_list
        }
    
    def _calculate_detailed_example_stats(self, mappings) -> Dict:
        """Calculate detailed example statistics for a set of mappings."""
        mappings_list = list(mappings)
        with_examples = [m for m in mappings_list if m.has_examples]
        total_examples = sum(m.example_count for m in mappings_list)
        coverage_pct = (len(with_examples) / len(mappings_list) * 100) if mappings_list else 0
        
        with_mdx = len([m for m in with_examples if m.has_mdx])
        with_yaml = len([m for m in with_examples if m.has_yaml])
        mdx_and_examples = len([m for m in with_examples if m.has_mdx and m.has_yaml])
        examples_only = len([m for m in with_examples if not m.has_mdx and not m.has_yaml])
        
        return {
            'with_examples': len(with_examples),
            'total_examples': total_examples,
            'coverage_pct': coverage_pct,
            'with_mdx': with_mdx,
            'with_yaml': with_yaml,
            'mdx_and_examples': mdx_and_examples,
            'examples_only': examples_only,
            'methods_with_examples': len(with_examples)
        }
    
    def _generate_missing_section(self, header: str, missing_list: List['MethodMapping']) -> List[str]:
        """Generate a section for missing items."""
        lines = [header]
        
        for mapping in sorted(missing_list, key=lambda x: x.method):
            examples_info = f" [{mapping.example_count} examples]" if mapping.has_examples else ""
            lines.append(f"    - {mapping.method}{examples_info}")
        
        return lines
    
    def generate_debug_report(self, method_name: str, version: str, 
                            mdx_mappings: Dict, yaml_mappings: Dict, 
                            example_mappings: Dict, variations: List[str]) -> str:
        """Generate a debug report for a specific method."""
        lines = [
            "=" * 60,
            f"DEBUG REPORT FOR: {method_name} (version: {version})",
            f"Generated at: {datetime.now().isoformat()}",
            "=" * 60
        ]
        
        # MDX mappings
        lines.extend(self._generate_debug_section(
            "MDX Mappings", method_name, mdx_mappings, variations
        ))
        
        # YAML mappings
        lines.extend(self._generate_debug_section(
            "YAML Mappings", method_name, yaml_mappings, variations
        ))
        
        # Example mappings
        lines.extend(self._generate_example_debug_section(
            "Example Mappings", method_name, example_mappings, variations
        ))
        
        return "\n".join(lines)
    
    def _generate_debug_section(self, header: str, method_name: str, 
                              mapping_dict: Dict, variations: List[str]) -> List[str]:
        """Generate a debug section for a specific mapping type."""
        lines = [f"\n--- {header} ---"]
        
        match_found = self._find_debug_match(method_name, mapping_dict, variations)
        
        if match_found:
            lines.append(f"  ✅ Match found: {match_found}")
            lines.append(f"     Path: {mapping_dict[match_found].path}")
        else:
            lines.append(f"  ❌ No direct match found for: {method_name}")
            similar_methods = self._find_similar_methods(method_name, mapping_dict)
            if similar_methods:
                lines.append("     Similar methods found:")
                for sim_method in similar_methods:
                    lines.append(f"       - {sim_method}")
            else:
                lines.append("     No similar methods found.")
                
        return lines
    
    def _generate_example_debug_section(self, header: str, method_name: str, 
                                      example_mappings: Dict, variations: List[str]) -> List[str]:
        """Generate a debug section for example mappings."""
        lines = [f"\n--- {header} ---"]
        
        match_found = self._find_debug_match(method_name, example_mappings, variations)
        
        if match_found:
            mapping = example_mappings[match_found]
            lines.append(f"  ✅ Match found: {match_found}")
            lines.append(f"     File Count: {len(mapping.files)}")
            for f in mapping.files[:5]:  # show first 5 files
                lines.append(f"       - {f}")
            if len(mapping.files) > 5:
                lines.append("       ...")
        else:
            lines.append(f"  ❌ No direct match found for: {method_name}")
            similar_methods = self._find_similar_methods(method_name, example_mappings)
            if similar_methods:
                lines.append("     Similar methods found:")
                for sim_method in similar_methods:
                    lines.append(f"       - {sim_method}")
            else:
                lines.append("     No similar methods found.")
                
        return lines
    
    def _find_debug_match(self, method_name: str, mapping_dict: Dict, variations: List[str]):
        """Find a match for a method name in a mapping dictionary."""
        for var in variations:
            if var in mapping_dict:
                return var
        return None
    
    def _find_similar_methods(self, method_name: str, mapping_dict: Dict) -> List[str]:
        """Find similar methods using fuzzy matching or other heuristics."""
        from rapidfuzz import process, fuzz
        
        candidates = list(mapping_dict.keys())
        # Use a reasonably high score to avoid irrelevant matches
        results = process.extract(method_name, candidates, scorer=fuzz.token_sort_ratio, limit=5, score_cutoff=70)
        
        return [res[0] for res in results]

    def generate_coverage_summary(self, unified: Dict[str, Dict[str, 'MethodMapping']]) -> str:
        """Generate a high-level coverage summary."""
        lines = ["📊 Method Coverage Summary"]
        
        for version in ["v1", "v2"]:
            if version not in unified:
                continue
            
            mappings = unified[version]
            total_methods = len(mappings)
            
            mdx_coverage = sum(1 for m in mappings.values() if m.has_mdx)
            yaml_coverage = sum(1 for m in mappings.values() if m.has_yaml)
            json_coverage = sum(1 for m in mappings.values() if m.has_examples)
            
            lines.extend([
                f"\n{version.upper()} API ({total_methods} methods):",
                self.format_coverage_stats(mdx_coverage, total_methods, "MDX Coverage"),
                self.format_coverage_stats(yaml_coverage, total_methods, "YAML Coverage"),
                self.format_coverage_stats(json_coverage, total_methods, "JSON Coverage")
            ])
            
        return "\n".join(lines)
    
    def generate_comparison_report(self, comparison: Dict[str, Dict[str, List[str]]], 
                                 method_mappings: Dict[str, Dict[str, 'MethodMapping']] = None) -> str:
        """
        Generate a report comparing methods found in different sources.

        Args:
            comparison: A dictionary with keys like 'mdx_only', 'postman_only', etc.
            method_mappings: Optional method mappings for providing additional context.
        """
        lines = [self.format_header("Comparison of Method Sources")]
        
        if not comparison:
            lines.append("No comparison data available.")
            return "\n".join(lines)
        
        source_map = {
            'mdx_only': "MDX documentation only",
            'postman_only': "Postman collections only",
            'yaml_only': "OpenAPI (YAML) specs only"
        }
        
        for source, versions in source_map.items():
            if source in comparison:
                lines.append(self.format_section_header(versions))
                
                for version, methods in comparison[source].items():
                    if methods:
                        lines.append(f"  {version.upper()} ({len(methods)} methods):")
                        
                        # Sort methods and limit to 20 for readability
                        sorted_methods = sorted(methods)
                        for i, method in enumerate(sorted_methods):
                            if i >= 20:
                                lines.append(f"    ... and {len(sorted_methods) - 20} more.")
                                break
                            
                            # Add MDX path if available
                            mdx_path = self._find_mdx_path_for_method(method, version, method_mappings)
                            path_info = f" (at {mdx_path})" if mdx_path else ""
                            lines.append(f"    - {method}{path_info}")
                    else:
                        lines.append(f"  {version.upper()}: ✅ All methods match.")
        
        return "\n".join(lines)
        
    def _find_mdx_path_for_method(self, method: str, version: str, 
                                 method_mappings: Dict[str, Dict[str, 'MethodMapping']]) -> Optional[str]:
        """Helper to find the MDX path for a given method."""
        if not method_mappings or version not in method_mappings:
            return None
        
        version_mappings = method_mappings[version]
        if method in version_mappings and version_mappings[method].has_mdx:
            return version_mappings[method].mdx_path
            
        return None 