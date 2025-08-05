#!/usr/bin/env python3
"""
Async Processors

Provides async processing capabilities for method mapping and file operations.
Significantly improves performance for large-scale operations.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from ..utils.logging_utils import get_logger

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
import re
import yaml

from ..managers.validation_manager import ValidationManager
from ..constants.enums import ValidationLevel


@dataclass
class ProcessingResult:
    """Result of file processing operation."""
    success: bool
    file_path: str
    processor_type: str
    data: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ProcessorConfig:
    """Configuration for file processors."""
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    timeout_seconds: int = 30
    encoding: str = 'utf-8'
    validation_level: ValidationLevel = ValidationLevel.NORMAL


class FileProcessorStrategy(ABC):
    """
    Abstract base class for file processor strategies.
    
    Defines the interface that all file processors must implement.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.NORMAL):
        self.validation_level = validation_level
        self.validator = ValidationManager(validation_level)
        self.logger = get_logger(f"processor-{self.__class__.__name__.lower()}")
    
    @abstractmethod
    def can_process(self, file_path: Path) -> bool:
        """Check if this processor can handle the given file."""
        pass
    
    @abstractmethod
    def process_file(self, file_path: Path) -> ProcessingResult:
        """Process the file and return results."""
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from the file."""
        pass
    
    def validate_file(self, file_path: Path) -> ProcessingResult:
        """Validate file before processing."""
        result = ProcessingResult(
            success=True,
            file_path=str(file_path),
            processor_type=self.__class__.__name__
        )
        
        if not file_path.exists():
            result.success = False
            result.errors.append(f"File not found: {file_path}")
            return result
        
        if not file_path.is_file():
            result.success = False
            result.errors.append(f"Not a file: {file_path}")
            return result
        
        return result


class JSONProcessorStrategy(FileProcessorStrategy):
    """Strategy for processing JSON files."""
    
    def can_process(self, file_path: Path) -> bool:
        """Check if file is a JSON file."""
        return file_path.suffix.lower() == '.json'
    
    def process_file(self, file_path: Path) -> ProcessingResult:
        """Process JSON file."""
        # Validate file first
        validation_result = self.validate_file(file_path)
        if not validation_result.success:
            return validation_result
        
        result = ProcessingResult(
            success=True,
            file_path=str(file_path),
            processor_type="JSONProcessor"
        )
        
        try:
            # Read and parse JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                data = json.loads(content)
                result.data = data
            except json.JSONDecodeError as e:
                result.success = False
                result.errors.append(f"Invalid JSON syntax: {e}")
                return result
            
            # Validate JSON structure
            validation = self.validator.validate_json(data)
            if not validation.is_valid:
                result.warnings.extend(validation.errors)
            
            # Extract metadata
            result.metadata = self.extract_metadata(file_path)
            
            # Detect specific JSON types
            result.metadata.update(self._detect_json_type(data))
            
            self.logger.debug(f"Successfully processed JSON file: {file_path}")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Error processing JSON file: {e}")
            self.logger.error(f"Failed to process {file_path}: {e}")
        
        return result
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from JSON file."""
        metadata = {
            "file_size": file_path.stat().st_size,
            "file_extension": file_path.suffix,
            "file_name": file_path.name
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata["content_length"] = len(content)
                metadata["line_count"] = content.count('\n') + 1
        except Exception as e:
            self.logger.warning(f"Could not extract metadata from {file_path}: {e}")
        
        return metadata
    
    def _detect_json_type(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Detect the type of JSON file based on structure."""
        json_type = "unknown"
        
        if isinstance(data, dict):
            # Check for KDF request/response patterns
            if "method" in data and "mmrpc" in data:
                if "result" in data or "error" in data:
                    json_type = "kdf_response"
                else:
                    json_type = "kdf_request"
            
            # Check for Postman collection patterns
            elif "info" in data and "item" in data:
                json_type = "postman_collection"
            
            # Check for OpenAPI patterns
            elif "openapi" in data or "swagger" in data:
                json_type = "openapi_spec"
            
            # Check for example data
            elif any(key in data for key in ["example", "examples", "request", "response"]):
                json_type = "api_example"
        
        return {"json_type": json_type}


class MDXProcessorStrategy(FileProcessorStrategy):
    """Strategy for processing MDX files."""
    
    def can_process(self, file_path: Path) -> bool:
        """Check if file is an MDX file."""
        return file_path.suffix.lower() == '.mdx'
    
    def process_file(self, file_path: Path) -> ProcessingResult:
        """Process MDX file."""
        validation_result = self.validate_file(file_path)
        if not validation_result.success:
            return validation_result
        
        result = ProcessingResult(
            success=True,
            file_path=str(file_path),
            processor_type="MDXProcessor"
        )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract MDX components
            extracted_data = self._extract_mdx_components(content)
            result.data = extracted_data
            
            # Validate MDX structure
            validation = self.validator.validate_file(file_path)
            if not validation.is_valid:
                result.warnings.extend(validation.errors)
            
            # Extract metadata
            result.metadata = self.extract_metadata(file_path)
            result.metadata.update(self._extract_mdx_metadata(content))
            
            self.logger.debug(f"Successfully processed MDX file: {file_path}")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Error processing MDX file: {e}")
            self.logger.error(f"Failed to process {file_path}: {e}")
        
        return result
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from MDX file."""
        metadata = {
            "file_size": file_path.stat().st_size,
            "file_extension": file_path.suffix,
            "file_name": file_path.name
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata["content_length"] = len(content)
                metadata["line_count"] = content.count('\n') + 1
                metadata["code_block_count"] = content.count('```')
        except Exception as e:
            self.logger.warning(f"Could not extract metadata from {file_path}: {e}")
        
        return metadata
    
    def _extract_mdx_components(self, content: str) -> Dict[str, Any]:
        """Extract various components from MDX content."""
        components = {
            "title": self._extract_title(content),
            "description": self._extract_description(content),
            "method_name": self._extract_method_name(content),
            "code_blocks": self._extract_code_blocks(content),
            "headings": self._extract_headings(content)
        }
        
        return components
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from MDX export statement."""
        title_pattern = r'export const title = ["\']([^"\']+)["\']'
        match = re.search(title_pattern, content)
        return match.group(1) if match else None
    
    def _extract_description(self, content: str) -> Optional[str]:
        """Extract description from MDX export statement."""
        desc_pattern = r'export const description = ["\']([^"\']+)["\']'
        match = re.search(desc_pattern, content)
        return match.group(1) if match else None
    
    def _extract_method_name(self, content: str) -> Optional[str]:
        """Extract method name from MDX heading."""
        method_pattern = r'##\s+([a-zA-Z0-9_:.-]+)\s*\{\{'
        match = re.search(method_pattern, content)
        return match.group(1) if match else None
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks from MDX content."""
        code_blocks = []
        code_pattern = r'```(\w+)?\n(.*?)\n```'
        
        for match in re.finditer(code_pattern, content, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2)
            code_blocks.append({
                "language": language,
                "code": code.strip()
            })
        
        return code_blocks
    
    def _extract_headings(self, content: str) -> List[Dict[str, str]]:
        """Extract headings from MDX content."""
        headings = []
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        
        for match in re.finditer(heading_pattern, content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({
                "level": level,
                "text": text
            })
        
        return headings
    
    def _extract_mdx_metadata(self, content: str) -> Dict[str, Any]:
        """Extract MDX-specific metadata."""
        metadata = {
            "has_exports": "export " in content,
            "has_imports": "import " in content,
            "component_count": len(re.findall(r'<[A-Z][a-zA-Z]*', content)),
            "jsx_element_count": len(re.findall(r'<\w+', content))
        }
        
        return metadata


class YAMLProcessorStrategy(FileProcessorStrategy):
    """Strategy for processing YAML files."""
    
    def can_process(self, file_path: Path) -> bool:
        """Check if file is a YAML file."""
        return file_path.suffix.lower() in ['.yaml', '.yaml']
    
    def process_file(self, file_path: Path) -> ProcessingResult:
        """Process YAML file."""
        validation_result = self.validate_file(file_path)
        if not validation_result.success:
            return validation_result
        
        result = ProcessingResult(
            success=True,
            file_path=str(file_path),
            processor_type="YAMLProcessor"
        )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                data = yaml.safe_load(content)
                result.data = data
            except yaml.YAMLError as e:
                result.success = False
                result.errors.append(f"Invalid YAML syntax: {e}")
                return result
            
            # Validate YAML structure
            validation = self.validator.validate_file(file_path)
            if not validation.is_valid:
                result.warnings.extend(validation.errors)
            
            # Extract metadata
            result.metadata = self.extract_metadata(file_path)
            result.metadata.update(self._detect_yaml_type(data))
            
            self.logger.debug(f"Successfully processed YAML file: {file_path}")
            
        except ImportError:
            result.success = False
            result.errors.append("PyYAML not installed - cannot process YAML files")
        except Exception as e:
            result.success = False
            result.errors.append(f"Error processing YAML file: {e}")
            self.logger.error(f"Failed to process {file_path}: {e}")
        
        return result
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from YAML file."""
        metadata = {
            "file_size": file_path.stat().st_size,
            "file_extension": file_path.suffix,
            "file_name": file_path.name
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata["content_length"] = len(content)
                metadata["line_count"] = content.count('\n') + 1
        except Exception as e:
            self.logger.warning(f"Could not extract metadata from {file_path}: {e}")
        
        return metadata
    
    def _detect_yaml_type(self, data: Any) -> Dict[str, str]:
        """Detect the type of YAML file based on structure."""
        yaml_type = "unknown"
        
        if isinstance(data, dict):
            # Check for OpenAPI patterns
            if "operationId" in data or "summary" in data:
                yaml_type = "openapi_path"
            elif "parameters" in data or "responses" in data:
                yaml_type = "api_definition"
            elif "get" in data or "post" in data or "put" in data or "delete" in data:
                yaml_type = "http_methods"
        
        return {"yaml_type": yaml_type}


class FileProcessorContext:
    """
    Context class that uses different processor strategies.
    
    Automatically selects the appropriate processor based on file type
    and provides a unified interface for file processing.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.NORMAL):
        self.validation_level = validation_level
        self.logger = get_logger("file-processor-context")
        
        # Initialize all available strategies
        self.strategies = [
            JSONProcessorStrategy(validation_level),
            MDXProcessorStrategy(validation_level),
            YAMLProcessorStrategy(validation_level)
        ]
        
        self.logger.debug(f"Initialized with {len(self.strategies)} processor strategies")
    
    def get_processor(self, file_path: Path) -> Optional[FileProcessorStrategy]:
        """Get the appropriate processor for the given file."""
        for strategy in self.strategies:
            if strategy.can_process(file_path):
                self.logger.debug(f"Selected {strategy.__class__.__name__} for {file_path}")
                return strategy
        
        self.logger.warning(f"No processor found for file type: {file_path.suffix}")
        return None
    
    def process_file(self, file_path: Union[str, Path]) -> ProcessingResult:
        """Process a file using the appropriate strategy."""
        file_path = Path(file_path)
        
        processor = self.get_processor(file_path)
        if not processor:
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                processor_type="Unknown",
                errors=[f"No processor available for file type: {file_path.suffix}"]
            )
        
        return processor.process_file(file_path)
    
    def process_files_batch(self, file_paths: List[Union[str, Path]]) -> List[ProcessingResult]:
        """Process multiple files using appropriate strategies."""
        results = []
        
        for file_path in file_paths:
            result = self.process_file(file_path)
            results.append(result)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        self.logger.stats("Batch Processing Results", {
            "Total files": len(results),
            "Successful": successful,
            "Failed": len(results) - successful,
            "Success rate": f"{(successful / len(results) * 100):.1f}%" if results else "0%"
        })
        
        return results
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        extensions = []
        
        # Test with dummy paths to get supported extensions
        test_extensions = ['.json', '.mdx', '.yaml', '.txt', '.md']
        
        for ext in test_extensions:
            test_path = Path(f"test{ext}")
            if self.get_processor(test_path):
                extensions.append(ext)
        
        return extensions
    
    def add_strategy(self, strategy: FileProcessorStrategy):
        """Add a new processor strategy."""
        self.strategies.append(strategy)
        self.logger.debug(f"Added processor strategy: {strategy.__class__.__name__}")
    
    def remove_strategy(self, strategy_class: type):
        """Remove a processor strategy by class type."""
        self.strategies = [s for s in self.strategies if not isinstance(s, strategy_class)]
        self.logger.debug(f"Removed processor strategy: {strategy_class.__name__}")


# Convenience functions
def create_file_processor(validation_level: ValidationLevel = ValidationLevel.NORMAL) -> FileProcessorContext:
    """Create a file processor context with default strategies."""
    return FileProcessorContext(validation_level)


def process_single_file(file_path: Union[str, Path], 
                       validation_level: ValidationLevel = ValidationLevel.NORMAL) -> ProcessingResult:
    """Process a single file with automatic processor selection."""
    processor = create_file_processor(validation_level)
    return processor.process_file(file_path) 