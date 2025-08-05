#!/usr/bin/env python3
"""
Exception Classes

Common exception hierarchy for the Komodo Documentation Library.
Provides specific exceptions for different error scenarios.
"""

from typing import Optional, Dict, Any


class KomodoLibraryError(Exception):
    """Base exception for all library errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class FileOperationError(KomodoLibraryError):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 operation: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.operation = operation


class ValidationError(KomodoLibraryError):
    """Raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value


class ParseError(KomodoLibraryError):
    """Raised when parsing fails."""
    
    def __init__(self, message: str, parser_type: Optional[str] = None, 
                 source_file: Optional[str] = None, line_number: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.parser_type = parser_type
        self.source_file = source_file
        self.line_number = line_number


class ConfigurationError(KomodoLibraryError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.config_key = config_key


class MethodNotFoundError(KomodoLibraryError):
    """Raised when a method cannot be found or mapped."""
    
    def __init__(self, message: str, method_name: Optional[str] = None, 
                 search_locations: Optional[list] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.method_name = method_name
        self.search_locations = search_locations or []


class PostmanGenerationError(KomodoLibraryError):
    """Raised when Postman collection generation fails."""
    
    def __init__(self, message: str, collection_version: Optional[str] = None, 
                 failed_method: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.collection_version = collection_version
        self.failed_method = failed_method


class OpenAPIError(KomodoLibraryError):
    """Raised when OpenAPI operations fail."""
    
    def __init__(self, message: str, spec_file: Optional[str] = None, 
                 operation: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.spec_file = spec_file
        self.operation = operation


class ExtractionError(KomodoLibraryError):
    """Raised when example extraction fails."""
    
    def __init__(self, message: str, source_file: Optional[str] = None, 
                 extraction_type: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.source_file = source_file
        self.extraction_type = extraction_type


class DeduplicationError(KomodoLibraryError):
    """Raised when deduplication operations fail."""
    
    def __init__(self, message: str, duplicate_count: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.duplicate_count = duplicate_count


class MappingError(KomodoLibraryError):
    """Raised when method mapping operations fail."""
    
    def __init__(self, message: str, mapping_type: Optional[str] = None, 
                 failed_methods: Optional[list] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.mapping_type = mapping_type
        self.failed_methods = failed_methods or []


# Convenience functions for common error scenarios
def raise_file_not_found(file_path: str, operation: str = "read") -> None:
    """Raise a FileOperationError for missing files."""
    raise FileOperationError(
        f"File not found: {file_path}",
        file_path=file_path,
        operation=operation
    )


def raise_invalid_json(file_path: str, error_details: str = "") -> None:
    """Raise a ParseError for invalid JSON."""
    message = f"Invalid JSON in file: {file_path}"
    if error_details:
        message += f" - {error_details}"
    raise ParseError(
        message,
        parser_type="json",
        source_file=file_path
    )


def raise_method_not_mapped(method_name: str, search_locations: list = None) -> None:
    """Raise a MethodNotFoundError for unmapped methods."""
    raise MethodNotFoundError(
        f"Method '{method_name}' could not be found or mapped",
        method_name=method_name,
        search_locations=search_locations
    ) 