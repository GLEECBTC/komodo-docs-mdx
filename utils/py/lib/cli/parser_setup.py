#!/usr/bin/env python3
"""
Parser Setup for KDF Tools CLI

This module contains the argument parser setup logic separated from the main CLI class
to improve maintainability and reduce the monolithic structure.
"""

import argparse
from pathlib import Path
from typing import Any


class ParserSetup:
    """Handles argument parser setup for KDF Tools CLI."""
    
    def __init__(self, config):
        self.config = config
        
    def setup_openapi_parser(self, subparsers):
        """Setup parser for the openapi command."""
        parser = subparsers.add_parser(
            'openapi',
            help='Generate OpenAPI specs from MDX documentation.',
            description='Processes MDX documentation files to create OpenAPI specifications'
        )
        parser.set_defaults(func='openapi_command')

    def setup_postman_parser(self, subparsers):
        """Setup parser for the postman command."""
        parser = subparsers.add_parser(
            'postman',
            help='Generate Postman collections from OpenAPI specs.',
            description='Converts OpenAPI specifications into Postman collections for easier API testing and integration.'
        )
        parser.set_defaults(func='postman_command')

    def setup_scan_mdx_parser(self, subparsers):
        """Sets up argument parser for the mdx_scan command."""
        parser = subparsers.add_parser('scan-mdx', help='Scan MDX files for method info.')
        parser.set_defaults(func='scan_mdx_command')

    def setup_scan_rust_parser(self, subparsers):
        """Setup parser for the scan-rust command."""
        parser = subparsers.add_parser(
            'scan-rust', 
            help='Scan KDF Rust repository for RPC methods.',
            description='Scans the Komodo DeFi Framework Rust repository to find RPC methods.'
        )
        parser.set_defaults(func='scan_rust_command')

    def setup_map_methods_parser(self, subparsers):
        """Setup parser for the map-methods command."""
        parser = subparsers.add_parser(
            'map_methods',
            help='Generate a unified mapping of all method-related files.',
            description='Creates a comprehensive JSON file that maps each method to its corresponding MDX, OpenAPI, and Postman files.'
        )
        parser.add_argument(
            '--remove',
            type=str,
            help='Remove all files associated with a specific method.'
        )
        parser.add_argument(
            '--debug',
            type=str,
            help='Debug method matching for a specific method.'
        )
        parser.set_defaults(func='methods_map_command')

    def setup_json_extract_parser(self, subparsers):
        """Setup parser for the json-extract command."""
        parser = subparsers.add_parser(
            'json-extract',
            help='Extract JSON examples from MDX files.',
            description='Extracts JSON request/response examples from MDX documentation.'
        )
        parser.set_defaults(func='json_extract_command')

    def setup_review_draft_quality_parser(self, subparsers):
        """Setup parser for the review-draft-quality command."""
        parser = subparsers.add_parser(
            'review-draft-quality',
            help='Compare generated documentation with live versions.',
            description='Compares generated documentation with live versions to assess quality.'
        )
        parser.add_argument(
            '--generated', type=Path, required=True,
            help='Path to the generated documentation file.'
        )
        parser.add_argument(
            '--live', type=Path, required=True,
            help='Path to the live documentation file.'
        )
        parser.add_argument(
            '--generated-dir', type=Path,
            help='Directory containing generated documentation files.'
        )
        parser.add_argument(
            '--live-dir', type=Path,
            help='Directory containing live documentation files.'
        )
        parser.add_argument(
            '--output', type=Path,
            help='Path to save the review report.'
        )
        parser.add_argument(
            '--format', choices=['json', 'markdown'], default='markdown',
            help='Format of the review report.'
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.set_defaults(func='review_draft_quality_command')

    def setup_scan_existing_docs_parser(self, subparsers):
        """Setup parser for the scan-existing-docs command."""
        parser = subparsers.add_parser(
            'scan-existing-docs',
            help='Scan existing KDF documentation to extract method patterns.',
            description='Scans existing KDF documentation to extract method patterns.'
        )
        parser.add_argument(
            '--docs-path', type=Path,
            help='Path to the directory containing existing documentation files.'
        )
        parser.add_argument(
            '--async-scan', action='store_true',
            help='Use asynchronous scanning for better performance.'
        )
        parser.add_argument(
            '--output', type=Path,
            help='Path to save the extracted method patterns.'
        )
        parser.add_argument(
            '--generate-report', action='store_true',
            help='Generate an analysis report of the extracted method patterns.'
        )
        parser.add_argument(
            '--show-categories', action='store_true',
            help='Show method categories in the analysis report.'
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.set_defaults(func='scan_existing_docs_command')

    def setup_generate_docs_parser(self, subparsers):
        """Sets up the argument parser for the `generate-docs` command."""
        parser = subparsers.add_parser(
            "generate-docs",
            help="Generate MDX documentation from templates for specified methods.",
            description="This command automates the creation of MDX documentation files from pre-defined templates. It can use a list of methods from a file or allow interactive selection.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            "-m", "--methods",
            nargs='+',
            help="A list of one or more method names to generate documentation for."
        )
        parser.add_argument(
            "-f", "--methods-file",
            type=str,
            help="Path to a file containing a list of method names (one per line)."
        )
        parser.add_argument(
            "-i", "--interactive",
            action="store_true",
            help="Use interactive mode to select methods from a list."
        )
        parser.add_argument(
            "-t", "--template",
            type=str,
            default="default",
            help="The template to use for generation (e.g., 'default', 'comprehensive')."
        )
        parser.add_argument(
            "-o", "--output-dir",
            type=str,
            default=str(Path(self.config.directories.data_dir) / "generated_docs") if self.config.directories.data_dir else "generated_docs",
            help="The directory to save the generated MDX files."
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.set_defaults(func='generate_docs_command')

    def setup_gap_analysis_parser(self, subparsers):
        """Sets up the argument parser for the `gap-analysis` command."""
        parser = subparsers.add_parser(
            "gap-analysis",
            help="Perform gap analysis between Rust and MDX methods.",
            description="Compares methods found in the Rust repository against those documented in MDX files."
        )
        parser.set_defaults(func='gap_analysis_command')

    def setup_get_kdf_responses_parser(self, subparsers):
        """Sets up argument parser for the get_kdf_responses command."""
        parser = subparsers.add_parser(
            'get-kdf-responses',
            help='Get KDF responses for a given method.',
            description='Gets API responses for a given method and saves them to JSON files.'
        )
        parser.add_argument('--method', type=str, help='The method to get responses for.')
        parser.add_argument('--clean', action='store_true', help='Clean JSON files before running.')
        parser.add_argument('--substitute-defaults', action='store_true', help='Use test parameter substitution for coin/ticker fields.')
        parser.set_defaults(func='get_kdf_responses_command')
        
    def setup_v2_no_param_report_parser(self, subparsers):
        """Sets up argument parser for the generate_v2_no_param_methods_report command."""
        parser = subparsers.add_parser(
            "v2-no-param-methods-report",
            help="Generate a report of V2 methods that don't have parameters.",
            description="Generates a report of V2 methods that don't have parameters."
        )
        parser.set_defaults(func='generate_v2_no_param_methods_report')

    def setup_build_container_parser(self, subparsers):
        """Sets up argument parser for the build-container command."""
        parser = subparsers.add_parser('build-container', help='Build KDF container image.')
        parser.add_argument('--kdf-branch', type=str, default='dev', help='KDF branch to build.')
        parser.add_argument('--commit', type=str, help='Commit hash to build.')
        parser.set_defaults(func='build_container_command')

    def setup_start_container_parser(self, subparsers):
        """Sets up argument parser for the start-container command."""
        parser = subparsers.add_parser('start-container', help='Start KDF container.')
        parser.add_argument('--kdf-branch', type=str, default='dev', help='KDF branch to use.')
        parser.add_argument('--commit', type=str, help='Commit hash to use.')
        parser.set_defaults(func='start_container_command')
    
    def setup_stop_container_parser(self, subparsers):
        """Sets up argument parser for the stop-container command."""
        parser = subparsers.add_parser('stop-container', help='Stop KDF container.')
        parser.set_defaults(func='stop_container_command')

    def setup_switch_kdf_branch_parser(self, subparsers):
        """Sets up argument parser for the switch-kdf-branch command."""
        parser = subparsers.add_parser('switch-kdf-branch', help='Switch KDF branch.')
        parser.add_argument('branch', type=str, help='Branch to switch to.')
        parser.set_defaults(func='switch_kdf_branch_command')

    def setup_get_json_example_method_paths_parser(self, subparsers):
        """Sets up argument parser for the get-json-example-method-paths command."""
        parser = subparsers.add_parser('get-json-example-method-paths', help='Get JSON example method paths.')
        parser.set_defaults(func='get_json_example_method_paths_command')

    def setup_report_error_responses_parser(self, subparsers):
        """Sets up argument parser for the report-error-responses command."""
        parser = subparsers.add_parser('report-error-responses', help='Generate a report of method requests that have error responses.')
        parser.set_defaults(func='report_error_responses_command')

    def setup_extract_errors_parser(self, subparsers):
        """Setup parser for the extract-errors command."""
        parser = subparsers.add_parser('extract-errors', help='Extract error enums from KDF source')
        parser.add_argument(
            '--source', type=str, required=True,
            help="The source to scan (e.g., 'rust' or 'mdx')."
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.set_defaults(func='extract_errors_command')

    def setup_balances_parser(self, subparsers):
        """Sets up argument parser for the balances command."""
        parser = subparsers.add_parser(
            "balances",
            help="Get address and balance info for test coins.",
            description="Checks balances for PRIMARY_COIN, SECONDARY_COIN and NODE_BALANCE_COINS on all nodes."
        )
        parser.add_argument('--clean', action='store_true', help='Clean JSON files before running.')
        parser.set_defaults(func='balances_command')

    def setup_sync_parser(self, subparsers):
        """Setup parser for the sync command."""
        parser = subparsers.add_parser(
            'sync',
            help='Bidirectional sync between MDX docs and Postman collections.',
            description='Sync requests and responses between MDX documentation and Postman collections.'
        )
        parser.add_argument(
            'direction',
            choices=['docs-to-postman', 'postman-to-docs', 'bidirectional'],
            help='Sync direction'
        )
        parser.add_argument(
            '--method-filter',
            type=str,
            help='Filter to specific method name'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.set_defaults(func='sync_command')

    def setup_workflow_parsers(self, subparsers):
        """Setup parsers for workflow commands."""
        
        # WalletConnect workflow
        wc_parser = subparsers.add_parser(
            'walletconnect-workflow',
            help='Launch interactive WalletConnect session management TUI.',
            description='Opens an interactive interface for managing WalletConnect sessions.'
        )
        wc_parser.add_argument(
            '--kdf-branch',
            type=str,
            default='dev',
            help='Specify the KDF branch to use'
        )
        wc_parser.set_defaults(func='walletconnect_workflow_command')
        
        # Trezor workflow
        trezor_parser = subparsers.add_parser(
            'trezor-workflow',
            help='Launch interactive Trezor device management TUI.',
            description='Opens an interactive interface for managing Trezor devices.'
        )
        trezor_parser.add_argument(
            '--kdf-branch',
            type=str,
            default='dev',
            help='Specify the KDF branch to use'
        )
        trezor_parser.set_defaults(func='trezor_workflow_command')

    def setup_all_parsers(self, subparsers):
        """Setup all argument parsers."""
        self.setup_openapi_parser(subparsers)
        self.setup_postman_parser(subparsers)
        self.setup_scan_rust_parser(subparsers)
        self.setup_scan_mdx_parser(subparsers)
        self.setup_map_methods_parser(subparsers)
        self.setup_json_extract_parser(subparsers)
        self.setup_review_draft_quality_parser(subparsers)
        self.setup_scan_existing_docs_parser(subparsers)
        self.setup_generate_docs_parser(subparsers)
        self.setup_gap_analysis_parser(subparsers)
        self.setup_get_kdf_responses_parser(subparsers)
        self.setup_v2_no_param_report_parser(subparsers)
        self.setup_build_container_parser(subparsers)
        self.setup_start_container_parser(subparsers)
        self.setup_stop_container_parser(subparsers)
        self.setup_switch_kdf_branch_parser(subparsers)
        self.setup_get_json_example_method_paths_parser(subparsers)
        self.setup_report_error_responses_parser(subparsers)
        self.setup_extract_errors_parser(subparsers)
        self.setup_balances_parser(subparsers)
        self.setup_sync_parser(subparsers)
        self.setup_workflow_parsers(subparsers) 