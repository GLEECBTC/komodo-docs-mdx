#!/usr/bin/env python3
"""
KDF Method Documentation Generator

This module handles the generation of documentation for KDF API methods
that are identified as missing from the documentation. It integrates with
repository scanning and analysis tools to create compliant MDX files.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# Since the definitions for these are not provided, we'll create them
# based on their usage in the mdx_generator and doc_generator.
@dataclass
class Parameter:
    name: str
    param_type: str
    required: bool
    description: str
    default_value: Optional[str] = None
    is_array: bool = False

@dataclass
class MethodDetails:
    name: str
    human_title: str
    description: str
    api_tag: str
    request_params: List[Parameter]
    response_params: List[Parameter]
    error_types: List[str]
    source_files: List[str]
    examples: List[Dict] = field(default_factory=list)


class KDFMethodDocGenerator:
    """
    Documentation generator for missing KDF methods.
    
    This class integrates with the repository scanner to generate compliant
    documentation for methods that are missing from the documentation.
    """
    
    TITLE_PATTERNS = {
        "task": lambda p: f"{p[2].replace('_', ' ').title()} {p[1].replace('_', ' ').title()} Task" if len(p) == 3 else f"{p[1].replace('_', ' ').title()} Task",
        "stream": lambda p: f"{p[2].replace('_', ' ').title()} {p[1].replace('_', ' ').title()} Stream" if len(p) == 3 else f"{p[1].replace('_', ' ').title()} Stream",
        "lightning": lambda p: f"{p[2].replace('_', ' ').title()} Lightning {p[1].replace('_', ' ').title()[:-1]}" if len(p) == 3 else "Lightning Operation",
        "experimental": lambda p: f"{p[-1].replace('_', ' ').title()} {p[-2].replace('_', ' ').title()}" if len(p) >= 3 else "Experimental Operation",
        "gui_storage": lambda p: f"{p[1].replace('_', ' ').title()} GUI Storage",
    }
    
    def __init__(self, github_scanner, method_analyzer, doc_generator, unified_mapping_path: Optional[Path] = None):
        self.github_scanner = github_scanner
        self.method_analyzer = method_analyzer
        self.doc_generator = doc_generator
        
        # Get the absolute path to the data directory
        current_dir = Path(__file__).parent.parent.parent  # Go up to utils/py/
        self.unified_mapping_path = unified_mapping_path or current_dir / "data/unified_method_mapping.json"
        
    def load_missing_methods(self) -> Dict[str, List[str]]:
        """Load the list of missing methods from unified mapping."""
        try:
            with self.unified_mapping_path.open('r') as f:
                data = json.load(f)
            return data.get('missing', {}).get('methods_lacking_coverage', {})
        except FileNotFoundError:
            print(f"Error: {self.unified_mapping_path} not found")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return {}
    
    def validate_method(self, method_name: str) -> Tuple[bool, str]:
        """Validate if the method is in the missing methods list."""
        missing_methods = self.load_missing_methods()
        
        # Check both v1 and v2
        for version, methods in missing_methods.items():
            if method_name in methods:
                return True, version
        
        return False, ""
    
    def generate_human_readable_title(self, method_name: str) -> str:
        """Convert API method name to human-readable title."""
        if "::" in method_name:
            parts = method_name.split("::")
            prefix = parts[0]
            if prefix in self.TITLE_PATTERNS:
                return self.TITLE_PATTERNS[prefix](parts)
            
            # Generic namespaced methods
            action = parts[-1].replace("_", " ").title()
            namespace = "::".join(parts[:-1]).replace("_", " ").title()
            return f"{action} {namespace}"
        
        # Handle simple methods
        return method_name.replace("_", " ").title()
    
    def generate_method_description(self, method_name: str) -> str:
        """Generate a method description based on analysis."""
        if "::" in method_name:
            parts = method_name.split("::")
            prefix, *rest = parts
            if prefix == "task":
                action = rest[1] if len(rest) > 1 else "operation"
                subject = rest[0].replace('_', ' ')
                action_map = {
                    "cancel": f"Cancels the {subject} task operation",
                    "init": f"Initializes the {subject} task operation",
                    "status": f"Retrieves the status of the {subject} task operation",
                    "user_action": f"Handles user action for the {subject} task operation",
                }
                return action_map.get(action, f"Manages the {subject} task") + " in the Komodo DeFi Framework."
            elif prefix == "stream":
                return f"Manages the {rest[0].replace('_', ' ')} streaming functionality in the Komodo DeFi Framework."
            elif prefix == "lightning":
                return f"Handles Lightning Network {rest[0].replace('_', ' ')} operations in the Komodo DeFi Framework."
        
        return f"The `{method_name}` method provides functionality for {method_name.replace('_', ' ')} operations in the Komodo DeFi Framework."
    
    def determine_api_version_tag(self, version: str) -> str:
        """Determine the appropriate API version tag."""
        return "API-v1" if version == "v1" else "API-v2"
    
    def generate_documentation(self, method_name: str) -> Optional[str]:
        """Generate complete documentation for a method."""
        is_valid, version = self.validate_method(method_name)
        if not is_valid:
            print(f"Error: Method '{method_name}' is not in the missing methods list")
            return None
        
        print(f"Generating documentation for {method_name} ({version})...")
        
        print("Scanning repository for method details...")
        method_info = self.github_scanner.scan_method(method_name)
        
        if handler := method_info.get('rpc_handler'):
            print(f"Found RPC handler in {handler.get('version', 'unknown')} dispatcher")
            print(f"Handler file: {handler.get('file_path', 'unknown')}")
        
        print("Analyzing method parameters...")
        analysis = self.method_analyzer.analyze_method(method_name, method_info)
        
        # Here we construct the MethodDetails object to pass to the mdx_generator
        # We need to convert dicts from analysis into Parameter objects.
        request_params = [Parameter(**p) for p in analysis.get('request_params', [])]
        response_params = [Parameter(**p) for p in analysis.get('response_params', [])]
        
        examples = analysis.get('examples', [])
        if not examples:
            examples = [{"method": method_name, "userpass": "RPC_UserP@SSW0RD"}]

        method_details = MethodDetails(
            name=method_name,
            human_title=self.generate_human_readable_title(method_name),
            description=self.generate_method_description(method_name),
            api_tag=self.determine_api_version_tag(version),
            request_params=request_params,
            response_params=response_params,
            error_types=analysis.get('error_types', []),
            examples=examples,
            source_files=method_info.get('source_files', []),
        )

        print("Generating documentation content...")
        return self.doc_generator.generate(method_details)
    
    def save_documentation(self, method_name: str, content: str, version: str) -> str:
        """Save generated documentation to appropriate location."""
        current_dir = Path(__file__).parent.parent.parent
        base_path = current_dir / "data" / "generated_docs" / version
        
        method_path = "/".join(method_name.split("::"))
        method_dir = base_path / method_path
        
        method_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = method_dir / "index.mdx"
        output_file.write_text(content, encoding="utf-8")
        
        return str(output_file)
    
    def run(self, method_name: str, save: bool = True, output_file: Optional[str] = None) -> None:
        """Main execution method."""
        try:
            content = self.generate_documentation(method_name)
            if not content:
                return
            
            if save:
                if output_file:
                    output_path = Path(output_file)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(content, encoding="utf-8")
                    print(f"Documentation saved to: {output_file}")
                else:
                    _is_valid, version = self.validate_method(method_name)
                    saved_path = self.save_documentation(method_name, content, version)
                    print(f"Documentation saved to: {saved_path}")
            else:
                print("\n" + "="*80)
                print("GENERATED DOCUMENTATION")
                print("="*80)
                print(content)
        
        except Exception as e:
            print(f"Error generating documentation: {e}")
            raise


def main():
    """Main CLI entry point for documentation generation."""
    parser = argparse.ArgumentParser(
        description="Generate KDF method documentation from repository analysis"
    )
    parser.add_argument(
        "method_name",
        nargs='?',
        help="Name of the method to generate documentation for"
    )
    parser.add_argument(
        "--list-missing",
        action="store_true",
        help="List all missing methods"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save the file, just print to stdout"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (if not using standard location)"
    )
    
    args = parser.parse_args()
    
    # Need to instantiate dependencies for the generator
    try:
        from ..analysis.github_scanner import GitHubScanner
        from ..analysis.rust_analyzer import MethodAnalyzer
        from .mdx_generator import MdxGenerator
    except ImportError as e:
        print(f"Failed to import a required module: {e}")
        return

    github_scanner = GitHubScanner()
    method_analyzer = MethodAnalyzer()
    mdx_generator = MdxGenerator()
    
    generator = KDFMethodDocGenerator(
        github_scanner=github_scanner, 
        method_analyzer=method_analyzer,
        doc_generator=mdx_generator
    )
    
    if args.list_missing:
        missing_methods = generator.load_missing_methods()
        if not missing_methods:
            print("No missing methods found.")
            return
        print("Missing Methods:")
        print("="*50)
        for version, methods in missing_methods.items():
            print(f"\n{version.upper()} ({len(methods)} methods):")
            for method in sorted(methods):
                print(f"  - {method}")
        return

    if not args.method_name:
        parser.error("the following arguments are required: method_name")
    
    generator.run(
        method_name=args.method_name,
        save=not args.no_save,
        output_file=args.output
    )


if __name__ == "__main__":
    main() 