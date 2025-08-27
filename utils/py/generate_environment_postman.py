#!/usr/bin/env python3
"""
Environment-Specific Postman Collection Generator

Generates separate Postman collections for different KDF environments:
- Native environment (supports TCP, SSL, WebSocket)
- WASM environment (WSS only)
- Hardware wallet variants (Trezor-specific collections)

Addresses the issue where electrum servers need different protocols
for different environments (SSL for native, WSS for WASM).
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
from datetime import datetime

# Add the lib directory to the path
sys.path.append(str(Path(__file__).parent / "lib"))

from managers.environment_manager import EnvironmentManager


class EnvironmentPostmanGenerator:
    """Generates environment-specific Postman collections."""
    
    def __init__(self, workspace_root: Optional[str] = None):
        """Initialize the generator.
        
        Args:
            workspace_root: Path to the workspace root. If None, auto-detects.
        """
        if workspace_root is None:
            # Navigate from utils/py/generate_environment_postman.py to workspace root
            # Current working directory should be the workspace root
            workspace_root = Path.cwd()
        
        self.workspace_root = Path(workspace_root)
        self.env_manager = EnvironmentManager()
        
        # Paths
        self.requests_dir = self.workspace_root / "src" / "data" / "requests" / "kdf"
        self.output_dir = self.workspace_root / "postman" / "generated" / "environments"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_request_data(self, version: str = "v2") -> Dict[str, Any]:
        """Load request data from JSON files.
        
        Args:
            version: API version ('v2' or 'legacy')
            
        Returns:
            Dictionary containing all request data
        """
        request_file = self.requests_dir / version / "coin_activation.json"
        
        if not request_file.exists():
            raise FileNotFoundError(f"Request file not found: {request_file}")
        
        with open(request_file, 'r') as f:
            return json.load(f)
    
    def filter_protocols_for_environment(self, request_data: Dict[str, Any], 
                                      environment: str) -> Dict[str, Any]:
        """Filter and update protocol configurations for specific environment.
        
        Args:
            request_data: Original request data
            environment: Target environment ('native_hd', 'wasm_iguana', etc.)
            
        Returns:
            Modified request data with environment-appropriate protocols
        """
        filtered_data = json.loads(json.dumps(request_data))  # Deep copy
        
        # Parse environment components
        env_parts = environment.split('_')
        base_env = env_parts[0]  # native, wasm
        wallet_type = env_parts[1] if len(env_parts) > 1 and env_parts[1] in ['hd', 'iguana'] else None
        
        for request_key, request_body in filtered_data.items():
            if not isinstance(request_body, dict):
                continue
            
            params = request_body.get('params', {})
            method = request_body.get('method', '')
            
            # Handle electrum servers
            self._update_electrum_servers(params, base_env)
            
            # Handle WebSocket URLs
            self._update_websocket_urls(params, base_env)
            
            # Handle nodes for ETH/Tendermint
            self._update_node_urls(params, base_env)
            
            # Handle wallet type specific parameters
            self._update_wallet_type_params(params, method, wallet_type)
        
        return filtered_data
    
    def _update_electrum_servers(self, params: Dict[str, Any], environment: str):
        """Update electrum server configurations for environment."""
        # Handle nested electrum servers (UTXO coins)
        if 'mode' in params and 'rpc_data' in params['mode']:
            rpc_data = params['mode']['rpc_data']
            if 'servers' in rpc_data:
                rpc_data['servers'] = self._filter_electrum_servers(
                    rpc_data['servers'], environment
                )
        
        # Handle direct electrum servers (Z-coins)
        if 'electrum_servers' in params:
            params['electrum_servers'] = self._filter_electrum_servers(
                params['electrum_servers'], environment
            )
    
    def _filter_electrum_servers(self, servers: List[Dict], environment: str) -> List[Dict]:
        """Filter electrum servers based on environment protocol preferences."""
        if environment == 'wasm':
            # WASM only supports WSS
            return [s for s in servers if s.get('protocol') == 'WSS']
        elif environment == 'native':
            # Native prefers TCP and SSL, but can use WSS
            preferred_order = ['TCP', 'SSL', 'WSS']
            sorted_servers = []
            for protocol in preferred_order:
                sorted_servers.extend([s for s in servers if s.get('protocol') == protocol])
            return sorted_servers[:3]  # Limit to 3 servers
        else:
            return servers
    
    def _update_websocket_urls(self, params: Dict[str, Any], environment: str):
        """Update WebSocket URLs for environment."""
        if environment == 'wasm':
            # Ensure all WebSocket URLs use WSS
            for key in ['nodes', 'ws_url']:
                if key in params:
                    if key == 'nodes' and isinstance(params[key], list):
                        for node in params[key]:
                            if 'ws_url' in node and node['ws_url'].startswith('ws://'):
                                # Convert ws:// to wss:// for WASM
                                node['ws_url'] = node['ws_url'].replace('ws://', 'wss://')
    
    def _update_node_urls(self, params: Dict[str, Any], environment: str):
        """Update node URLs for environment preferences."""
        if 'nodes' in params and isinstance(params['nodes'], list):
            for node in params['nodes']:
                if environment == 'wasm':
                    # Prefer WSS for WASM
                    if 'ws_url' in node and not node['ws_url'].startswith('wss://'):
                        # Try to convert to secure WebSocket
                        if node['ws_url'].startswith('ws://'):
                            node['ws_url'] = node['ws_url'].replace('ws://', 'wss://')
    
    def _update_wallet_type_params(self, params: Dict[str, Any], method: str, wallet_type: str):
        """Update parameters based on wallet type requirements."""
        if wallet_type is None:
            return
        
        # Get conditional parameters for this method and wallet type
        conditional_params = self.env_manager.get_conditional_params(method, wallet_type)
        
        if wallet_type == 'iguana':
            # Remove HD-only parameters for Iguana wallet
            hd_only_params = self.env_manager.get_conditional_params(method, 'hd')
            for param in hd_only_params:
                if param in params:
                    del params[param]
                    
        elif wallet_type == 'hd':
            # Ensure HD-specific parameters are present (if not already)
            # This could be used to add default HD parameters in the future
            pass
    
    def generate_postman_collection(self, environment: str, 
                                  request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a Postman collection for a specific environment.
        
        Args:
            environment: Environment name
            request_data: Filtered request data
            
        Returns:
            Postman collection JSON
        """
        env_configs = self.env_manager.get_environment_specific_postman_configs()
        config = env_configs.get(environment, {})
        
        collection = {
            "info": {
                "name": config.get('name', f'KDF API ({environment.title()})'),
                "description": self._generate_collection_description(environment, config),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "_postman_id": f"kdf-{environment}-{datetime.now().strftime('%Y%m%d')}"
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": config.get('base_url', 'http://127.0.0.1:7783'),
                    "type": "string"
                },
                {
                    "key": "userpass",
                    "value": "RPC_UserP@SSW0RD",
                    "type": "string"
                }
            ],
            "item": []
        }
        
        # Group requests by method family
        method_groups = self._group_requests_by_method(request_data)
        
        for method_family, requests in method_groups.items():
            folder_item = {
                "name": method_family,
                "item": []
            }
            
            for request_key, request_body in requests.items():
                # Check if this request is compatible with the environment
                method = request_body.get('method', '')
                hardware = 'trezor' if 'trezor' in environment else None
                wallet_type = config.get('wallet_type', None)
                
                if self._is_request_compatible(request_key, method, environment, hardware, wallet_type):
                    postman_request = self._create_postman_request(
                        request_key, request_body, environment
                    )
                    folder_item["item"].append(postman_request)
            
            if folder_item["item"]:  # Only add non-empty folders
                collection["item"].append(folder_item)
        
        return collection
    
    def _generate_collection_description(self, environment: str, config: Dict) -> str:
        """Generate description for the collection."""
        description = config.get('description', f'KDF API for {environment} environment')
        notes = config.get('notes', '')
        
        protocol_info = ""
        if 'preferred_protocols' in config:
            protocols = config['preferred_protocols']
            protocol_details = []
            for proto_type, proto_list in protocols.items():
                protocol_details.append(f"{proto_type}: {', '.join(proto_list)}")
            protocol_info = f"\n\nSupported Protocols:\n- " + "\n- ".join(protocol_details)
        
        hardware_info = ""
        if 'hardware' in config:
            hardware_info = f"\n\nHardware Support: {', '.join(config['hardware'])}"
        
        return f"{description}\n\n{notes}{protocol_info}{hardware_info}"
    
    def _group_requests_by_method(self, request_data: Dict[str, Any]) -> Dict[str, Dict]:
        """Group requests by method family for better organization."""
        groups = {}
        
        for request_key, request_body in request_data.items():
            if not isinstance(request_body, dict):
                continue
            
            method = request_body.get('method', '')
            
            # Determine method family
            if method.startswith('task::enable_'):
                coin_type = method.split('::')[1].replace('enable_', '')
                family = f"Task Enable {coin_type.upper()}"
            elif method.startswith('enable_'):
                family = "Legacy Enable"
            else:
                family = "Other Methods"
            
            if family not in groups:
                groups[family] = {}
            
            groups[family][request_key] = request_body
        
        return groups
    
    def _is_request_compatible(self, request_key: str, method: str, 
                             environment: str, hardware: str = None, wallet_type: str = None) -> bool:
        """Check if a request is compatible with the target environment."""
        # Extract base environment (remove HD/wallet type suffixes)
        base_env = environment.split('_')[0]  # native_hd -> native
        
        # Check method compatibility
        is_compatible, _ = self.env_manager.validate_method_compatibility(
            method, base_env, hardware, wallet_type
        )
        
        if not is_compatible:
            return False
        
        # Check example-specific compatibility using pattern matching
        return self.env_manager._matches_pattern_requirements(
            request_key, base_env, hardware, wallet_type
        )
    
    def _create_postman_request(self, request_key: str, request_body: Dict[str, Any], 
                               environment: str) -> Dict[str, Any]:
        """Create a Postman request item."""
        # Get method info for better naming
        method = request_body.get('method', '')
        method_info = self.env_manager.methods_data.get(method, {})
        examples = method_info.get('examples', {})
        
        # Use translated name if available
        display_name = examples.get(request_key, request_key)
        
        # Add environment suffix for clarity
        if environment in ['wasm', 'trezor_native', 'trezor_wasm']:
            display_name += f" ({environment.replace('_', ' ').title()})"
        
        postman_request = {
            "name": display_name,
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps(request_body, indent=2)
                },
                "url": {
                    "raw": "{{base_url}}",
                    "host": ["{{base_url}}"]
                },
                "description": self._generate_request_description(request_key, method, environment)
            },
            "response": []
        }
        
        return postman_request
    
    def _generate_request_description(self, request_key: str, method: str, 
                                    environment: str) -> str:
        """Generate description for a request."""
        description = f"Method: {method}\nEnvironment: {environment.title()}"
        
        # Add environment-specific notes
        if environment == 'wasm':
            description += "\n\nNote: This request uses WebSocket Secure (WSS) protocols only."
        elif 'trezor' in environment:
            description += "\n\nNote: This request requires Trezor hardware wallet."
        
        # Add protocol preferences
        protocol_prefs = self.env_manager.get_protocol_preferences(method, environment.split('_')[0])
        if protocol_prefs:
            description += f"\n\nProtocol preferences: {protocol_prefs}"
        
        return description
    
    def generate_all_collections(self, output_format: str = 'json') -> Dict[str, str]:
        """Generate all environment-specific collections.
        
        Args:
            output_format: Output format ('json' or 'both')
            
        Returns:
            Dictionary mapping environment names to output file paths
        """
        generated_files = {}
        
        # Load base request data
        request_data = self.load_request_data('v2')
        
        # Get all environment configurations
        env_configs = self.env_manager.get_environment_specific_postman_configs()
        
        for environment in env_configs.keys():
            print(f"Generating collection for environment: {environment}")
            
            # Filter request data for this environment
            filtered_data = self.filter_protocols_for_environment(request_data, environment)
            
            # Generate Postman collection
            collection = self.generate_postman_collection(environment, filtered_data)
            
            # Save to file
            output_file = self.output_dir / f"kdf_{environment}_collection.json"
            with open(output_file, 'w') as f:
                json.dump(collection, f, indent=2)
            
            generated_files[environment] = str(output_file)
            print(f"  → {output_file}")
        
        return generated_files
    
    def generate_environment_summary(self) -> Dict[str, Any]:
        """Generate a summary of environment-specific features."""
        report = self.env_manager.generate_compatibility_report()
        
        summary = {
            "environments": self.env_manager.get_environment_specific_postman_configs(),
            "method_compatibility": report,
            "generated_collections": list(self.env_manager.get_environment_specific_postman_configs().keys()),
            "generation_timestamp": datetime.now().isoformat()
        }
        
        # Save summary
        summary_file = self.output_dir / "environment_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Generate environment-specific Postman collections for KDF API"
    )
    parser.add_argument(
        '--workspace', '-w',
        help="Path to workspace root (auto-detected if not provided)"
    )
    parser.add_argument(
        '--environment', '-e',
        choices=['native_hd', 'native_iguana', 'wasm_hd', 'wasm_iguana', 'trezor_native_hd', 'trezor_wasm_hd', 'all'],
        default='all',
        help="Specific environment to generate (default: all)"
    )
    parser.add_argument(
        '--output-dir', '-o',
        help="Output directory (default: postman/generated/environments)"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    try:
        generator = EnvironmentPostmanGenerator(args.workspace)
        
        if args.output_dir:
            generator.output_dir = Path(args.output_dir)
            generator.output_dir.mkdir(parents=True, exist_ok=True)
        
        if args.environment == 'all':
            print("Generating all environment-specific collections...")
            generated_files = generator.generate_all_collections()
            
            # Generate summary
            summary = generator.generate_environment_summary()
            
            print(f"\n✅ Generated {len(generated_files)} collections:")
            for env, file_path in generated_files.items():
                print(f"  {env}: {file_path}")
            
            print(f"\n📊 Summary: {generator.output_dir / 'environment_summary.json'}")
            
        else:
            print(f"Generating collection for environment: {args.environment}")
            request_data = generator.load_request_data('v2')
            filtered_data = generator.filter_protocols_for_environment(
                request_data, args.environment
            )
            collection = generator.generate_postman_collection(args.environment, filtered_data)
            
            output_file = generator.output_dir / f"kdf_{args.environment}_collection.json"
            with open(output_file, 'w') as f:
                json.dump(collection, f, indent=2)
            
            print(f"✅ Generated: {output_file}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
