#!/usr/bin/env python3
"""
Bidirectional Sync Manager - Consolidates all sync functionality.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from .config import SyncConfig
from .extractors import MDXExtractor, PostmanExtractor
from .updaters import MDXUpdater, PostmanUpdater
from .base import SyncResult, RequestData

# Import existing infrastructure
from ..api_client.kdf_api_processor import ApiRequestProcessor
from ..postman.postman_manager import PostmanManager
from ..utils.logging_utils import get_logger
from ..constants.config import get_config


class BidirectionalSyncManager:
    """
    Main sync manager that consolidates all sync functionality, always using DirectoryConfig for paths.
    """
    
    def __init__(self, config: SyncConfig):
        self.config = config
        self.directories = config.directories
        self.logger: Any = get_logger("bidirectional-sync")  # Accept any logger type
        
        # Initialize existing infrastructure
        self.kdf_config = get_config()
        self.api_processor = ApiRequestProcessor(
            config=self.kdf_config,
            logger=self.logger
        )
        
        # Initialize extractors and updaters
        self.mdx_extractor = MDXExtractor(logger=self.logger)
        self.postman_extractor = PostmanExtractor(logger=self.logger)
        self.mdx_updater = MDXUpdater(logger=self.logger)
        self.postman_updater = PostmanUpdater(logger=self.logger)
        
        # Initialize postman manager
        self.postman_manager = PostmanManager(
            config=self.kdf_config,
            verbose=True
        )
        
        self.logger.info(f"Initialized BidirectionalSyncManager with directories: {self.directories}")
    
    async def sync_docs_to_postman(self, method_filter: Optional[str] = None) -> SyncResult:
        """
        Sync requests and responses from MDX docs to Postman collection.
        
        Args:
            method_filter: Optional method name to filter sync to specific method
            
        Returns:
            SyncResult with success status and details
        """
        try:
            self.logger.info("Starting Docs → Postman sync...")
            
            # Extract requests from MDX docs
            mdx_requests = self.mdx_extractor.extract_requests(
                source_path=self.directories.mdx_v2
            )
            
            # Apply method filter if specified
            if method_filter:
                mdx_requests = [req for req in mdx_requests if method_filter in req.method]
                self.logger.info(f"Filtered to {len(mdx_requests)} requests for method: {method_filter}")
            
            if not mdx_requests:
                return SyncResult(
                    success=False,
                    message="No requests extracted from MDX docs",
                    errors=["No MDX requests found"]
                )
            
            self.logger.info(f"Extracted {len(mdx_requests)} requests from MDX docs")
            
            # Update Postman collection
            postman_collection_path = Path(self.directories.postman_collections) / "KDF_API_V2_Collection.postman_collection.json"
            
            success = self.postman_updater.update_target(
                target_path=postman_collection_path,
                data=mdx_requests
            )
            
            if success:
                return SyncResult(
                    success=True,
                    message=f"Docs → Postman sync completed. Updated {len(mdx_requests)} requests",
                    data={
                        "extracted_requests": len(mdx_requests),
                        "updated_requests": len(mdx_requests),
                        "errors": 0
                    }
                )
            else:
                return SyncResult(
                    success=False,
                    message="Failed to update Postman collection",
                    errors=["Postman collection update failed"]
                )
            
        except Exception as e:
            error_msg = f"Docs → Postman sync failed: {e}"
            self.logger.error(error_msg)
            return SyncResult(
                success=False,
                message=error_msg,
                errors=[error_msg]
            )
    
    async def sync_postman_to_docs(self, method_filter: Optional[str] = None) -> SyncResult:
        """
        Sync requests and responses from Postman collection to MDX docs.
        
        Args:
            method_filter: Optional method name to filter sync to specific method
            
        Returns:
            SyncResult with success status and details
        """
        try:
            self.logger.info("Starting Postman → Docs sync...")
            
            # Extract requests from Postman collection
            postman_collection_path = Path(self.directories.postman_collections) / "KDF_API_V2_Collection.postman_collection.json"
            
            postman_requests = self.postman_extractor.extract_requests(
                source_path=postman_collection_path
            )
            
            # Apply method filter if specified
            if method_filter:
                postman_requests = [req for req in postman_requests if method_filter in req.method]
                self.logger.info(f"Filtered to {len(postman_requests)} requests for method: {method_filter}")
            
            if not postman_requests:
                return SyncResult(
                    success=False,
                    message="No requests extracted from Postman collection",
                    errors=["No Postman requests found"]
                )
            
            self.logger.info(f"Extracted {len(postman_requests)} requests from Postman collection")
            
            # Update MDX docs
            success = self.mdx_updater.update_target(
                target_path=self.directories.mdx_v2,
                data=postman_requests
            )
            
            if success:
                return SyncResult(
                    success=True,
                    message=f"Postman → Docs sync completed. Updated {len(postman_requests)} requests",
                    data={
                        "extracted_requests": len(postman_requests),
                        "updated_requests": len(postman_requests),
                        "errors": 0
                    }
                )
            else:
                return SyncResult(
                    success=False,
                    message="Failed to update MDX docs",
                    errors=["MDX docs update failed"]
                )
            
        except Exception as e:
            error_msg = f"Postman → Docs sync failed: {e}"
            self.logger.error(error_msg)
            return SyncResult(
                success=False,
                message=error_msg,
                errors=[error_msg]
            )
    
    async def bidirectional_sync(self, method_filter: Optional[str] = None) -> SyncResult:
        """
        Perform bidirectional sync between MDX docs and Postman collection.
        
        Args:
            method_filter: Optional method name to filter sync to specific method
            
        Returns:
            SyncResult with success status and details
        """
        try:
            self.logger.info("Starting bidirectional sync...")
            
            # Sync docs to postman
            docs_to_postman = await self.sync_docs_to_postman(method_filter)
            if not docs_to_postman.success:
                return docs_to_postman
            
            # Sync postman to docs
            postman_to_docs = await self.sync_postman_to_docs(method_filter)
            if not postman_to_docs.success:
                return postman_to_docs
            
            # Combine results
            docs_data = docs_to_postman.data or {}
            postman_data = postman_to_docs.data or {}
            
            total_extracted = (
                docs_data.get('extracted_requests', 0) +
                postman_data.get('extracted_requests', 0)
            )
            total_updated = (
                docs_data.get('updated_requests', 0) +
                postman_data.get('updated_requests', 0)
            )
            
            return SyncResult(
                success=True,
                message=f"Bidirectional sync completed successfully. Total extracted: {total_extracted}, Total updated: {total_updated}",
                data={
                    "total_extracted": total_extracted,
                    "total_updated": total_updated,
                    "docs_to_postman": docs_data,
                    "postman_to_docs": postman_data
                }
            )
            
        except Exception as e:
            error_msg = f"Bidirectional sync failed: {e}"
            self.logger.error(error_msg)
            return SyncResult(
                success=False,
                message=error_msg,
                errors=[error_msg]
            )
    
    def validate_sync_environment(self) -> SyncResult:
        """
        Validate that the sync environment is properly configured.
        
        Returns:
            SyncResult with validation status
        """
        errors = []
        
        # Check paths exist
        if not Path(self.directories.mdx_v2).exists():
            errors.append(f"MDX v2 docs path does not exist: {self.directories.mdx_v2}")
        
        if not Path(self.directories.postman_collections).exists():
            errors.append(f"Postman collections path does not exist: {self.directories.postman_collections}")
        
        # Check API connectivity
        try:
            # Basic connectivity check could be added here
            pass
        except Exception as e:
            errors.append(f"API connectivity check failed: {e}")
        
        if errors:
            return SyncResult(
                success=False,
                message="Sync environment validation failed",
                errors=errors
            )
        
        return SyncResult(
            success=True,
            message="Sync environment validation passed"
        ) 