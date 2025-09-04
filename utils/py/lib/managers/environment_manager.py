#!/usr/bin/env python3
"""
Environment Manager for KDF Methods

Handles environment-specific requirements for KDF API methods,
including hardware requirements, protocol preferences, and example filtering.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any


class EnvironmentManager:
    """Manages environment-specific requirements for KDF methods."""
    
    def __init__(self, kdf_methods_path: Optional[str] = None):
        """Initialize the environment manager.
        
        Args:
            kdf_methods_path: Path to kdf_methods.json file. If None, uses default path.
        """
        if kdf_methods_path is None:
            # Default path relative to the script location
            # Navigate from utils/py/lib/managers/ to workspace root
            # __file__ -> utils/py/lib/managers/environment_manager.py
            # .parent -> utils/py/lib/managers/
            # .parent -> utils/py/lib/
            # .parent -> utils/py/
            # .parent -> utils/
            # .parent -> workspace root
            script_dir = Path(__file__).parent.parent.parent.parent.parent
            kdf_methods_path = script_dir / "src" / "data" / "kdf_methods.json"
        
        self.kdf_methods_path = Path(kdf_methods_path)
        self.methods_data = self._load_methods_data()
    
    def _load_methods_data(self) -> Dict[str, Any]:
        """Load and parse the KDF methods data."""
        try:
            with open(self.kdf_methods_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"KDF methods file not found: {self.kdf_methods_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in KDF methods file: {e}")
    
    def is_deprecated(self, method: str) -> bool:
        """Check if a method is marked as deprecated.
        
        Args:
            method: The KDF method name
            
        Returns:
            True if the method is deprecated, False otherwise
        """
        if method not in self.methods_data:
            return False
        
        method_data = self.methods_data[method]
        return method_data.get('deprecated', False)
    
    def get_prerequisite_methods(self, method: str) -> List[str]:
        """Get list of prerequisite methods for a method.
        
        Args:
            method: The KDF method name
            
        Returns:
            List of prerequisite method names
        """
        if method not in self.methods_data:
            return []
        
        method_data = self.methods_data[method]
        requirements = method_data.get('requirements', {})
        return requirements.get('prerequisite_methods', [])
    
    def get_supported_environments(self, method: str) -> List[str]:
        """Get list of environments where the method is supported.
        
        Args:
            method: The KDF method name (e.g., 'task::enable_utxo::init')
            
        Returns:
            List of supported environment names (e.g., ['native', 'wasm'])
        """
        if method not in self.methods_data:
            return []
        
        requirements = self.methods_data[method].get('requirements', {})
        return requirements.get('environments', [])
    
    def is_environment_supported(self, method: str, environment: str) -> bool:
        """Check if a method is supported in a specific environment.
        
        Args:
            method: The KDF method name
            environment: Environment name ('native', 'wasm', etc.)
            
        Returns:
            True if the method supports the environment
        """
        return environment in self.get_supported_environments(method)
    
    def get_hardware_requirements(self, method: str) -> List[str]:
        """Get hardware requirements for a method.
        
        Args:
            method: The KDF method name
            
        Returns:
            List of required hardware types (e.g., ['trezor'])
        """
        if method not in self.methods_data:
            return []
        
        requirements = self.methods_data[method].get('requirements', {})
        return requirements.get('hardware', [])
    
    def requires_hardware(self, method: str, hardware_type: str = None) -> bool:
        """Check if a method requires specific hardware.
        
        Args:
            method: The KDF method name
            hardware_type: Specific hardware type to check (e.g., 'trezor')
                          If None, checks if any hardware is required
            
        Returns:
            True if the method requires the specified hardware (or any hardware)
        """
        hardware_reqs = self.get_hardware_requirements(method)
        
        if hardware_type is None:
            return len(hardware_reqs) > 0
        
        return hardware_type in hardware_reqs
    
    def get_protocol_preferences(self, method: str, environment: str) -> Dict[str, List[str]]:
        """Get protocol preferences for a method in a specific environment.
        
        Args:
            method: The KDF method name
            environment: Environment name
            
        Returns:
            Dictionary mapping protocol types to preferred options
            Example: {'electrum': ['WSS'], 'websocket': ['wss']}
        """
        if method not in self.methods_data:
            return {}
        
        requirements = self.methods_data[method].get('requirements', {})
        protocols = requirements.get('protocols', {})
        
        result = {}
        for protocol_type, env_prefs in protocols.items():
            if environment in env_prefs:
                result[protocol_type] = env_prefs[environment]
        
        return result
    
    def get_supported_wallet_types(self, method: str) -> List[str]:
        """Get list of wallet types where the method is supported.
        
        Args:
            method: The KDF method name (e.g., 'task::enable_utxo::init')
            
        Returns:
            List of supported wallet types (e.g., ['hd', 'iguana'])
        """
        if method not in self.methods_data:
            return []
        
        requirements = self.methods_data[method].get('requirements', {})
        return requirements.get('wallet_types', [])
    
    def is_wallet_type_supported(self, method: str, wallet_type: str) -> bool:
        """Check if a method is supported with a specific wallet type.
        
        Args:
            method: The KDF method name
            wallet_type: Wallet type ('hd', 'iguana')
            
        Returns:
            True if the method supports the wallet type
        """
        return wallet_type in self.get_supported_wallet_types(method)
    
    def get_conditional_params(self, method: str, wallet_type: str = None) -> List[str]:
        """Get parameters that are conditional based on wallet type.
        
        Args:
            method: The KDF method name
            wallet_type: Wallet type to get conditional params for
            
        Returns:
            List of parameter names that apply to the wallet type
        """
        if method not in self.methods_data:
            return []
        
        requirements = self.methods_data[method].get('requirements', {})
        conditional_params = requirements.get('conditional_params', {})
        
        if wallet_type == 'hd':
            return conditional_params.get('hd_only', [])
        elif wallet_type == 'iguana':
            return conditional_params.get('non_hd_only', [])
        else:
            # Return all conditional params if no specific type requested
            all_params = []
            all_params.extend(conditional_params.get('hd_only', []))
            all_params.extend(conditional_params.get('non_hd_only', []))
            return all_params

    def get_filtered_examples(self, method: str, environment: str = None, 
                            hardware: str = None, wallet_type: str = None) -> Dict[str, str]:
        """Get examples filtered by environment, hardware, and wallet type requirements.
        
        Args:
            method: The KDF method name
            environment: Filter by environment (optional)
            hardware: Filter by hardware requirement (optional)
            wallet_type: Filter by wallet type ('hd', 'iguana') (optional)
            
        Returns:
            Dictionary of example_key -> description pairs that match criteria
        """
        if method not in self.methods_data:
            return {}
        
        method_data = self.methods_data[method]
        all_examples = method_data.get('examples', {})
        
        # If no filtering requested, return all examples
        if environment is None and hardware is None and wallet_type is None:
            return all_examples
        
        # Check method-level requirements
        method_requirements = method_data.get('requirements', {})
        
        # Filter by environment
        if environment is not None:
            supported_envs = method_requirements.get('environments', [])
            if environment not in supported_envs:
                return {}  # Method not supported in this environment
        
        # Filter by wallet type
        if wallet_type is not None:
            supported_wallet_types = method_requirements.get('wallet_types', [])
            if wallet_type not in supported_wallet_types:
                return {}  # Method not supported with this wallet type
        
        # Filter by hardware
        if hardware is not None:
            required_hardware = method_requirements.get('hardware', [])
            if hardware not in required_hardware and len(required_hardware) > 0:
                return {}  # Method doesn't require this hardware
        
        # Check example-specific requirements
        example_requirements = method_requirements.get('example_requirements', {})
        filtered_examples = {}
        
        for example_key, description in all_examples.items():
            example_reqs = example_requirements.get(example_key, {})
            
            # Check hardware requirement for this specific example
            if hardware is not None:
                example_hardware = example_reqs.get('hardware', [])
                if len(example_hardware) > 0 and hardware not in example_hardware:
                    continue  # This example requires different hardware
            
            # Apply "x_only" pattern detection
            if self._matches_pattern_requirements(example_key, environment, hardware, wallet_type):
                filtered_examples[example_key] = description
        
        return filtered_examples
    
    def _matches_pattern_requirements(self, example_key: str, environment: str = None, 
                                    hardware: str = None, wallet_type: str = None) -> bool:
        """Check if an example matches pattern-based requirements (x_only patterns).
        
        Args:
            example_key: The example identifier
            environment: Target environment
            hardware: Target hardware
            wallet_type: Target wallet type
            
        Returns:
            True if the example matches the requirements
        """
        example_lower = example_key.lower()
        
        # Check for hardware-specific patterns
        if 'trezor' in example_lower:
            return hardware == 'trezor' or hardware is None
        
        # Check for environment-specific patterns
        if 'native' in example_lower:
            return environment == 'native' or environment is None
        
        if 'wasm' in example_lower:
            return environment == 'wasm' or environment is None
        
        # Check for wallet type patterns
        if 'hd' in example_lower and wallet_type is not None:
            return wallet_type == 'hd'
        
        if 'iguana' in example_lower and wallet_type is not None:
            return wallet_type == 'iguana'
        
        # Check for parameter-specific patterns (pin/passphrase = trezor)
        if any(pattern in example_lower for pattern in ['pin', 'passphrase']):
            return hardware == 'trezor' or hardware is None
        
        # Check for HD-specific parameter patterns
        if any(pattern in example_lower for pattern in ['gap_limit', 'scan_policy', 'min_addresses', 'path_to_address']):
            return wallet_type == 'hd' or wallet_type is None
        
        # If no specific patterns found, include the example
        return True
    
    def get_environment_specific_postman_configs(self) -> Dict[str, Dict]:
        """Generate environment-specific Postman collection configurations.
        
        Returns:
            Dictionary mapping environment names to their configurations
        """
        configs = {
            'native_hd': {
                'name': 'KDF API (Native + HD)',
                'description': 'Komodo DeFi Framework API for Native environments with HD wallets',
                'preferred_protocols': {
                    'electrum': ['TCP', 'SSL'],
                    'websocket': ['ws', 'wss']
                },
                'base_url': 'http://kdf-native-hd:8779',
                'notes': 'Native environment with HD wallet support. Includes HD-specific parameters.',
                'wallet_type': 'hd'
            },
            'native_iguana': {
                'name': 'KDF API (Native + Iguana)',
                'description': 'Komodo DeFi Framework API for Native environments with Iguana wallets',
                'preferred_protocols': {
                    'electrum': ['TCP', 'SSL'],
                    'websocket': ['ws', 'wss']
                },
                'base_url': 'http://kdf-native-nonhd:8778',
                'notes': 'Native environment with legacy Iguana wallet support.',
                'wallet_type': 'iguana'
            },
            'wasm_hd': {
                'name': 'KDF API (WASM + HD)',
                'description': 'Komodo DeFi Framework API for WASM environments with HD wallets',
                'preferred_protocols': {
                    'electrum': ['WSS'],
                    'websocket': ['wss']
                },
                'base_url': 'http://kdf-native-hd:8779',
                'notes': 'WASM environment with HD wallet support. WSS protocols only.',
                'wallet_type': 'hd'
            },
            'wasm_iguana': {
                'name': 'KDF API (WASM + Iguana)',
                'description': 'Komodo DeFi Framework API for WASM environments with Iguana wallets',
                'preferred_protocols': {
                    'electrum': ['WSS'],
                    'websocket': ['wss']
                },
                'base_url': 'http://kdf-native-nonhd:8778',
                'notes': 'WASM environment with legacy Iguana wallet support. WSS protocols only.',
                'wallet_type': 'iguana'
            },
            'trezor_native_hd': {
                'name': 'KDF API (Native + Trezor + HD)',
                'description': 'Komodo DeFi Framework API for Native with Trezor hardware wallet and HD support',
                'preferred_protocols': {
                    'electrum': ['TCP', 'SSL'],
                    'websocket': ['ws', 'wss']
                },
                'base_url': 'http://kdf-native-hd:8779',
                'notes': 'Native environment with Trezor hardware wallet and HD wallet support',
                'hardware': ['trezor'],
                'wallet_type': 'hd'
            },
            'trezor_wasm_hd': {
                'name': 'KDF API (WASM + Trezor + HD)',
                'description': 'Komodo DeFi Framework API for WASM with Trezor hardware wallet and HD support',
                'preferred_protocols': {
                    'electrum': ['WSS'],
                    'websocket': ['wss']
                },
                'base_url': 'http://kdf-native-hd:8779',
                'notes': 'WASM environment with Trezor hardware wallet and HD wallet support',
                'hardware': ['trezor'],
                'wallet_type': 'hd'
            }
        }
        
        return configs
    
    def validate_method_compatibility(self, method: str, environment: str, 
                                    hardware: str = None, wallet_type: str = None) -> Tuple[bool, List[str]]:
        """Validate if a method is compatible with given environment, hardware, and wallet type.
        
        Args:
            method: The KDF method name
            environment: Target environment
            hardware: Target hardware (optional)
            wallet_type: Target wallet type (optional)
            
        Returns:
            Tuple of (is_compatible, list_of_issues)
        """
        issues = []
        
        if method not in self.methods_data:
            return False, [f"Method '{method}' not found in registry"]
        
        # Check environment compatibility
        if not self.is_environment_supported(method, environment):
            supported_envs = self.get_supported_environments(method)
            issues.append(f"Method not supported in '{environment}' environment. "
                         f"Supported: {supported_envs}")
        
        # Check wallet type compatibility
        if wallet_type is not None and not self.is_wallet_type_supported(method, wallet_type):
            supported_wallet_types = self.get_supported_wallet_types(method)
            issues.append(f"Method not supported with '{wallet_type}' wallet type. "
                         f"Supported: {supported_wallet_types}")
        
        # Check hardware requirements
        required_hardware = self.get_hardware_requirements(method)
        if len(required_hardware) > 0:
            if hardware is None:
                issues.append(f"Method requires hardware: {required_hardware}")
            elif hardware not in required_hardware:
                issues.append(f"Method requires different hardware. "
                             f"Required: {required_hardware}, provided: {hardware}")
        
        return len(issues) == 0, issues
    
    def generate_compatibility_report(self) -> Dict[str, Any]:
        """Generate a comprehensive compatibility report for all methods.
        
        Returns:
            Dictionary containing compatibility analysis for all methods
        """
        report = {
            'methods_by_environment': {},
            'hardware_only_methods': [],
            'environment_restrictions': {},
            'protocol_preferences': {}
        }
        
        # Analyze each method (excluding deprecated ones)
        for method_name, method_data in self.methods_data.items():
            # Skip deprecated methods
            if method_data.get('deprecated', False):
                continue
                
            requirements = method_data.get('requirements', {})
            environments = requirements.get('environments', [])
            hardware = requirements.get('hardware', [])
            protocols = requirements.get('protocols', {})
            
            # Group methods by environment
            for env in environments:
                if env not in report['methods_by_environment']:
                    report['methods_by_environment'][env] = []
                report['methods_by_environment'][env].append(method_name)
            
            # Track hardware-only methods
            if len(hardware) > 0:
                report['hardware_only_methods'].append({
                    'method': method_name,
                    'hardware': hardware,
                    'environments': environments
                })
            
            # Track environment restrictions
            if len(environments) < 2:  # Methods that don't support both native and wasm
                report['environment_restrictions'][method_name] = environments
            
            # Track protocol preferences
            if protocols:
                report['protocol_preferences'][method_name] = protocols
        
        return report


if __name__ == "__main__":
    # Example usage and testing
    env_manager = EnvironmentManager()
    
    print("=== Environment Manager Test ===")
    
    # Test method compatibility
    method = "task::enable_utxo::user_action"
    print(f"\nTesting method: {method}")
    print(f"Supported environments: {env_manager.get_supported_environments(method)}")
    print(f"Supported wallet types: {env_manager.get_supported_wallet_types(method)}")
    print(f"Hardware requirements: {env_manager.get_hardware_requirements(method)}")
    
    # Test HD-specific parameters
    print(f"\nHD-only params (task::enable_utxo::init): {env_manager.get_conditional_params('task::enable_utxo::init', 'hd')}")
    print(f"Non-HD params (task::enable_eth::init): {env_manager.get_conditional_params('task::enable_eth::init', 'iguana')}")
    
    # Test filtering
    print(f"\nExamples (no filter): {env_manager.get_filtered_examples(method)}")
    print(f"Examples (trezor hardware): {env_manager.get_filtered_examples(method, hardware='trezor')}")
    print(f"Examples (HD wallet): {env_manager.get_filtered_examples(method, wallet_type='hd')}")
    
    # Test protocol preferences
    print(f"\nProtocol preferences (native): {env_manager.get_protocol_preferences('task::enable_utxo::init', 'native')}")
    print(f"Protocol preferences (wasm): {env_manager.get_protocol_preferences('task::enable_utxo::init', 'wasm')}")
    
    # Test compatibility validation
    print(f"\n=== Compatibility Tests ===")
    is_valid, issues = env_manager.validate_method_compatibility('task::enable_z_coin::init', 'wasm', wallet_type='hd')
    print(f"Z-coin in WASM with HD: {is_valid} ({issues})")
    
    is_valid, issues = env_manager.validate_method_compatibility('task::enable_utxo::init', 'native', wallet_type='hd')
    print(f"UTXO in Native with HD: {is_valid} ({issues})")
    
    # Generate compatibility report
    print(f"\n=== Compatibility Report ===")
    report = env_manager.generate_compatibility_report()
    print(f"Hardware-only methods: {len(report['hardware_only_methods'])}")
    print(f"Environment configs available: {len(env_manager.get_environment_specific_postman_configs())}")
