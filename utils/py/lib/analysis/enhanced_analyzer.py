#!/usr/bin/env python3
"""
Enhanced KDF Repository Analyzer - Focused on Actionable Data Extraction

This module provides targeted analysis of the local KDF repository to extract:
- Method-specific parameters with realistic types and descriptions
- Common error patterns based on method categories
- Realistic examples based on method patterns
- Clean, actionable information for documentation generation

Uses pattern matching and method categorization for intelligent parameter inference.
"""

import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Union

from ..utils.logging_utils import get_logger
from ...data.coins_config_loader import CoinsConfigLoader
from ..constants import ParameterInfo, UnifiedErrorInfo, UnifiedExampleInfo, UnifiedMethodInfo


class EnhancedRepositoryAnalyzer:
    """
    Enhanced analyzer that extracts actionable method information using
    pattern matching and method categorization.
    """
    
    def __init__(self, repo_path: Optional[Union[str, Path]] = None, 
                 default_branch: str = "dev", verbose: bool = True):
        """Initialize the enhanced repository analyzer."""
        self.repo_path = Path(repo_path) if repo_path else Path(__file__).parent.parent.parent / "data" / "komodo-defi-framework"
        self.default_branch = default_branch
        self.verbose = verbose
        self.logger = self._setup_logger()
        
        if self.verbose:
            self.logger.info(f"🔧 Enhanced analyzer using local repo: {self.repo_path}")
            self.logger.info(f"🌿 Default branch: {self.default_branch}")
        
        # Initialize structure and enum mappings
        self._init_structure_mappings()
        self._init_enum_mappings()
        
        # Initialize parameter patterns and error definitions
        self._init_parameter_patterns()
        self._init_error_patterns()
        
        # Method pattern definitions for intelligent parameter inference
        self.method_patterns = {
            "task_init": {
                "pattern": r"task::.+::init$",
                "common_params": ["ticker", "activation_params", "priv_key_policy"]
            },
            "task_status": {
                "pattern": r"task::.+::status$", 
                "common_params": ["task_id"]
            },
            "task_cancel": {
                "pattern": r"task::.+::cancel$",
                "common_params": ["task_id"]
            },
            "task_user_action": {
                "pattern": r"task::.+::user_action$",
                "common_params": ["task_id"]
            },
            "lightning_payment": {
                "pattern": r"lightning::payments::.+",
                "common_params": ["coin"]
            },
            "lightning_channel": {
                "pattern": r"lightning::channels::.+", 
                "common_params": ["coin"]
            },
            "lightning_node": {
                "pattern": r"lightning::nodes::.+",
                "common_params": ["coin"]
            },
            "stream_enable": {
                "pattern": r"stream::.+::enable$",
                "common_params": []
            },
            "gui_storage": {
                "pattern": r"gui_storage::.+",
                "common_params": []
            }
        }
        
        # Define parameter patterns for different method types
        self.parameter_definitions = {
            "ticker": ParameterInfo(
                name="ticker",
                type="string",
                required=True,
                default=None,
                description="The ticker symbol of the coin to activate",
                example='"KMD"'
            ),
            "activation_params": ParameterInfo(
                name="activation_params",
                type="object",
                required=True,
                default=None,
                description="A standard ActivationParams object containing activation configuration parameters",
                example='{"mode": {"rpc": "Electrum", "rpc_data": {"servers": [{"url": "electrum1.cipig.net:10001"}]}}}'
            ),
            "priv_key_policy": ParameterInfo(
                name="priv_key_policy",
                type="string",
                required=False,
                default="`ContextPrivKey`",
                description="Value can be PrivKeyActivationPolicy for coin activation",
                example='"Trezor"'
            ),
            "task_id": ParameterInfo(
                name="task_id",
                type="integer",
                required=True,
                default=None,
                description="The identifier of the task to query",
                example="12345"
            ),
            "coin": ParameterInfo(
                name="coin",
                type="string",
                required=True,
                default=None,
                description="Coin identifier",
                example='"KMD"'
            ),
            "address": ParameterInfo(
                name="address",
                type="string",
                required=True,
                default=None,
                description="Coin address",
                example='"RXL3YXG2ceaB6C5hfJcN4fvmLH2C34knhA"'
            ),
            "amount": ParameterInfo(
                name="amount",
                type="string",
                required=True,
                default=None,
                description="Amount to process",
                example='"1.0"'
            )
        }
        
        # Common error patterns by method category
        self.error_patterns = {
            "task": [
                UnifiedErrorInfo("NoSuchTask", "string", "The specified task was not found or has expired"),
                UnifiedErrorInfo("TaskFinished", "string", "The task is already finished and cannot be modified"),
                UnifiedErrorInfo("TaskTimedOut", "string", "The task operation timed out"),
                UnifiedErrorInfo("CoinCreationError", "string", "Error occurred during coin activation"),
                UnifiedErrorInfo("HwError", "string", "Hardware wallet error requiring user action")
            ],
            "lightning": [
                UnifiedErrorInfo("LightningError", "string", "Lightning Network operation failed"),
                UnifiedErrorInfo("NoSuchCoin", "string", "The specified coin is not activated"),
                UnifiedErrorInfo("InsufficientBalance", "string", "Insufficient balance for the operation"),
                UnifiedErrorInfo("ChannelNotFound", "string", "The specified channel was not found")
            ],
            "gui_storage": [
                UnifiedErrorInfo("AccountNotFound", "string", "The specified account was not found"),
                UnifiedErrorInfo("StorageError", "string", "Error accessing GUI storage"),
                UnifiedErrorInfo("InvalidAccountData", "string", "The account data is invalid")
            ],
            "stream": [
                UnifiedErrorInfo("CoinNotFound", "string", "The specified coin was not found"),
                UnifiedErrorInfo("UnknownClient", "string", "No client connection found with this client_id"),
                UnifiedErrorInfo("ClientAlreadyListening", "string", "The client is already listening to this stream"),
                UnifiedErrorInfo("CoinNotSupported", "string", "The coin type is not supported for streaming")
            ],
            "common": [
                UnifiedErrorInfo("InvalidUserpass", "string", "The userpass provided is invalid"),
                UnifiedErrorInfo("InternalError", "string", "An internal error occurred"),
                UnifiedErrorInfo("InvalidRequest", "string", "The request parameters are invalid")
            ]
        }
        
        # Initialize coins configuration loader
        self.coins_loader = CoinsConfigLoader()
        self.coins_loader.load_config()
    
    def _setup_logger(self):
        """Set up logger for the enhanced analyzer."""
        return get_logger("enhanced-analyzer")
    
    def _init_structure_mappings(self):
        """Initialize mappings between KDF structures and MDX documentation."""
        self.structure_mappings = {
            # Common activation structures
            "ActivationParams": {
                "mdx_name": "ActivationParams",
                "link": "/komodo-defi-framework/api/common_structures/activation/#activation-params"
            },
            "ActivationMode": {
                "mdx_name": "ActivationMode", 
                "link": "/komodo-defi-framework/api/common_structures/activation/#activation-mode"
            },
            "ActivationRpcData": {
                "mdx_name": "ActivationRpcData",
                "link": "/komodo-defi-framework/api/common_structures/activation/#activation-rpc-data"
            },
            "ActivationServers": {
                "mdx_name": "ActivationServers",
                "link": "/komodo-defi-framework/api/common_structures/activation/#activation-servers"
            },
            "AddressDerivationPath": {
                "mdx_name": "AddressDerivationPath",
                "link": "/komodo-defi-framework/api/common_structures/activation/#address-derivation-path"
            },
            "TokensRequest": {
                "mdx_name": "TokensRequest",
                "link": "/komodo-defi-framework/api/common_structures/activation/#tokens-request"
            },
            "UtxoMergeParams": {
                "mdx_name": "UtxoMergeParams",
                "link": "/komodo-defi-framework/api/common_structures/activation/#utxo-merge-params"
            },
            # Wallet structures
            "BalanceInfo": {
                "mdx_name": "BalanceInfo",
                "link": "/komodo-defi-framework/api/common_structures/wallet/#balance-info"
            },
            "DerivationMethod": {
                "mdx_name": "DerivationMethod", 
                "link": "/komodo-defi-framework/api/common_structures/wallet/#derivation-method"
            },
            # Lightning structures
            "ConfirmationTargets": {
                "mdx_name": "ConfirmationTargets",
                "link": "/komodo-defi-framework/api/common_structures/lightning/#confirmation-targets"
            }
        }
    
    def _init_enum_mappings(self):
        """Initialize mappings between KDF enums and MDX documentation."""
        self.enum_mappings = {
            # Private key policy enums
            "PrivKeyActivationPolicy": {
                "mdx_name": "PrivKeyActivationPolicyEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#priv-key-activation-policy-enum"
            },
            "EthPrivKeyActivationPolicy": {
                "mdx_name": "EthPrivKeyActivationPolicyEnum", 
                "link": "/komodo-defi-framework/api/common_structures/enums/#eth-priv-key-activation-policy-enum"
            },
            "PrivKeyPolicy": {
                "mdx_name": "PrivKeyPolicyEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#priv-key-policy-enum"
            },
            # RPC mode enums
            "UtxoRpcMode": {
                "mdx_name": "UtxoRpcModeEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#utxo-rpc-mode-enum"
            },
            "EthRpcMode": {
                "mdx_name": "EthRpcModeEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#eth-rpc-mode-enum"
            },
            "ZcoinRpcMode": {
                "mdx_name": "ZcoinRpcModeEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#zcoin-rpc-mode-enum"
            },
            # Scan policy enum
            "ScanPolicy": {
                "mdx_name": "ScanPolicyEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#scan-policy-enum"
            },
            # Trading enums
            "SwapMethod": {
                "mdx_name": "SwapMethodEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#swap-method-enum"
            },
            "OrderType": {
                "mdx_name": "OrderTypeEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#order-type-enum"
            },
            "OrderStatus": {
                "mdx_name": "OrderStatusEnum",
                "link": "/komodo-defi-framework/api/common_structures/enums/#order-status-enum"
            }
        }
    
    def _detect_structure_references(self, description: str, param_type: str) -> str:
        """Detect and link to common structures and enums in descriptions."""
        enhanced_description = description
        
        # Skip if already contains markdown links to avoid double-linking
        if '[' in enhanced_description and '](' in enhanced_description:
            return enhanced_description
        
        # Check for structure references
        for kdf_name, mapping in self.structure_mappings.items():
            if kdf_name.lower() in enhanced_description.lower() or kdf_name.lower() in param_type.lower():
                link_text = f"[{mapping['mdx_name']}]({mapping['link']})"
                
                # Replace mentions in description (case-insensitive, whole word only)
                import re
                pattern = re.compile(r'\b' + re.escape(kdf_name) + r'\b', re.IGNORECASE)
                enhanced_description = pattern.sub(link_text, enhanced_description, count=1)
        
        # Check for enum references  
        for kdf_name, mapping in self.enum_mappings.items():
            if kdf_name.lower() in enhanced_description.lower() or kdf_name.lower() in param_type.lower():
                link_text = f"[{mapping['mdx_name']}]({mapping['link']})"
                
                # Replace mentions in description (case-insensitive, whole word only)
                import re
                pattern = re.compile(r'\b' + re.escape(kdf_name) + r'\b', re.IGNORECASE)
                enhanced_description = pattern.sub(link_text, enhanced_description, count=1)
        
        return enhanced_description
    
    def _report_structure_mismatches(self, found_structures: Set[str]) -> List[str]:
        """Report any structure/enum mismatches found in KDF repo vs MDX docs."""
        mismatches = []
        
        for structure in found_structures:
            if structure not in self.structure_mappings and structure not in self.enum_mappings:
                # Try to guess the MDX name
                potential_mdx_name = structure
                if not structure.endswith("Enum") and structure.endswith("Policy"):
                    potential_mdx_name = structure + "Enum"
                elif not structure.endswith("Params") and "param" in structure.lower():
                    potential_mdx_name = structure + "Params"
                
                mismatches.append(f"KDF: '{structure}' -> Assumed MDX: '{potential_mdx_name}'")
        
        return mismatches
    
    def switch_branch(self, branch: str) -> bool:
        """Switch the local repository to the specified branch."""
        try:
            if self.verbose:
                self.logger.info(f"🔄 Switching to branch: {branch}")
            
            result = subprocess.run(
                ["git", "checkout", branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                if self.verbose:
                    self.logger.success(f"✅ Switched to branch: {branch}")
                return True
            else:
                if self.verbose:
                    self.logger.warning(f"⚠️ Failed to switch to branch {branch}: {result.stderr}")
                return False
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error switching branch: {e}")
            return False
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current git branch of the repository."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None
                
        except Exception as e:
            if self.verbose:
                self.logger.debug(f"Could not get current branch: {e}")
            return None
    
    def pull_latest(self, branch: Optional[str] = None) -> bool:
        """Pull the latest changes from the remote repository."""
        try:
            if branch:
                self.switch_branch(branch)
            
            if self.verbose:
                current_branch = self.get_current_branch()
                self.logger.info(f"📥 Pulling latest changes from {current_branch}")
            
            result = subprocess.run(
                ["git", "pull"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                if self.verbose:
                    self.logger.success("✅ Repository updated successfully")
                return True
            else:
                if self.verbose:
                    self.logger.warning(f"⚠️ Failed to pull: {result.stderr}")
                return False
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error pulling repository: {e}")
            return False
    
    def _init_error_patterns(self):
        """Initialize common error patterns for different method types."""
        self.error_patterns = {
            "common": [
                UnifiedErrorInfo(
                    name="InvalidUserpass",
                    type="string",
                    description="The userpass provided is invalid"
                ),
                UnifiedErrorInfo(
                    name="InternalError",
                    type="string", 
                    description="An internal error occurred processing the request"
                )
            ],
            "task": [
                UnifiedErrorInfo(
                    name="NoSuchTask",
                    type="string",
                    description="The specified task was not found or has expired"
                ),
                UnifiedErrorInfo(
                    name="TaskFinished",
                    type="string",
                    description="The task is already finished and cannot be modified"
                ),
                UnifiedErrorInfo(
                    name="TaskTimedOut",
                    type="string",
                    description="The task operation timed out"
                )
            ],
            "coin_activation": [
                UnifiedErrorInfo(
                    name="CoinCreationError",
                    type="string",
                    description="Error occurred during coin activation"
                ),
                UnifiedErrorInfo(
                    name="CoinAlreadyActivated",
                    type="string",
                    description="The coin is already activated"
                ),
                UnifiedErrorInfo(
                    name="InvalidActivationParams",
                    type="string",
                    description="The activation parameters are invalid or incomplete"
                )
            ],
            "lightning": [
                UnifiedErrorInfo(
                    name="LightningError",
                    type="string",
                    description="Lightning network operation failed"
                ),
                UnifiedErrorInfo(
                    name="InvoiceError",
                    type="string",
                    description="Invalid or expired Lightning invoice"
                ),
                UnifiedErrorInfo(
                    name="ChannelError",
                    type="string",
                    description="Lightning channel operation failed"
                )
            ]
        }
    
    async def analyze_method_comprehensive(self, method_name: str, version: str, 
                                         branch: Optional[str] = None) -> UnifiedMethodInfo:
        """Perform comprehensive analysis of a method with structure/enum detection."""
        try:
            if self.verbose:
                self.logger.info(f"🔍 Analyzing {method_name} ({version}) on branch {branch or self.default_branch}")
            
            # Switch branch if needed
            if branch and branch != self.get_current_branch():
                self.switch_branch(branch)
            
            # Classify method and extract information
            category = self._classify_method_category(method_name)
            parameters = self._extract_method_parameters(method_name, category, version)
            errors = self._extract_method_errors(method_name, category)
            examples = self._generate_method_examples(method_name, version, parameters)
            
            # Track structures/enums found for mismatch reporting
            found_structures = set()
            
            # Scan for additional structures in the KDF repository
            if self.repo_path.exists():
                try:
                    # Look for struct/enum definitions related to this method
                    rust_files = list(self.repo_path.rglob("*.rs"))
                    for file_path in rust_files[:50]:  # Limit to avoid performance issues
                        try:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')
                            # Extract struct and enum names
                            struct_matches = re.findall(r'pub struct (\w+)', content)
                            enum_matches = re.findall(r'pub enum (\w+)', content)
                            found_structures.update(struct_matches + enum_matches)
                        except Exception:
                            continue
                except Exception as e:
                    if self.verbose:
                        self.logger.warning(f"Could not scan repository for structures: {e}")
            
            # Report structure mismatches
            mismatches = self._report_structure_mismatches(found_structures)
            if mismatches and self.verbose:
                self.logger.info("📋 Structure/Enum Mismatches Found:")
                for mismatch in mismatches[:10]:  # Limit output
                    self.logger.info(f"   {mismatch}")
            
            # Generate description with enhanced context
            description = self._generate_enhanced_description(method_name, category)
            
            # Find related methods
            related_methods = self._find_related_methods(method_name)
            
            # Extract method tags
            tags = self._extract_method_tags(method_name, category)
            
            return UnifiedMethodInfo(
                name=method_name,
                version=version,
                handler_file=None,  # Could be enhanced to find actual handler file
                description=description,
                parameters=parameters,
                error_types=errors,
                examples=examples,
                related_methods=related_methods,
                tags=tags
            )
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Analysis failed for {method_name}: {e}")
            raise
    
    def _classify_method_category(self, method_name: str) -> str:
        """Classify method into categories for parameter/error inference."""
        if "task::" in method_name:
            return "task"
        elif "lightning::" in method_name:
            return "lightning"
        elif "stream::" in method_name:
            return "stream"
        elif "gui_storage::" in method_name:
            return "gui_storage"
        elif "enable" in method_name or "activation" in method_name:
            return "coin_activation"
        else:
            return "general"
    
    def _extract_method_errors(self, method_name: str, category: str) -> List[UnifiedErrorInfo]:
        """Extract relevant errors based on method category."""
        errors = []
        
        # Always include common errors
        errors.extend(self.error_patterns["common"])
        
        # Add category-specific errors
        if category in self.error_patterns:
            errors.extend(self.error_patterns[category])
        
        return errors
    
    def _generate_enhanced_description(self, method_name: str, category: str) -> str:
        """Generate enhanced description with proper context."""
        if "::" in method_name:
            parts = method_name.split("::")
            
            if parts[0] == "task":
                if "init" in method_name:
                    coin_type = parts[1].replace("enable_", "").replace("_", " ").upper()
                    return f"Initialize the {coin_type} activation task"
                elif "cancel" in method_name:
                    coin_type = parts[1].replace("enable_", "").replace("_", " ").upper()
                    return f"Cancel the {coin_type} activation task"
                elif "status" in method_name:
                    coin_type = parts[1].replace("enable_", "").replace("_", " ").upper()
                    return f"Get the status of the {coin_type} activation task"
                elif "user_action" in method_name:
                    coin_type = parts[1].replace("enable_", "").replace("_", " ").upper()
                    return f"Handle user action for the {coin_type} activation task"
                else:
                    return f"Manage the {parts[1].replace('_', ' ')} task operation"
            
            elif parts[0] == "lightning":
                operation = parts[-1].replace("_", " ")
                return f"Handle Lightning Network {operation} operations"
            
            elif parts[0] == "stream":
                operation = parts[-1].replace("_", " ")
                return f"Manage {operation} streaming functionality"
            
            elif parts[0] == "gui_storage":
                operation = parts[1].replace("_", " ")
                return f"Handle GUI storage {operation} operations"
        
        # Default description
        operation = method_name.replace("_", " ")
        return f"Handle {operation} operations"
    
    def _find_related_methods(self, method_name: str) -> List[str]:
        """Find related methods based on naming patterns."""
        related = []
        
        if "::" in method_name:
            parts = method_name.split("::")
            base = "::".join(parts[:-1])
            
            # For task methods, find the full lifecycle
            if method_name.endswith("::init"):
                related.extend([
                    f"{base}::status",
                    f"{base}::cancel",
                    f"{base}::user_action"
                ])
            elif method_name.endswith("::status"):
                related.extend([
                    f"{base}::init",
                    f"{base}::cancel"
                ])
            elif method_name.endswith("::cancel"):
                related.extend([
                    f"{base}::init",
                    f"{base}::status"
                ])
        
        return related
    
    def _extract_method_tags(self, method_name: str, category: str) -> List[str]:
        """Extract tags from method name and category."""
        tags = [category]
        
        if "::" in method_name:
            parts = method_name.split("::")
            if len(parts) > 1 and parts[1] not in tags:
                tags.append(parts[1])
        
        return tags
    
    def _categorize_method(self, method_name: str) -> str:
        """Categorize method based on naming patterns."""
        for category, config in self.method_patterns.items():
            if re.match(config["pattern"], method_name):
                return category
        
        # Default categorization
        if "::" in method_name:
            return method_name.split("::")[0]
        return "utils"
    
    def _generate_method_description(self, method_name: str, category: str) -> str:
        """Generate a concise, meaningful description for the method."""
        # Extract the action part of the method name
        if "::" in method_name:
            parts = method_name.split("::")
            if len(parts) >= 3:
                action = parts[-1].replace("_", " ")
                target = parts[-2].replace("_", " ")
                namespace = parts[0]
                
                if namespace == "task":
                    if action == "init":
                        return f"Initialize the {target} activation task"
                    elif action == "status":
                        return f"Check the status of the {target} activation task"
                    elif action == "cancel":
                        return f"Cancel the {target} activation task"
                    elif action == "user_action":
                        return f"Handle user action for the {target} activation task"
                elif namespace == "lightning":
                    return f"Handle Lightning Network {target} {action} operations"
                elif namespace == "gui_storage":
                    return f"Manage GUI storage {action} operations for {target}"
                elif namespace == "stream":
                    return f"Handle {target} streaming {action} operations"
            else:
                action = parts[-1].replace("_", " ")
                namespace = parts[0]
                return f"Handle {namespace} {action} operations"
        else:
            # Simple method names
            action = method_name.replace("_", " ")
            return f"Utility method for {action} operations"
    
    def _extract_method_parameters(self, method_name: str, category: str, version: str) -> List[ParameterInfo]:
        """Extract parameters based on method patterns and category."""
        parameters = []
        
        # Always include userpass for all methods
        parameters.append(ParameterInfo(
            name="userpass",
            type="string",
            required=True,
            default=None,
            description="Password for authentication",
            example='"RPC_UserP@SSW0RD"'
        ))
        
        # Get appropriate coin example for this method
        example_coin = self.coins_loader.get_example_coin_for_method(method_name)
        coin_ticker = example_coin.coin if example_coin else "KMD"
        
        # Get pattern-based parameters
        for pattern_name, config in self.method_patterns.items():
            if re.match(config["pattern"], method_name):
                for param_name in config["common_params"]:
                    param_info = self.parameter_definitions.get(param_name)
                    if param_info:
                        # Customize examples based on coin configuration
                        example = param_info.example
                        description = param_info.description
                        
                        # Update coin-specific examples
                        if param_name == "coin" and example_coin:
                            example = f'\"{coin_ticker}\"'
                            description = f"The coin ticker to use (e.g., {coin_ticker} for {example_coin.protocol_type} protocol)"
                        elif param_name == "ticker" and example_coin:
                            example = f'\"{coin_ticker}\"'
                            description = f"The coin ticker (e.g., {coin_ticker} for {example_coin.protocol_type} protocol)"
                        elif param_name == "activation_params" and example_coin:
                            activation_example = self.coins_loader.get_activation_params_example(example_coin)
                            example = json.dumps(activation_example, indent=2)
                            description = f"[ActivationParams](/komodo-defi-framework/api/common_structures/activation/#activation-params) for {example_coin.protocol_type} protocol"
                        elif param_name == "contract_address" and example_coin and example_coin.contract_address:
                            example = f'\"{example_coin.contract_address}\"'
                            description = f"The contract address for the token (e.g., {example_coin.contract_address} for {coin_ticker})"
                        elif param_name == "parent_coin" and example_coin and example_coin.parent_coin:
                            example = f'\"{example_coin.parent_coin}\"'
                            description = f"The parent coin (e.g., {example_coin.parent_coin} for {coin_ticker})"
                        elif param_name == "derivation_path" and example_coin and example_coin.derivation_path:
                            example = f'\"{example_coin.derivation_path}\"'
                            description = f"The derivation path (e.g., {example_coin.derivation_path} for {example_coin.protocol_type} protocol)"
                        
                        # Apply structure detection to description
                        enhanced_description = self._detect_structure_references(description, param_info.type)
                        
                        parameters.append(ParameterInfo(
                            name=param_name,
                            type=param_info.type,
                            required=param_info.required,
                            default=param_info.default,
                            description=enhanced_description,
                            example=example
                        ))
                break
        
        # Add method-specific parameters based on category
        if category == "task" and "init" in method_name:
            if not any(p.name == "activation_params" for p in parameters) and example_coin:
                activation_example = self.coins_loader.get_activation_params_example(example_coin)
                parameters.append(ParameterInfo(
                    name="activation_params",
                    type="object",
                    required=True,
                    default=None,
                    description="[ActivationParams](/komodo-defi-framework/api/common_structures/activation/#activation-params) for coin activation",
                    example=json.dumps(activation_example, indent=2)
                ))
        
        # Sort parameters: required first, then optional, alphabetically within each group
        required_params = [p for p in parameters if p.required]
        optional_params = [p for p in parameters if not p.required]
        
        required_params.sort(key=lambda x: x.name)
        optional_params.sort(key=lambda x: x.name)
        
        return required_params + optional_params
    
    def _generate_method_examples(self, method_name: str, version: str, 
                                parameters: List[ParameterInfo]) -> List[UnifiedExampleInfo]:
        """Generate realistic examples based on method type and parameters."""
        examples = []
        
        # Build request based on version
        if version == "v1":
            request = {
                "method": method_name,
                "userpass": "RPC_UserP@SSW0RD"
            }
            
            # Add parameters directly to request
            for param in parameters:
                if param.name != "userpass" and param.required:
                    if param.example:
                        try:
                            # Try to parse as JSON for complex types
                            value = json.loads(param.example)
                        except:
                            # Use as string if not valid JSON
                            value = param.example.strip('"')
                        request[param.name] = value
        else:  # v2
            request = {
                "mmrpc": "2.0",
                "method": method_name,
                "userpass": "RPC_UserP@SSW0RD",
                "params": {},
                "id": 0
            }
            
            # Add parameters to params object
            for param in parameters:
                if param.name != "userpass":
                    if param.required:
                        if param.example:
                            try:
                                # Try to parse as JSON for complex types
                                value = json.loads(param.example)
                            except (json.JSONDecodeError, TypeError):
                                # Use as string if not valid JSON
                                value = param.example.strip('"')
                            request["params"][param.name] = value
                    elif param.default and not param.default.startswith("`"):
                        # Include optional parameters with defaults for demonstration
                        try:
                            value = json.loads(param.default)
                        except (json.JSONDecodeError, TypeError):
                            value = param.default.strip('"`')
                        request["params"][param.name] = value
        
        # Generate appropriate response
        response = self._generate_method_response(method_name, version)
        
        # Create example
        example = UnifiedExampleInfo(
            title=f"{method_name.replace('_', ' ').title()} Example",
            request=request,
            response=response,
            description=f"Example request for {method_name}"
        )
        
        examples.append(example)
        return examples
    
    def _generate_method_response(self, method_name: str, version: str) -> Dict[str, Any]:
        """Generate realistic response based on method type."""
        base_response = {
            "mmrpc": "2.0",
            "id": 0
        } if version == "v2" else {}
        
        # Method-specific responses
        if "init" in method_name and "task::" in method_name:
            result = {"task_id": 12345}
        elif "status" in method_name and "task::" in method_name:
            result = {
                "status": "InProgress",
                "details": "Activating coin..."
            }
        elif "cancel" in method_name and "task::" in method_name:
            result = "success"
        elif "get_new_address" in method_name:
            result = {
                "address": "RXL3YXG2ceaB6C5hfJcN4fvmLH2C34knhA",
                "derivation_path": "m/44'/141'/0'/0/1"
            }
        elif "get_public_key" in method_name:
            result = {
                "public_key": "0366d28a7926fb20287132692c4cef7bc7e00e76da064948676f8549c0ed7114d3"
            }
        elif "lightning" in method_name and "payment" in method_name:
            result = {
                "payment_hash": "abc123...",
                "status": "completed"
            }
        else:
            result = {"success": True}
        
        if version == "v2":
            base_response["result"] = result
        else:
            base_response.update(result)
        
        return base_response

    def _init_parameter_patterns(self):
        """Initialize parameter patterns for different method types."""
        # Method pattern definitions for intelligent parameter inference
        self.method_patterns = {
            "task_init": {
                "pattern": r"task::.+::init$",
                "common_params": ["ticker", "activation_params", "priv_key_policy"]
            },
            "task_status": {
                "pattern": r"task::.+::status$", 
                "common_params": ["task_id"]
            },
            "task_cancel": {
                "pattern": r"task::.+::cancel$",
                "common_params": ["task_id"]
            },
            "task_user_action": {
                "pattern": r"task::.+::user_action$",
                "common_params": ["task_id"]
            },
            "lightning_payment": {
                "pattern": r"lightning::payments::.+",
                "common_params": ["coin"]
            },
            "lightning_channel": {
                "pattern": r"lightning::channels::.+", 
                "common_params": ["coin"]
            },
            "lightning_node": {
                "pattern": r"lightning::nodes::.+",
                "common_params": ["coin"]
            },
            "stream_enable": {
                "pattern": r"stream::.+::enable$",
                "common_params": []
            },
            "gui_storage": {
                "pattern": r"gui_storage::.+",
                "common_params": []
            }
        }
        
        # Define parameter patterns for different method types
        self.parameter_definitions = {
            "ticker": ParameterInfo(
                name="ticker",
                type="string",
                required=True,
                default=None,
                description="The ticker symbol of the coin to activate",
                example='"KMD"'
            ),
            "activation_params": ParameterInfo(
                name="activation_params",
                type="object",
                required=True,
                default=None,
                description="A standard ActivationParams object containing activation configuration parameters",
                example='{"mode": {"rpc": "Electrum", "rpc_data": {"electrum_servers": [{"url": "electrum1.cipig.net:10001"}], "electrum_rpc_password": "pass"}}}'
            ),
            "priv_key_policy": ParameterInfo(
                name="priv_key_policy",
                type="string",
                required=False,
                default="`ContextPrivKey`",
                description="Value can be PrivKeyActivationPolicy for coin activation",
                example='"Trezor"'
            ),
            "task_id": ParameterInfo(
                name="task_id",
                type="integer",
                required=True,
                default=None,
                description="The identifier of the task to query",
                example="12345"
            ),
            "coin": ParameterInfo(
                name="coin",
                type="string",
                required=True,
                default=None,
                description="Coin identifier",
                example='"KMD"'
            ),
            "address": ParameterInfo(
                name="address",
                type="string",
                required=True,
                default=None,
                description="Coin address",
                example='"RXL3YXG2ceaB6C5hfJcN4fvmLH2C34knhA"'
            ),
            "amount": ParameterInfo(
                name="amount",
                type="string",
                required=True,
                default=None,
                description="Amount to process",
                example='"1.0"'
            )
        } 