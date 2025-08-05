#!/usr/bin/env python3
"""
Updaters for different target types (MDX docs, Postman collections).
Consolidates update logic using existing lib infrastructure.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import re
from datetime import datetime

from .base import BaseUpdater, RequestData
from ..postman.postman_manager import PostmanManager
from ..utils.logging_utils import get_logger
from ..utils.file_utils import safe_write_json, ensure_directory_exists


class MDXUpdater(BaseUpdater):
    """Updater for MDX documentation files using existing infrastructure."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.code_group_pattern = re.compile(
            r'(<CodeGroup.*?mm2MethodDecorate="true".*?>)(.*?)(</CodeGroup>)',
            re.DOTALL
        )
        self.json_block_pattern = re.compile(
            r'(```json\s*\n)(.*?)(\n```)',
            re.DOTALL
        )
    
    def update_target(self, target_path: Union[str, Path], data: List[RequestData]) -> bool:
        """
        Update MDX documentation with new request/response data.
        
        Args:
            target_path: Path to MDX docs directory
            data: List of RequestData objects
            
        Returns:
            True if successful, False otherwise
        """
        target_path = Path(target_path)
        
        if not target_path.exists():
            self.logger.error(f"Target path does not exist: {target_path}")
            return False
        
        # Group data by source file
        data_by_file = {}
        for item in data:
            source_file = item.source_file
            if source_file:
                if source_file not in data_by_file:
                    data_by_file[source_file] = []
                data_by_file[source_file].append(item)
        
        success_count = 0
        total_files = len(data_by_file)
        
        for file_path, file_data in data_by_file.items():
            try:
                if self._update_single_file(Path(file_path), file_data):
                    success_count += 1
                    self.logger.info(f"Updated {file_path}")
                else:
                    self.logger.error(f"Failed to update {file_path}")
            except Exception as e:
                self.logger.error(f"Error updating {file_path}: {e}")
        
        self.logger.info(f"Updated {success_count}/{total_files} files")
        return success_count > 0
    
    def _update_single_file(self, file_path: Path, file_data: List[RequestData]) -> bool:
        """
        Update a single MDX file with new data.
        
        Args:
            file_path: Path to MDX file
            file_data: List of RequestData objects for this file
            
        Returns:
            True if successful, False otherwise
        """
        if not file_path.exists():
            self.logger.error(f"File does not exist: {file_path}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return False
        
        # Create backup
        backup_path = self.backup_target(file_path)
        if not backup_path:
            self.logger.warning(f"Failed to create backup for {file_path}")
        
        # Update content
        updated_content = self._update_content(content, file_data)
        
        if updated_content != content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                return True
            except Exception as e:
                self.logger.error(f"Failed to write updated content to {file_path}: {e}")
                return False
        
        return True
    
    def _update_content(self, content: str, file_data: List[RequestData]) -> str:
        """
        Update MDX content with new request/response data.
        
        Args:
            content: Original MDX content
            file_data: List of RequestData objects to apply
            
        Returns:
            Updated content
        """
        updated_content = content
        
        for data_item in file_data:
            method = data_item.method
            request = data_item.request
            response = data_item.response
            example_index = data_item.example_index
            
            if not method or not request:
                continue
            
            # Find and update CodeGroup components
            updated_content = self._update_code_groups(
                updated_content, method, request, response, example_index
            )
        
        return updated_content
    
    def _update_code_groups(self, content: str, method: str, request: Dict[str, Any], 
                           response: Optional[Dict[str, Any]], example_index: int) -> str:
        """
        Update CodeGroup components with new request/response data.
        
        Args:
            content: MDX content
            method: Method name
            request: Request data
            response: Response data (optional)
            example_index: Index of example to update
            
        Returns:
            Updated content
        """
        def replace_code_group(match):
            code_group_content = match.group(2)
            
            # Find JSON blocks in this CodeGroup
            json_blocks = self.json_block_pattern.findall(code_group_content)
            
            if example_index < len(json_blocks):
                # Update the specific example
                old_json = json_blocks[example_index][1]
                new_json = json.dumps(request, indent=4)
                
                # Replace the JSON block
                updated_code_group = code_group_content.replace(
                    json_blocks[example_index][0] + old_json + json_blocks[example_index][2],
                    json_blocks[example_index][0] + new_json + json_blocks[example_index][2]
                )
                
                return match.group(1) + updated_code_group + match.group(3)
            
            return match.group(0)
        
        return self.code_group_pattern.sub(replace_code_group, content)


class PostmanUpdater(BaseUpdater):
    """Updater for Postman collections using existing infrastructure."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.postman_manager = PostmanManager(verbose=True)
    
    def update_target(self, target_path: Union[str, Path], data: List[RequestData]) -> bool:
        """
        Update Postman collection with new request/response data.
        
        Args:
            target_path: Path to Postman collection file
            data: List of RequestData objects
            
        Returns:
            True if successful, False otherwise
        """
        target_path = Path(target_path)
        
        if not target_path.exists():
            self.logger.error(f"Postman collection not found: {target_path}")
            return False
        
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                collection_data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load Postman collection: {e}")
            return False
        
        # Create backup
        backup_path = self.backup_target(target_path)
        if not backup_path:
            self.logger.warning(f"Failed to create backup for {target_path}")
        
        # Update collection with new data
        updated_collection = self._update_collection(collection_data, data)
        
        try:
            safe_write_json(target_path, updated_collection)
            
            self.logger.info(f"Updated Postman collection: {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write updated Postman collection: {e}")
            return False
    
    def _update_collection(self, collection: Dict[str, Any], data: List[RequestData]) -> Dict[str, Any]:
        """
        Update Postman collection with new request/response data.
        
        Args:
            collection: Original collection data
            data: List of RequestData objects
            
        Returns:
            Updated collection data
        """
        updated_collection = collection.copy()
        
        # Group data by method
        data_by_method = {}
        for item in data:
            method = item.method
            if method:
                if method not in data_by_method:
                    data_by_method[method] = []
                data_by_method[method].append(item)
        
        # Update items in collection
        if 'item' in updated_collection:
            updated_collection['item'] = self._update_items(
                updated_collection['item'], data_by_method
            )
        
        return updated_collection
    
    def _update_items(self, items: List[Dict[str, Any]], 
                     data_by_method: Dict[str, List[RequestData]]) -> List[Dict[str, Any]]:
        """
        Update Postman collection items with new data.
        
        Args:
            items: List of collection items
            data_by_method: Data grouped by method name
            
        Returns:
            Updated items list
        """
        updated_items = []
        
        for item in items:
            updated_item = item.copy()
            
            # Handle folders
            if 'item' in updated_item:
                updated_item['item'] = self._update_items(
                    updated_item['item'], data_by_method
                )
            
            # Handle requests
            if 'request' in updated_item:
                method_name = self._extract_method_from_item(updated_item)
                if method_name and method_name in data_by_method:
                    updated_item = self._update_single_item(
                        updated_item, data_by_method[method_name]
                    )
            
            updated_items.append(updated_item)
        
        return updated_items
    
    def _extract_method_from_item(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Extract method name from Postman collection item.
        
        Args:
            item: Postman collection item
            
        Returns:
            Method name or None
        """
        try:
            url = item.get('request', {}).get('url', {})
            path_parts = url.get('path', [])
            
            for part in reversed(path_parts):
                if part and part != 'api':
                    return part
            
            return None
        except Exception:
            return None
    
    def _update_single_item(self, item: Dict[str, Any], 
                           method_data: List[RequestData]) -> Dict[str, Any]:
        """
        Update a single Postman collection item with new data.
        
        Args:
            item: Postman collection item
            method_data: List of RequestData objects for this method
            
        Returns:
            Updated item
        """
        updated_item = item.copy()
        
        # Update request body with the first available data
        if method_data:
            request_data = method_data[0]
            
            # Update request body
            if 'request' in updated_item:
                request = updated_item['request']
                
                # Update body
                if 'body' in request:
                    body = request['body']
                    if body.get('mode') == 'raw':
                        body['raw'] = json.dumps(request_data.request, indent=2)
                
                # Update URL if needed
                if 'url' in request:
                    url = request['url']
                    if 'path' in url:
                        # Ensure the method name is in the path
                        path_parts = url['path']
                        if path_parts and path_parts[-1] != request_data.method:
                            path_parts[-1] = request_data.method
        
        return updated_item 