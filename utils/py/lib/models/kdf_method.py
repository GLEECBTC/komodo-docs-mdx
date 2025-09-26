#!/usr/bin/env python3
"""
KDF Method Models - Object-oriented representation of KDF API methods and examples.

This module provides structured classes for representing KDF methods, their examples,
prerequisites, and execution status.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum
import json
from pathlib import Path


class MethodStatus(Enum):
    """Status of a method during processing."""
    PENDING = "pending"
    PREREQUISITES_NEEDED = "prerequisites_needed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class KdfExample:
    """Represents a single example request/response for a KDF method."""
    name: str
    description: str
    request_data: Dict[str, Any]
    response_data: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None
    error_data: Optional[Dict[str, Any]] = None
    instance_responses: Dict[str, Any] = field(default_factory=dict)
    collected: bool = False
    
    @property
    def has_response(self) -> bool:
        """Check if this example has response data."""
        return self.response_data is not None or bool(self.instance_responses)
    
    @property
    def is_successful(self) -> bool:
        """Check if this example completed successfully."""
        return self.collected and self.has_response and not self.error_data

    @staticmethod
    def _contains_string_in_data(data: Any, search_string: str) -> bool:
        """Recursively search for a string in any data structure."""
        if isinstance(data, str):
            return search_string.lower() in data.lower()
        elif isinstance(data, dict):
            for key, value in data.items():
                if search_string.lower() in key.lower():
                    return True
                if KdfExample._contains_string_in_data(value, search_string):
                    return True
        elif isinstance(data, list):
            for item in data:
                if KdfExample._contains_string_in_data(item, search_string):
                    return True
        return False

    @property
    def is_manual(self) -> bool:
        """Detect if example likely requires manual interaction/hardware."""
        manual_terms = [
            "walletconnect",
            "trezor",
            "metamask",
            "useraction",
            "user_action",
        ]
        name_l = self.name.lower()
        if any(t in name_l for t in manual_terms):
            return True
        desc_l = (self.description or "").lower()
        if any(t in desc_l for t in manual_terms):
            return True
        for term in manual_terms:
            if KdfExample._contains_string_in_data(self.request_data, term):
                return True
        return False

@dataclass
class KdfMethod:
    """Represents a KDF API method with its configuration and examples."""
    name: str
    sequence: int
    tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    request_table: str = ""
    response_table: str = ""
    errors_table: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None
    deprecated: bool = False
    examples: Dict[str, KdfExample] = field(default_factory=dict)
    status: MethodStatus = MethodStatus.PENDING
    prerequisite_methods_completed: Set[str] = field(default_factory=set)
    
    @classmethod
    def from_json(cls, name: str, method_data: Dict[str, Any], request_examples: Dict[str, Dict[str, Any]]) -> 'KdfMethod':
        """Create a KdfMethod instance from JSON configuration data."""
        # Extract examples and create KdfExample objects
        examples = {}
        example_configs = method_data.get("examples", {})
        
        for example_name, example_description in example_configs.items():
            if example_name in request_examples:
                request_data = request_examples[example_name]
                examples[example_name] = KdfExample(
                    name=example_name,
                    description=example_description,
                    request_data=request_data
                )
        
        return cls(
            name=name,
            sequence=method_data.get("sequence", 100),
            tags=method_data.get("tags", []),
            prerequisites=method_data.get("prerequisites", []),
            request_table=method_data.get("request_table", ""),
            response_table=method_data.get("response_table", ""),
            errors_table=method_data.get("errors_table", ""),
            requirements=method_data.get("requirements", {}),
            timeout=method_data.get("timeout"),
            deprecated=method_data.get("deprecated", False),
            examples=examples
        )

    @classmethod
    def from_config(cls, name: str, method_data: Dict[str, Any]) -> 'KdfMethod':
        """Create a KdfMethod from method config only (no request data binding)."""
        # Build examples map with empty request_data to satisfy typing
        examples: Dict[str, KdfExample] = {}
        for example_name, example_description in (method_data.get("examples", {}) or {}).items():
            examples[example_name] = KdfExample(
                name=example_name,
                description=example_description,
                request_data={}
            )
        return cls(
            name=name,
            sequence=method_data.get("sequence", 100),
            tags=method_data.get("tags", []),
            prerequisites=method_data.get("prerequisites", []),
            request_table=method_data.get("request_table", ""),
            response_table=method_data.get("response_table", ""),
            errors_table=method_data.get("errors_table", ""),
            requirements=method_data.get("requirements", {}),
            timeout=method_data.get("timeout"),
            deprecated=method_data.get("deprecated", False),
            examples=examples
        )

    # ===== Capability helpers (moved from EnvironmentManager) =====

    @property
    def supported_environments(self) -> List[str]:
        reqs = self.requirements or {}
        return reqs.get("environments", []) or []

    def supports_environment(self, environment: str) -> bool:
        return environment in self.supported_environments

    @property
    def supported_wallet_types(self) -> List[str]:
        reqs = self.requirements or {}
        return reqs.get("wallet_types", []) or []

    def supports_wallet_type(self, wallet_type: str) -> bool:
        return wallet_type in self.supported_wallet_types

    @property
    def required_hardware(self) -> List[str]:
        reqs = self.requirements or {}
        return reqs.get("hardware", []) or []

    def requires_hardware(self, hardware_type: Optional[str] = None) -> bool:
        hardware_list = self.required_hardware
        if hardware_type is None:
            return len(hardware_list) > 0
        return hardware_type in hardware_list

    def get_protocol_preferences(self, environment: str) -> Dict[str, List[str]]:
        reqs = self.requirements or {}
        protocols = reqs.get("protocols", {}) or {}
        result: Dict[str, List[str]] = {}
        for proto_type, env_map in protocols.items():
            if isinstance(env_map, dict) and environment in env_map:
                result[proto_type] = env_map[environment]
        return result

    @property
    def is_manual_method(self) -> bool:
        """Detect if method/examples require manual testing (WalletConnect, Trezor, Metamask, PIN, UserAction)."""
        manual_terms = [
            "walletconnect",
            "trezor",
            "metamask",
            "pin",
            "useraction",
            "user_action",
        ]
        name_l = self.name.lower()
        if any(t in name_l for t in manual_terms):
            return True
        # Check examples by name/desc
        for ex in self.examples.values():
            if ex.is_manual:
                return True
        # Check tags/requirements for hardware flags
        req = self.requirements or {}
        hardware = [h.lower() for h in req.get("hardware", []) if isinstance(h, str)]
        if any(h in ["trezor", "ledger", "metamask", "walletconnect"] for h in hardware):
            return True
        return False

    def get_conditional_params_for_wallet(self, wallet_type: Optional[str] = None) -> List[str]:
        reqs = self.requirements or {}
        conditional_params = reqs.get("conditional_params", {}) or {}
        if wallet_type == 'hd':
            return conditional_params.get('hd_only', []) or []
        elif wallet_type == 'iguana':
            return conditional_params.get('non_hd_only', []) or []
        # Return all conditional params if no specific type requested
        all_params: List[str] = []
        all_params.extend(conditional_params.get('hd_only', []) or [])
        all_params.extend(conditional_params.get('non_hd_only', []) or [])
        return all_params

    def get_prerequisite_methods(self) -> List[str]:
        # Prefer requirements.prerequisite_methods with fallback to top-level prerequisites
        reqs = self.requirements or {}
        prereq_methods = reqs.get('prerequisite_methods', []) or []
        if prereq_methods:
            return prereq_methods
        return self.prerequisites or []

    @staticmethod
    def _matches_example_pattern(example_key: str, environment: Optional[str] = None,
                                 hardware: Optional[str] = None,
                                 wallet_type: Optional[str] = None) -> bool:
        example_lower = example_key.lower()
        if 'trezor' in example_lower:
            return hardware == 'trezor' or hardware is None
        if 'native' in example_lower:
            return environment == 'native' or environment is None
        if 'wasm' in example_lower:
            return environment == 'wasm' or environment is None
        if 'hd' in example_lower and wallet_type is not None:
            return wallet_type == 'hd'
        if 'iguana' in example_lower and wallet_type is not None:
            return wallet_type == 'iguana'
        if any(pattern in example_lower for pattern in ['pin', 'passphrase']):
            return hardware == 'trezor' or hardware is None
        if any(pattern in example_lower for pattern in ['gap_limit', 'scan_policy', 'min_addresses', 'path_to_address']):
            return wallet_type == 'hd' or wallet_type is None
        return True

    def filter_examples(self, environment: Optional[str] = None,
                        hardware: Optional[str] = None,
                        wallet_type: Optional[str] = None) -> Dict[str, str]:
        # If no filtering requested, return all example descriptions
        all_examples = {ex.name: ex.description for ex in self.examples.values()}
        if environment is None and hardware is None and wallet_type is None:
            return all_examples
        # Method-level requirements checks
        method_requirements = self.requirements or {}
        if environment is not None:
            if environment not in (method_requirements.get('environments', []) or []):
                return {}
        if wallet_type is not None:
            if wallet_type not in (method_requirements.get('wallet_types', []) or []):
                return {}
        if hardware is not None:
            req_hw = method_requirements.get('hardware', []) or []
            if len(req_hw) > 0 and hardware not in req_hw:
                return {}
        # Example-specific requirements
        example_requirements = method_requirements.get('example_requirements', {}) or {}
        filtered: Dict[str, str] = {}
        for example_key, description in all_examples.items():
            ex_reqs = example_requirements.get(example_key, {}) or {}
            if hardware is not None:
                ex_hw = ex_reqs.get('hardware', []) or []
                if len(ex_hw) > 0 and hardware not in ex_hw:
                    continue
            if self._matches_example_pattern(example_key, environment, hardware, wallet_type):
                filtered[example_key] = description
        return filtered
    
    @property
    def is_activation_method(self) -> bool:
        """Check if this is an activation method."""
        activation_terms = ["enable", "activate", "init", "electrum"]
        return any(term in self.name.lower() for term in activation_terms)
    
    @property
    def is_wallet_method(self) -> bool:
        """Check if this is a wallet-related method."""
        wallet_terms = ["withdraw", "fetch_utxos", "consolidate", "balance"]
        return any(term in self.name.lower() for term in wallet_terms)
    
    @property
    def prerequisites_satisfied(self) -> bool:
        """Check if all prerequisites are satisfied."""
        return set(self.prerequisites).issubset(self.prerequisite_methods_completed)
    
    @property
    def can_process(self) -> bool:
        """Check if this method can be processed (prerequisites satisfied and not deprecated)."""
        return self.prerequisites_satisfied and not self.deprecated and self.status in [MethodStatus.PENDING, MethodStatus.PREREQUISITES_NEEDED]
    
    @property
    def has_examples(self) -> bool:
        """Check if this method has examples to process."""
        return len(self.examples) > 0
    
    @property
    def collected_examples_count(self) -> int:
        """Count of examples that have been collected."""
        return sum(1 for example in self.examples.values() if example.collected)
    
    @property
    def successful_examples_count(self) -> int:
        """Count of examples that completed successfully."""
        return sum(1 for example in self.examples.values() if example.is_successful)
    
    def mark_prerequisite_completed(self, prerequisite_method: str):
        """Mark a prerequisite method as completed."""
        self.prerequisite_methods_completed.add(prerequisite_method)
        
        # Update status if all prerequisites are now satisfied
        if self.prerequisites_satisfied and self.status == MethodStatus.PREREQUISITES_NEEDED:
            self.status = MethodStatus.PENDING
    
    def get_example(self, example_name: str) -> Optional[KdfExample]:
        """Get a specific example by name."""
        return self.examples.get(example_name)
    
    def add_example_response(self, example_name: str, response_data: Dict[str, Any], 
                           status_code: int = 200, instance_responses: Optional[Dict[str, Any]] = None):
        """Add response data to an example."""
        if example_name in self.examples:
            example = self.examples[example_name]
            example.response_data = response_data
            example.status_code = status_code
            if instance_responses:
                example.instance_responses = instance_responses
            example.collected = True
    
    def add_example_error(self, example_name: str, error_data: Dict[str, Any], 
                         instance_responses: Optional[Dict[str, Any]] = None):
        """Add error data to an example."""
        if example_name in self.examples:
            example = self.examples[example_name]
            example.error_data = error_data
            if instance_responses:
                example.instance_responses = instance_responses
            example.collected = True
    
    def __lt__(self, other: 'KdfMethod') -> bool:
        """Enable sorting by sequence, then alphabetically by name."""
        if self.sequence != other.sequence:
            return self.sequence < other.sequence
        return self.name < other.name


@dataclass
class MethodRequestQueue:
    """Queue for managing method processing order and prerequisites."""
    methods: Dict[str, KdfMethod] = field(default_factory=dict)
    completed_methods: Set[str] = field(default_factory=set)
    failed_methods: Set[str] = field(default_factory=set)
    
    def add_method(self, method: KdfMethod):
        """Add a method to the queue."""
        self.methods[method.name] = method
    
    def get_next_processable_method(self) -> Optional[KdfMethod]:
        """Get the next method that can be processed (lowest sequence, prerequisites satisfied)."""
        processable_methods = [
            method for method in self.methods.values()
            if method.can_process and method.name not in self.completed_methods
        ]
        
        if not processable_methods:
            return None
        
        # Sort by sequence, then alphabetically
        processable_methods.sort()
        return processable_methods[0]
    
    def mark_method_completed(self, method_name: str):
        """Mark a method as completed and update prerequisites for other methods."""
        if method_name in self.methods:
            self.methods[method_name].status = MethodStatus.COMPLETED
            
        self.completed_methods.add(method_name)
        
        # Update prerequisite status for all methods
        for method in self.methods.values():
            if method_name in method.prerequisites:
                method.mark_prerequisite_completed(method_name)
    
    def mark_method_failed(self, method_name: str, reason: str = ""):
        """Mark a method as failed."""
        if method_name in self.methods:
            self.methods[method_name].status = MethodStatus.FAILED
            
        self.failed_methods.add(method_name)
    
    def get_methods_needing_prerequisites(self) -> List[KdfMethod]:
        """Get methods that need prerequisites but haven't been marked as such."""
        return [
            method for method in self.methods.values()
            if not method.prerequisites_satisfied and method.status == MethodStatus.PENDING
        ]
    
    def update_prerequisite_status(self):
        """Update the status of methods based on their prerequisites."""
        for method in self.methods.values():
            if not method.prerequisites_satisfied and method.status == MethodStatus.PENDING:
                method.status = MethodStatus.PREREQUISITES_NEEDED
    
    @property
    def pending_count(self) -> int:
        """Count of methods still pending processing."""
        return len([m for m in self.methods.values() if m.status in [MethodStatus.PENDING, MethodStatus.PREREQUISITES_NEEDED]])
    
    @property
    def completed_count(self) -> int:
        """Count of completed methods."""
        return len(self.completed_methods)
    
    @property
    def failed_count(self) -> int:
        """Count of failed methods."""
        return len(self.failed_methods)


class KdfMethodsLoader:
    """Utility class for loading KDF methods from JSON files."""
    
    @staticmethod
    def load_from_files(workspace_root: Path) -> MethodRequestQueue:
        """Load all KDF methods from configuration and request files."""
        # Load method configurations separately and combine for queue creation
        data_dir = workspace_root / "src/data"
        v2_file = data_dir / "kdf_methods_v2.json"
        legacy_file = data_dir / "kdf_methods_legacy.json"

        methods_config = {}
        try:
            with open(legacy_file, 'r') as f:
                legacy_cfg = json.load(f)
                # Use unique method keys; if collisions exist, keep both by suffixing version for internal queue
                for name, cfg in legacy_cfg.items():
                    if name in methods_config:
                        methods_config[f"legacy::{name}"] = cfg
                    else:
                        methods_config[name] = cfg
        except FileNotFoundError:
            pass
        try:
            with open(v2_file, 'r') as f:
                v2_cfg = json.load(f)
                for name, cfg in v2_cfg.items():
                    if name in methods_config:
                        methods_config[f"v2::{name}"] = cfg
                    else:
                        methods_config[name] = cfg
        except FileNotFoundError:
            pass
        # Do not fallback to single file; expect split files present
        
        # Load request examples from all request files
        all_request_examples = {}
        request_dirs = [
            workspace_root / "src/data/requests/kdf/v2",
            workspace_root / "src/data/requests/kdf/legacy"
        ]
        
        for request_dir in request_dirs:
            if request_dir.exists():
                for request_file in request_dir.glob("*.json"):
                    with open(request_file, 'r') as f:
                        request_data = json.load(f)
                        all_request_examples.update(request_data)
        
        # Create method queue
        queue = MethodRequestQueue()
        
        # Create KdfMethod objects
        for method_name, method_config in methods_config.items():
            method = KdfMethod.from_json(method_name, method_config, all_request_examples)
            queue.add_method(method)
        
        # Update prerequisite status
        queue.update_prerequisite_status()
        
        return queue


# -------- Generic request parsing helpers (centralized for reuse) --------

def extract_method_from_request(request_data: Dict[str, Any]) -> Optional[str]:
    """Extract the method name from a request object."""
    if isinstance(request_data, dict) and 'method' in request_data:
        return request_data['method']
    return None

def extract_ticker_from_request(request_data: Dict[str, Any]) -> Optional[str]:
    """Extract the ticker symbol from a request object."""
    if isinstance(request_data, dict):
        # Look for ticker in params
        params = request_data.get('params')
        if isinstance(params, dict):
            if 'ticker' in params:
                return params['ticker']
            if 'coin' in params:
                return params['coin']
        # Look for ticker in other common locations
        if 'ticker' in request_data:
            return request_data['ticker']
        if 'coin' in request_data:
            return request_data['coin']
    return None
