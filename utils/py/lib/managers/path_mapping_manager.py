
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from functools import lru_cache
import json
from ..constants.config import EnhancedKomodoConfig, get_config
from ..utils.logging_utils import get_logger
from ..constants.data_structures import PathMapping
from ..constants.enums import VersionStatus


class EnhancedPathMapper:
    """
    Enhanced path mapper that uses centralized configuration.
    """
    
    def __init__(self, config: Optional[EnhancedKomodoConfig] = None):
        self.config = config or get_config()
        self.logger = get_logger('path_mapping_manager')
        self.category_mappings = self._initialize_category_mappings()
        
    def _initialize_category_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        Initialize category mappings for different versions.
        This allows for flexible restructuring of categories.
        """
        try:
            mappings_path = Path(self.config._resolve_path(self.config.directories.category_mappings))
            with open(mappings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"!!!!!!!!!!!!! Error initializing category mappings: {e} !!!!!!!!!!!!")
            return {
                "v2": {"_default": "misc_cat_mapping_error"},
                "v1": {"_default": "misc_cat_mapping_error"}
            }
    
    def get_method_path_mapping(self, method_name: str, mdx_path: str, version: str) -> PathMapping:
        """
        Get complete path mapping for a method using enhanced configuration.
        
        Args:
            method_name: The canonical method name (e.g., "task::enable_eth::init")
            mdx_path: The current MDX file path
            version: The API version
            
        Returns:
            PathMapping with all generated paths and enhanced metadata
        """
        # Normalize version using configuration
        normalized_version = self.config.version_mapping.get_canonical_version(version)
        
        # Get version metadata from configuration
        version_status = self.config.version_mapping.get_version_status(normalized_version)
        migration_target = self.config.version_mapping.get_migration_target(normalized_version)
        is_deprecated = self.config.version_mapping.is_deprecated(normalized_version)
        
        # Extract category and subcategory from MDX path
        category, subcategory = self._extract_category_from_mdx_path(mdx_path, normalized_version)
        
        # Generate all paths using configuration
        try:
            base_json_dir = self.config.get_directory_for_version_and_type(normalized_version, "json")
        except Exception:
            # Fallback for unsupported versions
            base_json_dir = ""
        
        openapi_path = self._generate_openapi_method_path(method_name, normalized_version, category, subcategory)
        postman_json_path = self._generate_postman_json_path(method_name, category, subcategory, base_json_dir)
        postman_collection_path = self._generate_postman_collection_path(category, subcategory, normalized_version)
        
        return PathMapping(
            method_name=method_name,
            version=normalized_version,
            mdx_path=mdx_path,
            category=category,
            subcategory=subcategory,
            openapi_path=openapi_path,
            postman_json_path=postman_json_path,
            postman_collection_path=postman_collection_path,
            deprecated=is_deprecated,
            migration_source=None,  # Could be enhanced later
            version_status=version_status,
            migration_target=migration_target
        )
    
    @lru_cache(maxsize=256)
    def _extract_category_from_mdx_path(self, mdx_path: str, version: str) -> Tuple[str, Optional[str]]:
        """Extract category and subcategory from MDX path using configuration."""
        try:
            # Get the base MDX directory for this version
            base_mdx_dir = self.config.get_directory_for_version_and_type(version, "mdx")
            base_mdx_path = Path(base_mdx_dir)
            
            # Make mdx_path relative to base
            mdx_path_obj = Path(mdx_path)
            if mdx_path_obj.is_absolute():
                try:
                    relative_path = mdx_path_obj.relative_to(base_mdx_path)
                except ValueError:
                    # Path is not under base directory, extract from path
                    relative_path = mdx_path_obj
            else:
                relative_path = mdx_path_obj
            
            # Extract category from path parts
            parts = relative_path.parts
            if len(parts) >= 2:
                category = parts[0]
                subcategory = parts[1] if len(parts) > 2 else None
            elif len(parts) == 1:
                category = parts[0]
                subcategory = None
            else:
                self.logger.warning(f"!!!!!!!!!!!! Error extracting category from MDX path: {parts}. Setting to misc !!!!!!!!!!!!")
                category = "misc_extraction_error"
                subcategory = None
            
            # Apply category mappings
            category_map = self.category_mappings.get(version, {})
            mapped_category = category_map.get(category, category_map.get("_default", category))
            
            return mapped_category, subcategory
            
        except Exception as e:  
            # Fallback category extraction
            self.logger.warning(f"!!!!!!!!!!!! Error extracting category from MDX path: {e}. Setting to misc_error !!!!!!!!!!!!")
            return "misc_extraction_exception", None
    
    def _generate_openapi_method_path(self, method_name: str, version: str, category: str, subcategory: Optional[str]) -> str:
        """Generate OpenAPI YAML file path."""
        base_dir = self.config.directories.openapi_paths
        
        # Convert method name to filename
        filename = self._method_name_to_filename(method_name) + ".yaml"
        base_path = Path(base_dir)
        
        if subcategory:
            return str(base_path / category / subcategory / filename)
        else:
            return str(base_path / category / filename)
    
    def _generate_postman_json_path(self, method_name: str, category: str, subcategory: Optional[str], base_dir: str) -> str:
        """Generate Postman JSON file path."""
        if not base_dir:
            return ""
        
        # Convert method name to directory name
        method_dir = self._method_name_to_filename(method_name)
        base_path = Path(base_dir)
        
        if subcategory:
            return str(base_path / category / subcategory / method_dir)
        else:
            return str(base_path / category / method_dir)
    
    def _generate_postman_collection_path(self, category: str, subcategory: Optional[str], version: str) -> str:
        """Generate Postman collection path using configuration."""
        try:
            collections_dir = Path(self.config._resolve_path(self.config.directories.postman_collections))
            
            if subcategory:
                return str(collections_dir / f"{version}_{category}_{subcategory}.json")
            else:
                return str(collections_dir / f"{version}_{category}.json")
        except Exception:
            return ""
    
    @lru_cache(maxsize=128)
    def _method_name_to_filename(self, method_name: str) -> str:
        """Convert method name to filename format."""
        return method_name.replace("::", "-")
    
    def get_schema_path(self, schema_name: str) -> Optional[Path]:
        """Constructs the full path to a schema file in the components directory."""
        try:
            schemas_dir = Path(self.config.directories.openapi_schemas)
            
            schema_file = schemas_dir / f"{self._method_name_to_filename(schema_name)}.yaml"
            if schema_file.exists():
                return schema_file
        except Exception:
            return None
        return None

    def get_version_from_path(self, file_path: str) -> Optional[str]:
        """
        Determine API version from a file path.
        """
        path_str = str(file_path)

        v1_dir = str(self.config.get_directory_for_version_and_type("v1", "yaml"))
        v2_dir = str(self.config.get_directory_for_version_and_type("v2", "yaml"))
        v2_dev_dir = str(self.config.get_directory_for_version_and_type("v2_dev", "yaml"))
        
        if v1_dir in path_str:
            return "v1"
        if v2_dir in path_str or v2_dev_dir in path_str:
            return "v2"
        return None

    def get_supported_versions(self, include_deprecated: bool = False) -> List[str]:
        """Get list of supported versions from configuration."""
        versions = []
        for version_name, version_config in self.config.versions.items():
            if include_deprecated or version_config.status != VersionStatus.LEGACY:
                versions.append(version_name)
        return versions
    
    def handle_version_migration(self, method_name: str, from_version: str, to_version: str, 
                                dry_run: bool = False) -> Dict[str, str]:
        """
        Handle version migration using configuration system.
        
        Returns:
            Dictionary with migration information and actions taken
        """
        from_normalized = self.config.version_mapping.get_canonical_version(from_version)
        to_normalized = self.config.version_mapping.get_canonical_version(to_version)
        
        migration_info = {
            "method": method_name,
            "from_version": from_normalized,
            "to_version": to_normalized,
            "status": "planned" if dry_run else "completed",
            "actions": []
        }
        
        # Check if migration is supported
        migration_target = self.config.version_mapping.get_migration_target(from_normalized)
        if migration_target and migration_target != to_normalized:
            migration_info["warnings"] = [
                f"Version {from_normalized} is configured to migrate to {migration_target}, not {to_normalized}"
            ]
        
        # Generate old and new paths
        try:
            old_mdx_dir = self.config.get_directory_for_version_and_type(from_normalized, "mdx")
            new_mdx_dir = self.config.get_directory_for_version_and_type(to_normalized, "mdx")
            
            migration_info["actions"].append({
                "type": "move_mdx",
                "from": old_mdx_dir,
                "to": new_mdx_dir,
                "executed": not dry_run
            })
        except Exception as e:
            migration_info["errors"] = [f"Failed to determine migration paths: {e}"]
        
        return migration_info
    
    def create_directory_structure(self, path_mapping: PathMapping, dry_run: bool = False) -> List[str]:
        """Create directory structure for a path mapping."""
        directories_to_create = []
        
        # Collect all directories that need to be created
        if path_mapping.openapi_path:
            directories_to_create.append(Path(path_mapping.openapi_path).parent)
        
        if path_mapping.postman_json_path:
            directories_to_create.append(Path(path_mapping.postman_json_path))
        
        if path_mapping.postman_collection_path:
            directories_to_create.append(Path(path_mapping.postman_collection_path).parent)
        
        created_dirs = []
        for directory in directories_to_create:
            if directory and not directory.exists():
                if not dry_run:
                    try:
                        directory.mkdir(parents=True, exist_ok=True)
                        created_dirs.append(str(directory))
                    except Exception as e:
                        # Log error but continue
                        pass
                else:
                    created_dirs.append(f"[DRY RUN] {str(directory)}")
        
        return created_dirs
    
    def get_method_path(self, target: str, method: str, version: str) -> Optional[Path]:
        """
        Derives the path to a method using the method paths report for the given target.

        Args:
            target: The type of target to derive the path for (e.g., 'mdx', 'json', 'openapi', 'rust').
            method: The canonical name of the method.
            version: The version of the method (e.g., 'v1', 'v2').

        Returns:
            The Path to the method's directory, or None if not found.
        """
        if target == "mdx":
            report_path = self.config.directories.mdx_method_paths_report
        elif target == "json":
            report_path = self.config.directories.mdx_json_example_method_paths_report
        elif target == "openapi":
            report_path = self.config.directories.mdx_openapi_method_paths_report
        elif target == "rust":
            report_path = self.config.directories.rust_methods_report
        else:
            get_logger(__name__).error(f"Invalid target type: {target}")
            return None
        try:
            with open(report_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            get_logger(__name__).error(f"Error reading MDX method paths report from {report_path}: {e}")
            return None
        
        method_paths = data.get("method_paths", {})
        if version not in method_paths:
            get_logger(__name__).warning(f"Version '{version}' not found in MDX method paths report.")
            return None
        path_str = method_paths.get(version, {}).get(method)
        if path_str:
            return Path(path_str)
        get_logger(__name__).warning(f"MDX Path not found for method '{method}' in version '{version}'.")
        return None
