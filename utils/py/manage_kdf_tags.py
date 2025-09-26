#!/usr/bin/env python3
"""
CLI utility for managing KDF method tags using the TagManager.

This script provides a convenient interface to analyze and apply automatic tags
to KDF methods based on their characteristics.
"""

import argparse
import sys
import json
import logging
from pathlib import Path

# Add lib path
sys.path.append(str(Path(__file__).parent / "lib"))

from managers.tag_manager import TagManager


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    log_level = logging.INFO if verbose else logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )


def get_default_paths() -> tuple[Path, Path]:
    """Get default paths for KDF methods and requests."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Default to v2 file; tool can still accept overrides via --kdf-methods
    kdf_methods_path = project_root / "src" / "data" / "kdf_methods_v2.json"
    requests_base_path = project_root / "src" / "data" / "requests" / "kdf"
    
    return kdf_methods_path, requests_base_path


def cmd_stats(args) -> None:
    """Show tag statistics."""
    tag_manager = TagManager(args.kdf_methods, args.requests_base)
    stats = tag_manager.get_tag_statistics()
    print(json.dumps(stats, indent=2))


def cmd_preview(args) -> None:
    """Preview tag changes."""
    tag_manager = TagManager(args.kdf_methods, args.requests_base)
    
    if args.method:
        try:
            preview = tag_manager.preview_tag_changes(args.method)
            print(json.dumps(preview, indent=2))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        changes = tag_manager.apply_derived_tags(dry_run=True)
        
        print(f"Summary:")
        print(f"  Methods that would be modified: {changes['methods_modified']}")
        print(f"  Tags that would be added: {changes['tags_added']}")
        print(f"  Tags that would be removed: {changes['tags_removed']}")
        
        if args.detailed and changes['modifications']:
            print(f"\nDetailed changes:")
            for method_name, method_changes in changes['modifications'].items():
                print(f"\n{method_name}:")
                print(f"  Current tags: {method_changes['old_tags']}")
                print(f"  Would add: {method_changes['added_tags']}")
                print(f"  Would remove: {method_changes['removed_tags']}")
                print(f"  Final tags: {method_changes['new_tags']}")


def cmd_apply(args) -> None:
    """Apply tag changes."""
    tag_manager = TagManager(args.kdf_methods, args.requests_base)
    
    if not args.confirm:
        print("This will modify the KDF methods file. Use --confirm to proceed.")
        sys.exit(1)
    
    print("Applying tag changes...")
    changes = tag_manager.apply_derived_tags(dry_run=False)
    
    print(f"Completed!")
    print(f"  Modified methods: {changes['methods_modified']}")
    print(f"  Added tags: {changes['tags_added']}")
    print(f"  Removed tags: {changes['tags_removed']}")
    
    if changes['modifications']:
        print(f"\nBackup created at: {tag_manager.kdf_methods_path}.backup")


def cmd_analyze(args) -> None:
    """Analyze specific tagging rules."""
    tag_manager = TagManager(args.kdf_methods, args.requests_base)
    
    analysis = {
        "total_methods": len(tag_manager.kdf_methods),
        "rule_analysis": {}
    }
    
    # Analyze each rule
    rules = {
        "v2": "Methods with mmrpc 2.0 requests",
        "task-based": "Methods with names starting with 'task::'",
        "single_wallet_type": "Methods with exactly one wallet type",
        "single_environment": "Methods with exactly one environment",
        "trezor": "Methods referencing Trezor",
        "metamask": "Methods referencing MetaMask"
    }
    
    derived_tags = tag_manager.derive_tags_for_all_methods()
    
    for rule_name, rule_desc in rules.items():
        methods_with_rule = []
        for method_name, tags in derived_tags.items():
            if rule_name in tags:
                methods_with_rule.append(method_name)
            elif rule_name == "single_wallet_type":
                # Check for any wallet type tags
                method_data = tag_manager.kdf_methods[method_name]
                wallet_tag = tag_manager._get_single_wallet_type_tag(method_data)
                if wallet_tag:
                    methods_with_rule.append(method_name)
            elif rule_name == "single_environment":
                # Check for any environment tags
                method_data = tag_manager.kdf_methods[method_name]
                env_tag = tag_manager._get_single_environment_tag(method_data)
                if env_tag:
                    methods_with_rule.append(method_name)
        
        analysis["rule_analysis"][rule_name] = {
            "description": rule_desc,
            "count": len(methods_with_rule),
            "methods": methods_with_rule if args.detailed else methods_with_rule[:5]
        }
    
    print(json.dumps(analysis, indent=2))


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage KDF method tags automatically",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current tag statistics
  %(prog)s stats
  
  # Preview what changes would be made
  %(prog)s preview
  
  # Preview changes for a specific method
  %(prog)s preview --method "task::enable_eth::init"
  
  # Show detailed analysis of tagging rules
  %(prog)s analyze --detailed
  
  # Apply all derived tags (creates backup)
  %(prog)s apply --confirm
        """
    )
    
    # Get default paths
    default_kdf_methods, default_requests_base = get_default_paths()
    
    parser.add_argument(
        "--kdf-methods",
        default=default_kdf_methods,
        type=Path,
        help=f"Path to kdf methods directory or file (default: {default_kdf_methods})"
    )
    parser.add_argument(
        "--requests-base",
        default=default_requests_base,
        type=Path,
        help=f"Path to requests base directory (default: {default_requests_base})"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show tag statistics")
    
    # Preview command
    preview_parser = subparsers.add_parser("preview", help="Preview tag changes")
    preview_parser.add_argument(
        "--method",
        help="Preview changes for specific method only"
    )
    preview_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed changes for all methods"
    )
    
    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply tag changes")
    apply_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that you want to apply changes"
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze tagging rules")
    analyze_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show all methods for each rule"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    setup_logging(args.verbose)
    
    # Validate paths
    if not args.kdf_methods.exists():
        print(f"Error: KDF methods file not found: {args.kdf_methods}", file=sys.stderr)
        sys.exit(1)
    
    if not args.requests_base.exists():
        print(f"Error: Requests base directory not found: {args.requests_base}", file=sys.stderr)
        sys.exit(1)
    
    # Execute command
    commands = {
        "stats": cmd_stats,
        "preview": cmd_preview,
        "apply": cmd_apply,
        "analyze": cmd_analyze
    }
    
    try:
        commands[args.command](args)
    except Exception as e:
        logging.error(f"Command failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
