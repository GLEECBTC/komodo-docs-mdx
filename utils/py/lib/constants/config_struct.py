#!/usr/bin/env python3
"""
Configuration Data Structures

Dataclass definitions for configuration and settings management
in the Komodo DeFi Framework documentation tools.
"""
import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .enums import ValidationLevel, VersionStatus, DeploymentEnvironment


# =============================================================================
# CONFIGURATION DOMAIN - Configuration and settings management
# =============================================================================

@dataclass
class CoinConfig:
    """Coin configuration data structure."""
    coin: str
    name: str
    protocol: Dict[str, Any]
    protocol_type: str
    parent_coin: Optional[str] = None
    contract_address: Optional[str] = None
    derivation_path: Optional[str] = None
    mature_confirmations: int = 0
    chain_id: Optional[int] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    electrum: Optional[List[Dict[str, Any]]] = None
    decimals: Optional[int] = None
    swap_contract_address: Optional[str] = None
    sign_message_prefix: Optional[str] = None
    required_confirmations: Optional[int] = None
    requires_notarization: bool = False
    is_testnet: bool = False
    
    @classmethod
    def from_config_dict(cls, coin_ticker: str, config: Dict[str, Any]) -> 'CoinConfig':
        """Create CoinConfig from configuration dictionary."""
        protocol = config.get("protocol", {})
        protocol_type = protocol.get("type", "Unknown")
        
        return cls(
            coin=coin_ticker,
            name=config.get("name", coin_ticker),
            protocol_type=protocol_type,
            parent_coin=config.get("parent_coin"),
            contract_address=config.get("contract_address"),
            derivation_path=config.get("derivation_path"),
            chain_id=config.get("chain_id"),
            nodes=config.get("nodes"),
            electrum=config.get("electrum"),
            decimals=config.get("decimals"),
            swap_contract_address=config.get("swap_contract_address"),
            sign_message_prefix=config.get("sign_message_prefix"),
            required_confirmations=config.get("required_confirmations"),
            is_testnet=config.get("is_testnet", False)
        )


@dataclass
class DirectoryConfig:
    """Enhanced configuration for directory paths with version support."""
    workspace_root: str  # The absolute path to the workspace root
    kdf_branch: Optional[str] = None
    mdx_branch: Optional[str] = None
    branched_reports_dir: Optional[Path] = None  # Will be set to Path in __post_init__

    # MDX documentation paths - these become Path objects after __post_init__
    mdx_v1: Union[str, Path] = "src/pages/komodo-defi-framework/api/legacy"
    mdx_v2: Union[str, Path] = "src/pages/komodo-defi-framework/api/v20"
    mdx_v2_dev: Union[str, Path] = "src/pages/komodo-defi-framework/api/v20-dev"
    mdx_common_structures: Union[str, Path] = "src/pages/komodo-defi-framework/api/common_structures"
    
    # OpenAPI specification paths - these become Path objects after __post_init__
    yaml_v1: Union[str, Path] = "openapi/paths/v1"
    yaml_v2: Union[str, Path] = "openapi/paths/v2"
    openapi_paths: Union[str, Path] = "openapi/paths"
    openapi_components: Union[str, Path] = "openapi/paths/components"
    openapi_schemas: Union[str, Path] = "openapi/paths/components/schemas"
    openapi_main: Union[str, Path] = "openapi/openapi.yaml"
    
    # Postman collection paths - these become Path objects after __post_init__
    postman_json_v1: Union[str, Path] = "postman/json/kdf/v1"
    postman_json_v2: Union[str, Path] = "postman/json/kdf/v2"
    postman_collections: Union[str, Path] = "postman/collections"
    postman_environments: Union[str, Path] = "postman/environments"
    
    # Docker and containerization paths - these become Path objects after __post_init__
    docker_dir: Union[str, Path] = "utils/docker"
    docker_dot_kdf_dir: Union[str, Path] = "utils/docker/kdf-config"

    # Data and cache directories - these become Path objects after __post_init__
    data_dir: Union[str, Path] = "utils/py/data"
    templates_dir: Union[str, Path] = "templates"
    reports_dir: Union[str, Path] = "reports"
    cache_dir: Union[str, Path] = "cache"
    kdf_repo_path: Union[str, Path] = "utils/docker/komodo-defi-framework"

    # Test parameters file (JSON) used across various scripts/tests
    test_params_json: Union[str, Path] = "utils/py/kdf_test_cases/test_params.json"

    # Reference files - these become Path objects after __post_init__
    category_mappings: Union[str, Path] = "utils/py/data/category_mappings.json"

    # Report filenames - these become Path objects after __post_init__
    rust_methods_report: Union[str, Path] = "kdf_rust_methods.json"
    mdx_methods_report: Union[str, Path] = "kdf_mdx_methods.json"
    mdx_method_paths_report: Union[str, Path] = "kdf_mdx_method_paths.json"
    mdx_json_example_methods_report: Union[str, Path] = "kdf_mdx_json_example_methods.json"
    mdx_json_example_method_paths_report: Union[str, Path] = "kdf_mdx_json_example_method_paths.json"
    mdx_openapi_methods_report: Union[str, Path] = "kdf_openapi_methods.json"
    mdx_openapi_method_paths_report: Union[str, Path] = "kdf_openapi_method_paths.json"
    unified_method_mapping_report: Union[str, Path] = "kdf_unified_method_map.json"
    kdf_gap_analysis_report: Union[str, Path] = "kdf_gap_analysis.json"
    v2_no_param_methods_report: Union[str, Path] = "v2_no_param_methods.json"
    kdf_error_responses_report: Union[str, Path] = "kdf_error_responses.json"

    def __post_init__(self):
        """Resolve all path strings to absolute Path objects."""
        self._resolve_paths()
        self._ensure_paths_exist()

    def _ensure_paths_exist(self):
        """Ensure all paths exist."""
        for _, value in self.__dict__.items():
            if isinstance(value, Path):
                if not value.exists():
                    if str(value).endswith(".json") or str(value).endswith(".yaml"):
                        continue
                    value.mkdir(parents=True, exist_ok=True)

    def _resolve_paths(self):
        """
        Converts all string paths in the configuration to absolute pathlib.Path objects.
        After this method runs, all path attributes are Path objects, not strings.
        """
        root = Path(self.workspace_root)
        
        # Resolve non-report paths first
        for name, value in self.__dict__.items():
            if (
                isinstance(value, str)
                and 'report' not in name  # skip individual report file names handled later
                and name not in {'workspace_root', 'kdf_branch', 'mdx_branch'}
            ):
                setattr(self, name, root / value)
                
        # Explicitly resolve top-level reports_dir (plural) which was skipped above
        if isinstance(self.reports_dir, str):
            self.reports_dir = root / self.reports_dir

        # Build reports base directory (include branch subfolder when set)
        reports_root_path = Path(self.reports_dir)
        if self.kdf_branch:
            reports_base_dir = reports_root_path / self.kdf_branch
        else:
            reports_base_dir = reports_root_path

        self.branched_reports_dir = reports_base_dir  # Update reports_dir to include branch
        if not self.branched_reports_dir.exists():
            self.branched_reports_dir.mkdir(parents=True, exist_ok=True)

        report_attributes = [
            "rust_methods_report", "mdx_methods_report", "mdx_method_paths_report",
            "mdx_json_example_methods_report", "mdx_json_example_method_paths_report",
            "mdx_openapi_methods_report", "mdx_openapi_method_paths_report",
            "unified_method_mapping_report", "kdf_gap_analysis_report",
            "v2_no_param_methods_report", "kdf_error_responses_report"
        ]

        for attr in report_attributes:
            original_path = getattr(self, attr)  # e.g., "reports/kdf_rust_methods.json"
            file_name = Path(original_path).name
            setattr(self, attr, reports_base_dir / file_name)

        # Manually resolve any remaining important paths
        self.category_mappings = root / self.category_mappings
        # Resolve test_params_json (handled here explicitly in case it was skipped)
        if isinstance(self.test_params_json, str):
            self.test_params_json = root / self.test_params_json

    def get_version_directories(self) -> Dict[str, Dict[str, Union[str, Path]]]:
        """Get directories organized by version and type."""
        return {
            "v1": {
                "yaml": self.yaml_v1,
                "json": self.postman_json_v1,
                "mdx": self.mdx_v1
            },
            "v2": {
                "yaml": self.yaml_v2,
                "json": self.postman_json_v2,
                "mdx": self.mdx_v2
            },
            "v2-dev": {
                "yaml": self.yaml_v2,  # v2-dev uses same YAML as v2
                "json": self.postman_json_v2,  # v2-dev uses same JSON as v2
                "mdx": self.mdx_v2_dev
            }
        }

    def get_relative_path(self, absolute_path: str) -> str:
        """
        Convert an absolute path to a relative path from the workspace root.
        
        Args:
            absolute_path: The full path to convert.
            
        Returns:
            A relative path string.
        """
        path = Path(absolute_path)
        if not path.is_absolute():
            return str(absolute_path)
        
        try:
            return str(path.relative_to(self.workspace_root))
        except ValueError:
            return str(absolute_path)


@dataclass
class LoggingConfig:
    """Enhanced configuration for logging and output."""
    verbose: bool = True
    quiet: bool = False
    log_file: Optional[str] = None
    progress_indicators: bool = True
    emoji_output: bool = True
    
    # Log levels and formatting
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Output control
    show_warnings: bool = True
    show_debug: bool = False
    colored_output: bool = True


@dataclass
class OpenAPIConfig:
    """Configuration for OpenAPI generation."""
    userpass: str = "RPC_UserP@SSW0RD"
    mmrpc_version: str = "2.0"
    openapi_version: str = "3.0.3"
    common_structures_dir: str = "src/pages/komodo-defi-framework/api/common_structures"
    enums_doc_path: str = "src/pages/komodo-defi-framework/api/common_structures/enums/index.mdx"
    output_path: str = "openapi/paths"
    tracking_data_dir: str = "utils/py/data"


@dataclass
class ProcessingConfig:
    """Enhanced configuration for processing operations."""
    batch_size: int = 50
    parallel_processing: bool = True
    max_workers: int = 4
    continue_on_error: bool = False
    validate_every_nth_block: int = 10
    required_confirmations: int = 3
    
    # File operation settings
    backup_on_write: bool = False
    cleanup_temp_files: bool = True
    max_file_age_hours: int = 24
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_cache_size_mb: int = 100


@dataclass
class ValidationConfig:
    """Enhanced configuration for validation rules."""
    strict_method_validation: bool = True
    require_examples: bool = False
    validate_json_syntax: bool = True
    check_duplicates: bool = True
    minimum_method_name_length: int = 2
    
    # Validation levels
    default_validation_level: ValidationLevel = ValidationLevel.NORMAL
    file_validation_level: ValidationLevel = ValidationLevel.NORMAL
    schema_validation_enabled: bool = True
    
    # Custom validation rules
    custom_validation_rules: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_validation_rules is None:
            self.custom_validation_rules = {}


@dataclass
class VersionConfig:
    """Configuration for a specific API version."""
    name: str
    status: VersionStatus
    aliases: List[str] = field(default_factory=list)
    migration_target: Optional[str] = None
    
    @classmethod
    def create_version_configs(cls) -> Dict[str, 'VersionConfig']:
        """Create default version configurations."""
        return {
            "v1": cls(
                name="v1",
                status=VersionStatus.LEGACY,
                aliases=["legacy", "v1.0", "deprecated"],
                migration_target=None
            ),
            "v2": cls(
                name="v2",
                status=VersionStatus.ACTIVE,
                aliases=["v20", "v2.0", "current", "stable"],
                migration_target=None
            ),
            "v2-dev": cls(
                name="v2-dev",
                status=VersionStatus.DEVELOPMENT,
                aliases=["v20-dev", "dev", "development", "beta"],
                migration_target="v2"
            )
        }


@dataclass
class VersionMappingConfig:
    """
    Centralized version mapping configuration to eliminate duplication across the codebase.
    
    This class provides a single source of truth for:
    - Version aliases and canonical names
    - Directory mappings for different file types
    - Postman collection version mappings
    - OpenAPI source version mappings
    - Migration paths between versions
    """
    
    # Core version definitions
    canonical_versions: Dict[str, str] = field(default_factory=lambda: {
        # Canonical mappings - all aliases point to these canonical versions
        'v1': 'v1',
        'legacy': 'v1',
        'deprecated': 'v1',
        'v1.0': 'v1',
        
        'v2': 'v2',
        'v20': 'v2',
        'v2.0': 'v2',
        'current': 'v2',
        'stable': 'v2',
        
        'v2-dev': 'v2-dev',
        'v20-dev': 'v2-dev',
        'dev': 'v2-dev',
        'development': 'v2-dev',
        'beta': 'v2-dev'
    })
    
    # Postman collection version mappings
    postman_version_mapping: Dict[str, str] = field(default_factory=lambda: {
        'v1': 'v1',
        'v2': 'v2',
        'v20': 'v2',
        'v2-dev': 'v2',  # v2-dev methods use v2 Postman data
        'v20-dev': 'v2'  # v20-dev methods use v2 Postman data
    })
    
    # OpenAPI source directory mappings
    openapi_source_mapping: Dict[str, List[str]] = field(default_factory=lambda: {
        'v1': ['legacy'],
        'v2': ['v20', 'v20-dev'],  # v2 processes both v20 and v20-dev
        'v2-dev': ['v20-dev'],
        'v20-dev': ['v20-dev']
    })
    
    # Documentation directory mappings
    doc_path_mapping: Dict[str, str] = field(default_factory=lambda: {
        'v1': 'legacy',
        'v2': 'v20',
        'v2-dev': 'v20-dev',
        'v20': 'v20',
        'v20-dev': 'v20-dev'
    })
    
    # Version status definitions
    version_status: Dict[str, VersionStatus] = field(default_factory=lambda: {
        'v1': VersionStatus.LEGACY,
        'v2': VersionStatus.ACTIVE,
        'v2-dev': VersionStatus.DEVELOPMENT
    })
    
    # Migration targets
    migration_targets: Dict[str, Optional[str]] = field(default_factory=lambda: {
        'v1': None,  # No migration target for legacy
        'v2': None,  # Current stable version
        'v2-dev': 'v2'  # Development migrates to stable
    })
    
    def get_canonical_version(self, version: str) -> str:
        """Get the canonical version name for any version alias."""
        return self.canonical_versions.get(version, version)
    
    def get_postman_version(self, version: str) -> str:
        """Get the Postman collection version for a given version."""
        canonical = self.get_canonical_version(version)
        return self.postman_version_mapping.get(canonical, canonical)
    
    def get_openapi_sources(self, version: str) -> List[str]:
        """Get the source directories for OpenAPI generation for a given version."""
        canonical = self.get_canonical_version(version)
        return self.openapi_source_mapping.get(canonical, [canonical])
    
    def get_doc_path(self, version: str) -> str:
        """Get the documentation path for a given version."""
        canonical = self.get_canonical_version(version)
        return self.doc_path_mapping.get(canonical, canonical)
    
    def get_version_status(self, version: str) -> VersionStatus:
        """Get the status for a given version."""
        canonical = self.get_canonical_version(version)
        return self.version_status.get(canonical, VersionStatus.UNKNOWN)
    
    def get_migration_target(self, version: str) -> Optional[str]:
        """Get the migration target for a given version."""
        canonical = self.get_canonical_version(version)
        return self.migration_targets.get(canonical)
    
    def is_deprecated(self, version: str) -> bool:
        """Check if a version is deprecated."""
        return self.get_version_status(version) == VersionStatus.LEGACY
    
    def get_all_canonical_versions(self) -> List[str]:
        """Get all canonical version names."""
        return list(set(self.canonical_versions.values()))
    
    def get_aliases_for_version(self, canonical_version: str) -> List[str]:
        """Get all aliases for a canonical version."""
        return [alias for alias, canon in self.canonical_versions.items() 
                if canon == canonical_version]


@dataclass
class NodeConfig:
    """Represents the configuration for a single test node."""
    name: str
    port: int
    api_url: str
    userpass: str
    passphrase: str
    hd_mode: bool = False
    wasm_mode: bool = False
    


@dataclass
class EnhancedKomodoConfig:
    """Enhanced configuration with flexible directory management and version handling."""
    
    # Core configuration
    directories: DirectoryConfig = field(init=False)
    versions: Dict[str, VersionConfig] = field(default_factory=VersionConfig.create_version_configs)
    version_mapping: VersionMappingConfig = field(default_factory=VersionMappingConfig)
    openapi: OpenAPIConfig = field(default_factory=OpenAPIConfig)
    nodes: List[NodeConfig] = field(default_factory=lambda: [
        # Native (non-HD) node
        NodeConfig(
            name="kdf_native_nonhd",
            port=8778,
            api_url="http://127.0.0.1:8778",
            hd_mode=False,
            wasm_mode=False,
            userpass="RPC_UserP@SSW0RD",
            passphrase="movie near museum glare gossip clerk adapt chair inch child erupt verify"
        ),
        # Native HD node
        NodeConfig(
            name="kdf_native_hd",
            port=8779,
            api_url="http://127.0.0.1:8779",
            hd_mode=True,
            wasm_mode=False,
            userpass="RPC_UserP@SSW0RD",
            passphrase="clever measure tired have excuse lava box job forest labor kitchen device"
        ),
        # WASM HD node
        NodeConfig(
            name="kdf_wasm_hd",
            port=8780,
            api_url="http://127.0.0.1:8780",
            hd_mode=True,
            wasm_mode=True,
            userpass="RPC_UserP@SSW0RD",
            passphrase="evil game choice book glad motor old family slender famous black cancel"
        ),
        # WASM non-HD node
        NodeConfig(
            name="kdf_wasm_nonhd",
            port=8781,
            api_url="http://127.0.0.1:8781",
            hd_mode=False,
            wasm_mode=True,
            userpass="RPC_UserP@SSW0RD",
            passphrase="super sick hybrid myself useful bulb horror slice silk royal guess machine"
        ),
    ])
    
    # Environment and deployment settings
    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
    workspace_root: Optional[str] = None
    kdf_branch: Optional[str] = None
    mdx_branch: Optional[str] = None
    
    # Feature flags
    enable_async_processing: bool = True
    enable_postman_integration: bool = True
    enable_openapi_generation: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    
    def __post_init__(self):
        """Post-initialization setup."""
        self._resolve_workspace_root()
        self._get_git_branches()
        self.directories = DirectoryConfig(
            workspace_root=self.workspace_root,
            kdf_branch=self.kdf_branch,
            mdx_branch=self.mdx_branch
        )
        self._setup_logging()
    
    def _get_git_branches(self):
        """Get git branches for MDX and KDF repos."""
        if self.workspace_root:
            self.mdx_branch = get_current_git_branch(self.workspace_root)
            kdf_repo_path = Path(self.workspace_root) / "utils" / "docker" / "komodo-defi-framework"
            self.kdf_branch = get_current_git_branch(str(kdf_repo_path))
            if not self.kdf_branch or self.kdf_branch == 'unknown':
                self.kdf_branch = "dev"  # Fallback
        else:
            self.mdx_branch = "dev"
            self.kdf_branch = "dev"

    def _setup_logging(self):
        """Configure logging based on settings."""
        import logging
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format
        )
    
    def _resolve_workspace_root(self):
        """Resolve workspace root if not explicitly set."""
        if self.workspace_root is None:
            # Try to find workspace root by looking for characteristic files
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                if (parent / "src" / "pages").exists() and (parent / "utils").exists():
                    self.workspace_root = str(parent)
                    break
            else:
                self.workspace_root = str(current)
    
    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to workspace root."""
        import os
        if os.path.isabs(path):
            return path
        return os.path.join(self.workspace_root, path)

    def get_directory_for_version_and_type(self, version: str, dir_type: str) -> str:
        """
        Get a specific directory path for a given version and type.

        Args:
            version: The version alias (e.g., 'v2', 'v20-dev').
            dir_type: The type of directory ('mdx', 'yaml', 'json').

        Returns:
            The absolute path as a string.

        Raises:
            ValueError: If the mapping for the version or type does not exist.
        """
        version_dirs = self.directories.get_version_directories()
        canonical_version = self.get_canonical_version(version)

        if canonical_version in version_dirs:
            if dir_type in version_dirs[canonical_version]:
                return str(version_dirs[canonical_version][dir_type])
            raise ValueError(f"Directory type '{dir_type}' not found for version '{version}' (canonical: '{canonical_version}').")
        raise ValueError(f"Version '{version}' (canonical: '{canonical_version}') not found in directory configuration.")

    # Version mapping convenience methods
    def get_canonical_version(self, version: str) -> str:
        """Get canonical version name."""
        return self.version_mapping.get_canonical_version(version)
    
    def get_postman_version(self, version: str) -> str:
        """Get Postman collection version."""
        return self.version_mapping.get_postman_version(version)
    
    def get_openapi_sources(self, version: str) -> List[str]:
        """Get OpenAPI source directories."""
        return self.version_mapping.get_openapi_sources(version)
    
    def get_doc_path(self, version: str) -> str:
        """Get documentation path."""
        return self.version_mapping.get_doc_path(version)
    
    def is_version_deprecated(self, version: str) -> bool:
        """Check if version is deprecated."""
        return self.version_mapping.is_deprecated(version)
    
    def get_version_status(self, version: str) -> VersionStatus:
        """Get version status."""
        return self.version_mapping.get_version_status(version)
    
    def get_supported_versions(self, include_deprecated: bool = False) -> List[str]:
        """Get list of supported versions."""
        versions = self.version_mapping.get_all_canonical_versions()
        if not include_deprecated:
            versions = [v for v in versions if not self.is_version_deprecated(v)]
        return sorted(versions)


def get_current_git_branch(repo_path: str) -> str:
    """Gets the current git branch for a given repository path."""
    try:
        repo_path_str = str(repo_path)
        if not os.path.isdir(os.path.join(repo_path_str, '.git')):
            # self.logger.warning(f"No .git directory found in {repo_path_str}, cannot determine branch.")
            return "unknown"
        
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path_str,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # self.logger.error(f"Could not determine git branch for {repo_path}: {e}")
        return "unknown"

