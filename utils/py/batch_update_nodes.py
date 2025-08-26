#!/usr/bin/env python3
"""
Batch script to update node values in all request JSON files

This script finds all JSON files in the requests directory and updates their
node values using the update_request_nodes.py script.

Usage:
    python batch_update_nodes.py [--dry-run] [--directory <path>]
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_request_files(directory: Path) -> list[Path]:
    """Find all JSON files in the requests directory"""
    json_files = []
    
    if not directory.exists():
        logger.error(f"Directory does not exist: {directory}")
        return json_files
    
    # Find all .json files recursively
    for json_file in directory.rglob("*.json"):
        json_files.append(json_file)
    
    logger.info(f"Found {len(json_files)} JSON files to process")
    return json_files

def update_file(json_file: Path, dry_run: bool = False) -> bool:
    """Update a single JSON file using the update_request_nodes.py script"""
    
    script_path = Path(__file__).parent / "update_request_nodes.py"
    
    if not script_path.exists():
        logger.error(f"Update script not found: {script_path}")
        return False
    
    try:
        if dry_run:
            # For dry run, we'll just try to load and validate the file
            import json
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"[DRY RUN] Would update: {json_file}")
            return True
        else:
            # Run the actual update script
            cmd = [sys.executable, str(script_path), str(json_file)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Check if any updates were actually made
                if "Successfully updated" in result.stdout:
                    logger.info(f"✅ Updated: {json_file}")
                    return True
                else:
                    logger.info(f"ℹ️ No updates needed: {json_file}")
                    return False
            else:
                logger.error(f"❌ Failed to update {json_file}: {result.stderr}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error processing {json_file}: {e}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Batch update node values in all request JSON files"
    )
    parser.add_argument(
        "--directory", 
        "-d",
        default="src/data/requests/kdf",
        help="Directory to search for JSON files (default: src/data/requests/kdf)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    parser.add_argument(
        "--verbose", 
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Convert to absolute path relative to the script's location
    if not os.path.isabs(args.directory):
        # If relative path, make it relative to the workspace root (2 levels up from this script)
        workspace_root = Path(__file__).parent.parent.parent
        directory = workspace_root / args.directory
    else:
        directory = Path(args.directory)
    
    logger.info(f"🔍 Searching for JSON files in: {directory}")
    
    # Find all request files
    json_files = find_request_files(directory)
    
    if not json_files:
        logger.info("No JSON files found to process")
        return
    
    # Process each file
    updated_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            if update_file(json_file, args.dry_run):
                updated_count += 1
        except Exception as e:
            logger.error(f"Unexpected error processing {json_file}: {e}")
            error_count += 1
    
    # Summary
    total_files = len(json_files)
    skipped_count = total_files - updated_count - error_count
    
    logger.info("=" * 50)
    logger.info("📊 BATCH UPDATE SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total files processed: {total_files}")
    logger.info(f"Files updated: {updated_count}")
    logger.info(f"Files skipped (no updates needed): {skipped_count}")
    logger.info(f"Errors: {error_count}")
    
    if args.dry_run:
        logger.info("🔍 This was a dry run - no files were actually modified")
    else:
        if updated_count > 0:
            logger.info("🎉 Batch update completed successfully!")
        else:
            logger.info("✅ All files were already up-to-date!")
    
    if error_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()