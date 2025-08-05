#!/usr/bin/env python3
"""
Postman Collection Parser

Parses Postman collection files to extract method mappings and request information.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..utils.logging_utils import get_logger
from ..constants import PostmanRequestInfo, PostmanMethodMapping
from ..utils.file_utils import safe_read_json


class PostmanCollectionParser:
    """
    Parses Postman collection files to extract method and request information.
    
    Provides functionality to:
    - Parse collection structure
    - Extract method names from requests
    - Map methods to folder hierarchies
    - Generate hotlinks for direct access
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = get_logger("postman-parser")
    
    def parse_collection_file(self, collection_path: str) -> Dict[str, PostmanMethodMapping]:
        """
        Parse a Postman collection file and extract method mappings.
        
        Args:
            collection_path: Path to the Postman collection JSON file
            
        Returns:
            Dictionary mapping method names to PostmanMethodMapping objects
        """
        try:
            collection_data = safe_read_json(collection_path)
            
            # Extract version from collection info
            version = self._extract_version_from_collection(collection_data, collection_path)
            
            # Parse collection structure
            methods = {}
            self._parse_collection_items(
                collection_data.get('item', []), 
                methods, 
                collection_path, 
                version, 
                []
            )
            
            if self.verbose:
                self.logger.info(f"Parsed {len(methods)} methods from {Path(collection_path).name}")
            
            return methods
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Failed to parse collection {collection_path}: {e}")
            return {}
    
    def _extract_version_from_collection(self, collection_data: Dict[str, Any], file_path: str) -> str:
        """Extract API version from collection data or filename."""
        # Try to get version from collection name
        collection_name = collection_data.get('info', {}).get('name', '')
        
        # Look for version patterns in name
        version_patterns = [
            r'API\s+V(\d+)',
            r'Framework\s+V(\d+)',
            r'v(\d+)',
            r'V(\d+)'
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, collection_name, re.IGNORECASE)
            if match:
                return f"v{match.group(1)}"
        
        # Fallback to filename
        filename = Path(file_path).name.lower()
        if 'v1' in filename:
            return 'v1'
        elif 'v2' in filename:
            return 'v2'
        
        return 'unknown'
    
    def _parse_collection_items(self, items: List[Dict], methods: Dict[str, PostmanMethodMapping], 
                              collection_path: str, version: str, current_path: List[str]) -> None:
        """Recursively parse collection items (folders and requests)."""
        for item_index, item in enumerate(items):
            if 'item' in item:
                # This is a folder
                folder_name = item.get('name', f'Folder_{item_index}')
                folder_path = current_path + [folder_name]
                
                # Recursively parse folder items
                self._parse_collection_items(
                    item['item'], 
                    methods, 
                    collection_path, 
                    version, 
                    folder_path
                )
            else:
                # This is a request
                request_info = self._extract_request_info(item, current_path, item_index)
                if request_info:
                    method_name = request_info.method_name
                    
                    # Create or update method mapping
                    if method_name not in methods:
                        methods[method_name] = PostmanMethodMapping(
                            method_name=method_name,
                            collection_file=collection_path,
                            collection_version=version,
                            requests=[],
                            folder_hierarchy=current_path
                        )
                    
                    methods[method_name].requests.append(request_info)
    
    def _extract_request_info(self, request_item: Dict, folder_path: List[str], 
                            item_index: int) -> Optional[PostmanRequestInfo]:
        """Extract request information from a Postman request item."""
        try:
            request_name = request_item.get('name', '')
            request_data = request_item.get('request', {})
            
            # Extract method name from request body or name
            method_name = self._extract_method_name_from_request(request_data, request_name)
            
            if not method_name:
                return None
            
            # Extract operation type from request name
            operation_type = self._extract_operation_type(request_name)
            
            return PostmanRequestInfo(
                name=request_name,
                method_name=method_name,
                folder_path=folder_path,
                item_index=item_index,
                description=request_data.get('description', ''),
                operation_type=operation_type
            )
            
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Failed to extract request info: {e}")
            return None
    
    def _extract_method_name_from_request(self, request_data: Dict, request_name: str) -> Optional[str]:
        """Extract the API method name from request data."""
        # Try to get method from request body
        body = request_data.get('body', {})
        if body.get('mode') == 'raw':
            try:
                raw_body = body.get('raw', '')
                if raw_body:
                    body_json = json.loads(raw_body)
                    method = body_json.get('method')
                    if method:
                        return method
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Try to extract from request name
        # Pattern: "method_name - Operation-Type"
        if ' - ' in request_name:
            potential_method = request_name.split(' - ')[0].strip()
            # Validate that it looks like a method name
            if self._is_valid_method_name(potential_method):
                return potential_method
        
        # Try to extract method patterns from request name
        method_patterns = [
            r'^([a-zA-Z_][a-zA-Z0-9_:]*(?:::[a-zA-Z_][a-zA-Z0-9_]*)*)\s*-',  # method::name - ...
            r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*-',  # method_name - ...
        ]
        
        for pattern in method_patterns:
            match = re.match(pattern, request_name)
            if match:
                method = match.group(1)
                if self._is_valid_method_name(method):
                    return method
        
        return None
    
    def _is_valid_method_name(self, method_name: str) -> bool:
        """Check if a string looks like a valid API method name."""
        if not method_name:
            return False
        
        # Valid method names should:
        # - Start with letter or underscore
        # - Contain only letters, numbers, underscores, and colons
        # - Not be too short or too long
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_:]*$'
        
        return (
            bool(re.match(pattern, method_name)) and 
            2 <= len(method_name) <= 100 and
            not method_name.startswith('__')  # Avoid Python special methods
        )
    
    def _extract_operation_type(self, request_name: str) -> str:
        """Extract operation type from request name."""
        operation_patterns = {
            'basic': r'Basic\s+Request',
            'doc': r'Doc\s+Operation',
            'example': r'Example-\d+',
            'error': r'Error\s+Response',
            'advanced': r'Advanced\s+Request'
        }
        
        for op_type, pattern in operation_patterns.items():
            if re.search(pattern, request_name, re.IGNORECASE):
                return op_type
                
        return 'default'
    
    def generate_postman_hotlinks(self, method_mappings: Dict[str, PostmanMethodMapping]) -> Dict[str, Dict]:
        """
        Generate hotlink information for method mappings.
        
        Args:
            method_mappings: Dictionary of method mappings
            
        Returns:
            Dictionary with hotlink information for each method
        """
        hotlinks = {}
        
        for method_name, mapping in method_mappings.items():
            collection_filename = Path(mapping.collection_file).name
            
            # Generate import URL (for local files, this would be a file:// URL)
            import_url = f"postman://collection/import?url=file://{mapping.collection_file}"
            
            # Generate direct links to requests
            request_links = []
            for request in mapping.requests:
                folder_path = " > ".join(request.folder_path)
                direct_link = f"#{'/'.join(request.folder_path)}/{request.name}"
                
                request_links.append({
                    "name": request.name,
                    "operation_type": request.operation_type,
                    "folder_path": folder_path,
                    "direct_link": direct_link,
                    "item_index": request.item_index
                })
            
            hotlinks[method_name] = {
                "collection_info": {
                    "file": collection_filename,
                    "version": mapping.collection_version,
                    "full_path": mapping.collection_file
                },
                "folder_hierarchy": mapping.folder_hierarchy,
                "import_url": import_url,
                "request_count": len(mapping.requests),
                "requests": request_links
            }
        
        return hotlinks
    
    def parse_all_collections(self, collections_dir: str = "postman/collections") -> Dict[str, Dict[str, PostmanMethodMapping]]:
        """
        Parse all Postman collection files in a directory.
        
        Args:
            collections_dir: Directory containing collection files
            
        Returns:
            Dictionary mapping versions to method mappings
        """
        collections_path = Path(collections_dir)
        all_mappings = {}
        
        if not collections_path.exists():
            if self.verbose:
                self.logger.warning(f"Collections directory not found: {collections_dir}")
            return all_mappings
        
        # Find collection files
        collection_files = list(collections_path.glob("*.json"))
        
        if self.verbose:
            self.logger.info(f"Found {len(collection_files)} collection files")
        
        for collection_file in collection_files:
            if self.verbose:
                self.logger.info(f"Parsing {collection_file.name}...")
            
            methods = self.parse_collection_file(str(collection_file))
            
            # Organize by version
            for method_name, mapping in methods.items():
                version = mapping.collection_version
                if version not in all_mappings:
                    all_mappings[version] = {}
                all_mappings[version][method_name] = mapping
        
        return all_mappings 