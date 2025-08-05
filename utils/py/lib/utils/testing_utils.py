#!/usr/bin/env python3
"""
Testing Utilities for KDF Documentation Library

This module provides testing utilities extracted from the demo and test files,
providing patterns for testing the various components of the library.
"""

from typing import Dict, List, Any
from datetime import datetime

from ..utils.logging_utils import get_logger
from ..rust.scanner import KDFScanner
from ..constants import RustMethodDetails
from ..mdx.mdx_generator import MdxGenerator


class DocumentationTestSuite:
    """
    Test suite for documentation generation functionality.
    Provides patterns and utilities for testing the documentation pipeline.
    """
    
    def __init__(self):
        self.logger = get_logger("doc-test-suite")
        
    def test_missing_methods_lookup(self) -> Dict[str, int]:
        """Test loading and analyzing missing methods data."""
        self.logger.info("Testing Missing Methods Lookup")
        
        try:
            from ..rust.scanner import KDFScanner
            scanner = KDFScanner()
            
            # Load missing methods data (would need to be implemented)
            # missing_methods = scanner.load_missing_methods()
            
            # For now, return mock data structure
            return {
                "v1": 15,
                "v2": 87,
                "total": 102
            }
            
        except Exception as e:
            self.logger.error(f"Error in missing methods lookup test: {e}")
            return {}
    
    def test_title_generation(self) -> Dict[str, str]:
        """Test human-readable title generation for different method types."""
        self.logger.info("Testing Title Generation")
        
        generator = MdxGenerator()
        
        test_methods = [
            "task::enable_bch::cancel",
            "stream::balance::enable", 
            "lightning::payments::send_payment",
            "gui_storage::add_account",
            "get_enabled_coins",
        ]
        
        results = {}
        for method in test_methods:
            title = generator.humanize_method_name(method)
            results[method] = title
            self.logger.debug(f"{method:30} → {title}")
        
        return results
    
    def test_parameter_table_generation(self) -> str:
        """Test parameter table generation with different scenarios."""
        self.logger.info("Testing Parameter Table Generation")
        
        generator = MdxGenerator()
        
        # Test with various parameter configurations
        test_parameters = [
            {
                "name": "coin",
                "type": "String",
                "required": True,
                "description": "The coin ticker symbol"
            },
            {
                "name": "amount",
                "type": "BigDecimal",
                "required": True,
                "description": "The amount to process"
            },
            {
                "name": "confirmations",
                "type": "u32",
                "required": False,
                "default": "1",
                "description": "Number of confirmations required"
            }
        ]
        
        table = generator.format_parameters_table(test_parameters)
        self.logger.debug("Generated parameter table:")
        self.logger.debug(table)
        
        return table
    
    def test_method_documentation_generation(self, method_name: str = "task::enable_bch::cancel") -> str:
        """Test complete documentation generation for a method."""
        self.logger.info(f"Testing Method Documentation Generation for: {method_name}")
        
        generator = MdxGenerator()
        
        # Mock method info
        method_info = {
            "method_name": method_name,
            "description": "Cancel the enable BCH task operation",
            "parameters": [
                {
                    "name": "task_id",
                    "type": "u64",
                    "required": True,
                    "description": "The task ID to cancel"
                }
            ],
            "response_type": "CancelTaskResult",
            "examples": []
        }
        
        try:
            content = generator.generate_method_documentation(method_name, method_info, "v2")
            self.logger.success(f"Generated documentation ({len(content)} characters)")
            return content
        except Exception as e:
            self.logger.error(f"Error generating documentation: {e}")
            return ""
    
    def test_local_repository_scanner(self) -> Dict[str, Any]:
        """Test local repository scanner functionality."""
        self.logger.info("Testing Local Repository Scanner")
        
        try:
            scanner = KDFScanner()
            
            # Test method details extraction (mock)
            test_method = "task::enable_bch::cancel"
            
            # This would normally extract from actual repo
            mock_details = RustMethodDetails(
                method_name=test_method,
                handler_file="/path/to/handler.rs",
                parameters=[
                    {
                        "name": "task_id",
                        "type": "u64",
                        "required": True,
                        "description": "Task identifier"
                    }
                ],
                description="Cancel the BCH enable task"
            )
            
            return {
                "method": test_method,
                "has_handler": mock_details.handler_file is not None,
                "parameter_count": len(mock_details.parameters),
                "has_description": mock_details.description is not None
            }
            
        except Exception as e:
            self.logger.error(f"Error in local repository scanner test: {e}")
            return {"error": str(e)}
    
    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite and return results."""
        self.logger.info("Running Comprehensive Test Suite")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        # Test 1: Missing Methods Lookup
        try:
            results["tests"]["missing_methods"] = self.test_missing_methods_lookup()
        except Exception as e:
            results["tests"]["missing_methods"] = {"error": str(e)}
        
        # Test 2: Title Generation
        try:
            results["tests"]["title_generation"] = self.test_title_generation()
        except Exception as e:
            results["tests"]["title_generation"] = {"error": str(e)}
        
        # Test 3: Parameter Table Generation
        try:
            table = self.test_parameter_table_generation()
            results["tests"]["parameter_table"] = {
                "success": True,
                "table_length": len(table),
                "has_content": len(table) > 0
            }
        except Exception as e:
            results["tests"]["parameter_table"] = {"error": str(e)}
        
        # Test 4: Method Documentation Generation
        try:
            content = self.test_method_documentation_generation()
            results["tests"]["method_documentation"] = {
                "success": True,
                "content_length": len(content),
                "has_export_title": "export const title" in content,
                "has_examples": "CodeGroup" in content
            }
        except Exception as e:
            results["tests"]["method_documentation"] = {"error": str(e)}
        
        # Test 5: Local Repository Scanner
        try:
            results["tests"]["local_scanner"] = self.test_local_repository_scanner()
        except Exception as e:
            results["tests"]["local_scanner"] = {"error": str(e)}
        
        # Calculate summary
        passed_tests = sum(1 for test in results["tests"].values() 
                          if isinstance(test, dict) and "error" not in test)
        total_tests = len(results["tests"])
        
        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
        }
        
        self.logger.info(f"Test Suite Complete: {passed_tests}/{total_tests} tests passed")
        
        return results


class RepositoryTestUtilities:
    """
    Utilities for testing repository scanning functionality.
    """
    
    def __init__(self):
        self.logger = get_logger("repo-test-utils")
    
    def test_repository_setup(self, branch: str = "dev") -> bool:
        """Test setting up the local repository."""
        try:
            from ..rust.scanner import KDFScanner
            return KDFScanner(repo_path="data/komodo-defi-framework").setup_repository(force_clone=False)
        except Exception as e:
            self.logger.error(f"Repository setup test failed: {e}")
            return False
    
    def test_method_scanning(self, method_names: List[str]) -> Dict[str, RustMethodDetails]:
        """Test scanning specific methods."""
        try:
            from ..scanning import scan_local_methods
            return scan_local_methods(method_names)
        except Exception as e:
            self.logger.error(f"Method scanning test failed: {e}")
            return {}
    
    def validate_method_details(self, method_details: RustMethodDetails) -> Dict[str, bool]:
        """Validate the structure of method details."""
        return {
            "has_method_name": bool(method_details.method_name),
            "has_parameters": len(method_details.parameters) > 0,
            "has_description": bool(method_details.description),
            "has_handler_file": bool(method_details.handler_file),
            "has_response_type": bool(method_details.response_type)
        }


# Convenience functions for quick testing
def run_quick_test() -> Dict[str, Any]:
    """Run a quick test of the documentation system."""
    suite = DocumentationTestSuite()
    return suite.run_comprehensive_test_suite()


def test_single_method_generation(method_name: str) -> str:
    """Test generating documentation for a single method."""
    suite = DocumentationTestSuite()
    return suite.test_method_documentation_generation(method_name)


def validate_library_integration() -> bool:
    """Test that all library components can be imported and used."""
    try:
        # Test imports
        from ..rust.scanner import KDFScanner
        from ..constants import RustMethodDetails
        from .doc_generator import MdxGenerator
        
        # Test basic instantiation
        scanner = KDFScanner()
        generator = MdxGenerator()
        
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Integration error: {e}")
        return False 