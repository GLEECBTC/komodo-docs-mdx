#!/usr/bin/env python3
"""
Extractors for different source types (MDX docs, Postman collections).
Consolidates extraction logic using existing lib infrastructure.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from .base import BaseExtractor, RequestData
from ..postman.postman_scanner import MdxJsonExampleExtractor
from ..mdx.mdx_scanner import UnifiedScanner
from ..utils.logging_utils import get_logger


class MDXExtractor(BaseExtractor):
    """Extractor for MDX documentation files using existing infrastructure."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.existing_extractor = MdxJsonExampleExtractor(verbose=True)
        self.scanner = UnifiedScanner(verbose=True)
    
    def extract_requests(self, source_path: Union[str, Path]) -> List[RequestData]:
        """
        Extract requests from MDX documentation using existing infrastructure.
        
        Args:
            source_path: Path to MDX docs directory
            
        Returns:
            List of RequestData objects
        """
        source_path = Path(source_path)
        requests = []
        
        # Find all MDX files
        mdx_files = list(source_path.rglob("*.mdx"))
        self.logger.info(f"Found {len(mdx_files)} MDX files to process")
        
        for mdx_file in mdx_files:
            try:
                file_requests = self._extract_from_file(mdx_file)
                requests.extend(file_requests)
                if file_requests:
                    self.logger.debug(f"Extracted {len(file_requests)} requests from {mdx_file}")
            except Exception as e:
                self.logger.error(f"Failed to extract from {mdx_file}: {e}")
        
        self.logger.info(f"Total extracted requests: {len(requests)}")
        return requests
    
    def _extract_from_file(self, file_path: Path) -> List[RequestData]:
        """
        Extract requests from a single MDX file using existing extractor.
        
        Args:
            file_path: Path to MDX file
            
        Returns:
            List of RequestData objects
        """
        # Use existing MDX extractor
        extracted_examples = self.existing_extractor.extract_examples_from_file(str(file_path))
        
        requests = []
        for example in extracted_examples:
            try:
                # Convert ExtractedExample to RequestData
                request_data = RequestData(
                    method=example.method_name,
                    request=example.content,
                    source_file=str(file_path),
                    example_index=0,  # We'll need to track this better
                    source='mdx',
                    version=example.version,
                    description=example.description
                )
                
                # Standardize request
                request_data.request = self.standardize_request({
                    'method': request_data.method,
                    'request': request_data.request,
                    'version': request_data.version
                })['request']
                
                if self.validate_request({
                    'method': request_data.method,
                    'request': request_data.request
                }):
                    requests.append(request_data)
                else:
                    self.logger.warning(f"Invalid request in {file_path}: {example.method_name}")
                    
            except Exception as e:
                self.logger.error(f"Error processing example in {file_path}: {e}")
        
        return requests


class PostmanExtractor(BaseExtractor):
    """Extractor for Postman collections using existing infrastructure."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
    
    def extract_requests(self, source_path: Union[str, Path]) -> List[RequestData]:
        """
        Extract requests from Postman collection using existing infrastructure.
        
        Args:
            source_path: Path to Postman collection file
            
        Returns:
            List of RequestData objects
        """
        source_path = Path(source_path)
        
        if not source_path.exists():
            self.logger.error(f"Postman collection not found: {source_path}")
            return []
        
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                collection_data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load Postman collection: {e}")
            return []
        
        requests = []
        
        # Extract requests from collection
        if 'item' in collection_data:
            requests.extend(self._extract_from_items(collection_data['item'], source_path))
        
        self.logger.info(f"Extracted {len(requests)} requests from Postman collection")
        return requests
    
    def _extract_from_items(self, items: List[Dict[str, Any]], source_path: Path) -> List[RequestData]:
        """
        Extract requests from Postman collection items.
        
        Args:
            items: List of Postman collection items
            source_path: Path to source file for metadata
            
        Returns:
            List of RequestData objects
        """
        requests = []
        
        for item in items:
            # Handle folders
            if 'item' in item:
                requests.extend(self._extract_from_items(item['item'], source_path))
            
            # Handle requests
            if 'request' in item:
                request_data = self._extract_single_request(item, source_path)
                if request_data:
                    requests.append(request_data)
        
        return requests
    
    def _extract_single_request(self, item: Dict[str, Any], source_path: Path) -> Optional[RequestData]:
        """
        Extract a single request from Postman collection item.
        
        Args:
            item: Postman collection item
            source_path: Path to source file for metadata
            
        Returns:
            RequestData object or None if extraction failed
        """
        try:
            request = item.get('request', {})
            method = request.get('method', '').upper()
            url = request.get('url', {})
            
            # Extract method name from URL path
            method_name = self._extract_method_from_url(url)
            if not method_name:
                return None
            
            # Extract request body
            body = request.get('body', {})
            request_data = self._extract_request_body(body, method_name)
            
            if not request_data:
                return None
            
            # Create RequestData object
            return RequestData(
                method=method_name,
                request=request_data,
                source_file=str(source_path),
                source='postman',
                version=self._determine_version(request_data),
                description=item.get('name', '')
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting request from item: {e}")
            return None
    
    def _extract_method_from_url(self, url: Dict[str, Any]) -> Optional[str]:
        """
        Extract method name from Postman URL.
        
        Args:
            url: Postman URL object
            
        Returns:
            Method name or None
        """
        try:
            path_parts = url.get('path', [])
            
            for part in reversed(path_parts):
                if part and part != 'api':
                    return part
            
            return None
        except Exception:
            return None
    
    def _extract_request_body(self, body: Dict[str, Any], method_name: str) -> Optional[Dict[str, Any]]:
        """
        Extract request body from Postman body.
        
        Args:
            body: Postman body object
            method_name: Method name for context
            
        Returns:
            Request data dictionary or None
        """
        try:
            mode = body.get('mode', '')
            
            if mode == 'raw':
                raw_data = body.get('raw', '')
                try:
                    return json.loads(raw_data)
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON in request body for {method_name}")
                    return None
            
            elif mode == 'urlencoded':
                # Convert URL encoded data to JSON
                urlencoded = body.get('urlencoded', [])
                request_data = {}
                
                for param in urlencoded:
                    key = param.get('key', '')
                    value = param.get('value', '')
                    if key:
                        request_data[key] = value
                
                return request_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting request body: {e}")
            return None
    
    def _determine_version(self, request_data: Dict[str, Any]) -> str:
        """
        Determine API version from request data.
        
        Args:
            request_data: Request data dictionary
            
        Returns:
            API version ('v1' or 'v2')
        """
        # Check for mmrpc field (v2)
        if 'mmrpc' in request_data:
            return 'v2'
        
        # Check for userpass field (v1)
        if 'userpass' in request_data:
            return 'v1'
        
        # Default to v2
        return 'v2' 