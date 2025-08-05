#!/usr/bin/env python3
"""
Sync CLI - Bidirectional sync between MDX docs and Postman collections.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

from .sync_manager import BidirectionalSyncManager
from .config import SyncConfig
from ..utils.logging_utils import get_logger
from ..constants.config import get_config


class SyncCLI:
    """CLI for bidirectional sync operations."""
    
    def __init__(self, main_config=None):
        self.main_config = main_config or get_config()
        self.logger = get_logger("sync-cli")
    
    def create_sync_config(self, **kwargs) -> SyncConfig:
        """Create SyncConfig from main config."""
        return SyncConfig.from_main_config(self.main_config, **kwargs)
    
    async def sync_docs_to_postman(self, method_filter: Optional[str] = None, dry_run: bool = False) -> int:
        """Sync from MDX docs to Postman collection."""
        try:
            sync_config = self.create_sync_config(dry_run=dry_run)
            manager = BidirectionalSyncManager(sync_config)
            
            self.logger.info("Starting Docs → Postman sync...")
            result = await manager.sync_docs_to_postman(method_filter)
            
            if result.success:
                self.logger.info(f"✅ Sync completed: {result.message}")
                if result.data:
                    self.logger.info(f"📊 Extracted: {result.data.get('extracted_requests', 0)} requests")
                    self.logger.info(f"📊 Updated: {result.data.get('requests_with_responses', 0)} requests")
                return 0
            else:
                self.logger.error(f"❌ Sync failed: {result.message}")
                if result.errors:
                    for error in result.errors:
                        self.logger.error(f"  - {error}")
                return 1
                
        except Exception as e:
            self.logger.error(f"❌ Sync failed with exception: {e}")
            return 1
    
    async def sync_postman_to_docs(self, method_filter: Optional[str] = None, dry_run: bool = False) -> int:
        """Sync from Postman collection to MDX docs."""
        try:
            sync_config = self.create_sync_config(dry_run=dry_run)
            manager = BidirectionalSyncManager(sync_config)
            
            self.logger.info("Starting Postman → Docs sync...")
            result = await manager.sync_postman_to_docs(method_filter)
            
            if result.success:
                self.logger.info(f"✅ Sync completed: {result.message}")
                if result.data:
                    self.logger.info(f"📊 Extracted: {result.data.get('extracted_requests', 0)} requests")
                    self.logger.info(f"📊 Updated: {result.data.get('requests_with_responses', 0)} requests")
                return 0
            else:
                self.logger.error(f"❌ Sync failed: {result.message}")
                if result.errors:
                    for error in result.errors:
                        self.logger.error(f"  - {error}")
                return 1
                
        except Exception as e:
            self.logger.error(f"❌ Sync failed with exception: {e}")
            return 1
    
    async def bidirectional_sync(self, method_filter: Optional[str] = None, dry_run: bool = False) -> int:
        """Perform bidirectional sync."""
        try:
            sync_config = self.create_sync_config(dry_run=dry_run)
            manager = BidirectionalSyncManager(sync_config)
            
            self.logger.info("Starting bidirectional sync...")
            
            # Sync docs to postman
            docs_to_postman = await manager.sync_docs_to_postman(method_filter)
            if not docs_to_postman.success:
                self.logger.error("Docs → Postman sync failed")
                return 1
            
            # Sync postman to docs
            postman_to_docs = await manager.sync_postman_to_docs(method_filter)
            if not postman_to_docs.success:
                self.logger.error("Postman → Docs sync failed")
                return 1
            
            self.logger.info("✅ Bidirectional sync completed successfully")
            return 0
            
        except Exception as e:
            self.logger.error(f"❌ Bidirectional sync failed with exception: {e}")
            return 1


def main():
    """Main entry point for sync CLI."""
    parser = argparse.ArgumentParser(
        description="Bidirectional sync between MDX docs and Postman collections",
        formatter_class=argparse.RawTextHelpFormatter
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
    
    parser.add_argument(
        '--kdf-branch',
        type=str,
        default='dev',
        help='KDF branch to use'
    )
    
    args = parser.parse_args()
    
    try:
        cli = SyncCLI()
        
        if args.direction == 'docs-to-postman':
            return asyncio.run(cli.sync_docs_to_postman(args.method_filter, args.dry_run))
        elif args.direction == 'postman-to-docs':
            return asyncio.run(cli.sync_postman_to_docs(args.method_filter, args.dry_run))
        elif args.direction == 'bidirectional':
            return asyncio.run(cli.bidirectional_sync(args.method_filter, args.dry_run))
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 