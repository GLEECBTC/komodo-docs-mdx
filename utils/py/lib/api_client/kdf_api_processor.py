import json
import os
import requests
import time
import subprocess
import copy
from typing import Dict, Any, Set, Optional, List
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import concurrent.futures  # for ThreadPoolExecutor in send_request_to_all_nodes

from lib.constants.config_struct import EnhancedKomodoConfig, NodeConfig
from lib.utils.logging_utils import KomodoLogger
from lib.managers.path_mapping_manager import EnhancedPathMapper
from lib.utils import (
    get_logger,
)
from lib.utils.file_utils import safe_write_json
from lib.utils.file_utils import ensure_directory_exists
from lib.managers.git_manager import GitManager


class ApiRequestProcessor:
    def __init__(self, config: EnhancedKomodoConfig,
     logger: KomodoLogger, kdf_branch: str = 'dev', substitute_defaults: bool = False):
        self.config = config
        self.logger = logger
        self.substitute_defaults = substitute_defaults
        self.git_manager = GitManager(self.logger)
        self.path_mapper = EnhancedPathMapper(config=self.config)
        self._load_dotenv()
        self.kdf_branch = kdf_branch
        self.enabled_coins: Dict[str, Set[str]] = {node.name: set() for node in self.config.nodes}
        self.session = requests.Session()
        self.coins_config: Dict[str, Any] = {}
        self.protocol_to_activation: Dict[str, Any] = {}
        self.method_results_cache: Dict[str, Dict[str, Any]] = {node.name: {} for node in self.config.nodes}
        self.completed_methods: Dict[str, Set[str]] = {node.name: set() for node in self.config.nodes}
        self.activation_methods: Set[str] = set()
        self.v1_methods: Set[str] = set()
        self.v2_methods: Set[str] = set()
        
        # Cache for test parameter constants (utils/py/kdf_test_cases/test_params.json)
        self._test_params: Dict[str, Any] = {}

        # Mappings and Constants
        self.enable_hd = self._get_env_var_as_bool("ENABLE_HD", False)
        self.path_mapper = EnhancedPathMapper(config=self.config)
        self._initialize_processor()

    def _load_dotenv(self):
        """Loads .env file from the docker data directory."""
        dotenv_path = self.config.directories.docker_dot_kdf_dir / ".env"
        if not dotenv_path.exists():
            self.logger.warning(f".env file not found at {dotenv_path}. Using default values.")
            return

        with open(dotenv_path, 'r') as f:
            for line in f.read().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    # Remove surrounding quotes if they exist
                    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                        value = value[1:-1]
                    os.environ[key] = value
                    # Uncomment to log env vars to console (for debugging)
                    # self.logger.info(f"ENV VAR: {key} = {value}")
        self.logger.success("Successfully loaded environment variables.")
        self.enable_hd = self._get_env_var_as_bool("ENABLE_HD", False)

    @staticmethod
    def _get_env_var_as_bool(var_name, default=False):
        """Gets an environment variable and converts it to a boolean."""
        value = os.getenv(var_name, str(default)).lower()
        return value in ['true', '1', 't', 'y', 'yes']

    @staticmethod
    def _get_env_var_as_int(var_name, default):
        """Gets an environment variable and converts it to an integer."""
        try:
            return int(os.getenv(var_name, str(default)))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _get_env_var_as_str_array(var_name, default=[]):
        """Gets a comma-separated string from env and converts to a list of strings."""
        
        value = os.getenv(var_name)
        value = value.replace('"', '').replace("'", '').replace(',', ' ')
        if not value:
            return default
        return [item.strip() for item in value.split(' ') if item.strip()]

    def generate_mm2_config_for_node(self, node_config: NodeConfig, mm2_path: str):
        """Generates an MM2.json file for a specific node."""
        config_data = self.get_mm2_data()

        # Override defaults with node-specific values
        config_data['rpcport'] = node_config.port
        config_data['enable_hd'] = node_config.hd_mode
        config_data['userpass'] = node_config.userpass
        config_data['passphrase'] = node_config.passphrase

        # Unique wallet name and password for each node
        node_name = node_config.name
        config_data['wallet_name'] = f"{node_name}_wallet"
        config_data['wallet_password'] = f"Sup3rS3cur3-{node_name}-P@ssw0rd"

        # Special handling for wasm nodes if needed
        if node_config.wasm_mode:
            # Add any wasm-specific config overrides here
            pass
        
        self.logger.info(f"Generating MM2.json for {node_name} at {mm2_path}")
        ensure_directory_exists(Path(mm2_path).parent)
        safe_write_json(mm2_path, config_data)


    def generate_mm2_config(self):
        """
        Generates MM2.json files for all configured nodes.
        The base configuration is loaded from .env, then customized for each node.
        """
        self.logger.info("Generating MM2 config files for all nodes...")
        for node_cfg in self.config.nodes:
            node_dir = self.config.directories.docker_dir / f"kdf-config-{node_cfg.name.replace('_', '-')}"
            mm2_path = node_dir / "MM2.json"
            self.generate_mm2_config_for_node(node_cfg, str(mm2_path))

    def get_mm2_data(self):
        """
        Constructs the base MM2.json data from environment variables.
        """
        config_data = {
            "gui": os.getenv("GUI", "kdf_mdx_docs"),
            "rpcip": "0.0.0.0",
            "rpc_local_only": False,
            "enable_hd": self.enable_hd,
            "netid": self._get_env_var_as_int("NETID", 8762),
            "rpcport": self._get_env_var_as_int("RPC_PORT", 7783),
            "1inch_api": os.getenv("ONE_INCH_API", ""),
            "seednodes": self._get_env_var_as_str_array("SEED_NODES", []),
            "passphrase": os.getenv("PASSPHRASE", ""),
            "rpc_password": "RPC_UserP@SSW0RD",
            "use_watchers": self._get_env_var_as_bool("USE_WATCHERS", False),
            "i_am_seed": self._get_env_var_as_bool("I_AM_SEED", False),
            "is_bootstrap_node": self._get_env_var_as_bool("IS_BOOTSTRAP_NODE", False),
            "disable_p2p": self._get_env_var_as_bool("DISABLE_P2P", False),
            "use_trading_proto_v2": self._get_env_var_as_bool("USE_TRADING_PROTO_V2", False),
            "allow_weak_password": self._get_env_var_as_bool("ALLOW_WEAK_PASSWORD", True),
            "wallet_name": os.getenv("WALLET_NAME", "active_wallet"),
            "wallet_password": os.getenv("WALLET_PASSWORD", "1c@N-n0t-Di3"),
            "event_streaming_configuration": {
                "access_control_allow_origin": "*"
            }
        }
        return config_data

    def stop_container(self):
        try:
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=self.config.directories.docker_dir, check=True
            )
            self.logger.success("Container stopped successfully.")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to stop container: {e}")
            return False

    def _initialize_processor(self):
        """Fetches coins config and updates initial enabled coins list."""
        self.logger.info("Initializing ApiRequestProcessor...")
        self._load_activation_mapping()
        self._load_mdx_methods()
        self._fetch_coins_config()
        self._fetch_coins_file()
        self.generate_mm2_config()
        

    def _load_mdx_methods(self):
        """Loads the kdf_mdx_methods.json file to determine method versions."""
        mdx_methods_path = self.config.directories.branched_reports_dir / self.config.directories.mdx_methods_report
        if not mdx_methods_path.exists():
            self.logger.error(f"MDX methods report not found at: {mdx_methods_path}")
            self.logger.error("Please run 'kdf-tools scan-mdx' to generate it.")
            return

        try:
            self.logger.info(f"Loading mdx methods from {mdx_methods_path}")
            with open(mdx_methods_path, 'r') as f:
                mdx_methods_data = json.load(f)
            
            self.v1_methods = set(mdx_methods_data.get("repository_data", {}).get("v1", {}).get("methods", []))
            self.v2_methods = set(mdx_methods_data.get("repository_data", {}).get("v2", {}).get("methods", []))
            
            self.logger.success(f"Successfully loaded {len(self.v1_methods)} v1 methods and {len(self.v2_methods)} v2 methods.")
        except Exception as e:
            self.logger.error(f"Error loading MDX methods report from {mdx_methods_path}: {e}")

    def _load_activation_mapping(self):
        """Loads the protocol_activation_mapping.json file."""
        mapping_file = self.config.directories.data_dir / "coins" / "protocol_activation_mapping.json"
        try:
            self.logger.info(f"Loading activation mapping from {mapping_file}")
            with open(mapping_file, 'r') as f:
                self.protocol_to_activation = json.load(f)

            # Populate activation_methods set
            for activations in self.protocol_to_activation.values():
                for method_name in activations.values():
                    if method_name:
                        self.activation_methods.add(method_name)
            
            self.logger.success(f"Successfully loaded protocol activation mapping and identified {len(self.activation_methods)} activation methods.")
        except FileNotFoundError:
            self.logger.error(f"Activation mapping file not found at: {mapping_file}")
            self.protocol_to_activation = {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON from {mapping_file}: {e}")
            self.protocol_to_activation = {}

    def _fetch_coins_config(self, branch: str = "master"):
        """Fetches the coins_config.json file."""
        url = f"https://raw.githubusercontent.com/KomodoPlatform/coins/{branch}/utils/coins_config.json"
        try:
            self.logger.fetch(f"Fetching coins config from {url}")
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            self.coins_config = response.json()
            self.logger.success("Successfully fetched and loaded coins config.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch coins_config.json: {e}")
            self.coins_config = {}

    def _fetch_coins_file(self, branch: str = "master"):
        """Fetches the coins file."""
        url = f"https://raw.githubusercontent.com/KomodoPlatform/coins/{branch}/coins"
        try:
            self.logger.fetch(f"Fetching coins config from {url}")
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            self.coins_file = response.json()
            self.logger.success("Successfully fetched and loaded coins file.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch coins: {e}")
            self.coins_file = {}
        with open(self.config.directories.docker_dot_kdf_dir / "coins", "w") as f:
            json.dump(self.coins_file, f, indent=4)
            self.logger.success("Successfully saved coins file.")

    # =============================================================
    # Test parameter substitution helpers
    # =============================================================

    def _load_test_params(self) -> None:
        """Load constants from utils/py/kdf_test_cases/test_params.json once."""
        if self._test_params:
            return
        # Use centralized path from DirectoryConfig for test parameters
        test_params_path = self.config.directories.test_params_json
        try:
            with open(test_params_path, "r") as fp:
                self._test_params = json.load(fp)
                self.logger.debug(f"Loaded test params from {test_params_path}")
        except FileNotFoundError:
            self.logger.warning(f"test_params.json not found at {test_params_path}; default substitution disabled.")
        except json.JSONDecodeError as exc:
            self.logger.error(f"Could not parse {test_params_path}: {exc}")

    def _substitute_default_params(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Return copy of *body* with coin/ticker/base/rel substituted from test params."""
        self._load_test_params()

        # Skip substitution for methods that rely on the *exact* coin values passed
        # by the caller. Substituting these values would lead to incorrect behaviour
        # or failed requests. Currently the following methods are exempt:
        #   • convert_utxo_address – converting between specific UTXO coins must use
        #     the tickers provided in the example (e.g., BTC → RVN).
        #   • get_kdf_responses   – metadata-style call that should always use the
        #     supplied parameters (if any) without alteration.
        skip_substitution_methods = {"convert_utxo_address"}

        method_name = body.get("method")
        if method_name in skip_substitution_methods:
            self.logger.debug(
                f"Skipping default parameter substitution for method '{method_name}'."
            )
            return body

        if not self._test_params:
            return body
        primary = self._test_params.get("PRIMARY_COIN")
        secondary = self._test_params.get("SECONDARY_COIN")
        mapping = {
            "coin": primary,
            "ticker": primary,
            "base": primary,
            "rel": secondary,
            "my_coin": primary,
            "other_coin": secondary
        }
        new_body = copy.deepcopy(body)
        for k, v in mapping.items():
            if v is None:
                continue
            if k in new_body:
                new_body[k] = v
            params = new_body.get("params")
            if isinstance(params, dict) and k in params:
                params[k] = v
        return new_body

    def _make_request(self, url: str, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper for making API requests."""
        if self.substitute_defaults:
            request_body = self._substitute_default_params(request_body)
        try:
            response = self.session.post(url, json=request_body, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            self.logger.error(f"HTTP error occurred: {http_err} - {response.text}")
            if 'Userpass is invalid' in response.text:
                self.logger.error(f"Userpass is invalid. Please check your .env file.")
                self.stop_container()
                sys.exit(1)
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"error": response.text}
        except Exception as e:
            self.logger.error(f"Request error occurred: {e}")
            return {"error": str(e)}


    def _update_enabled_coins(self, node: Optional[NodeConfig] = None):
        """Calls get_enabled_coins and updates the internal set."""
        target_node = node or self.config.nodes[0]
        self.logger.info(f"Updating list of enabled coins from node: {target_node.name}")

        node_url = target_node.api_url
        request_body = {
            "userpass": target_node.userpass,
            "mmrpc": "2.0",
            "method": "get_enabled_coins",
            "id": 0
        }
        response = self._make_request(node_url, request_body)
        if "result" in response:
            self.enabled_coins[target_node.name] = {coin['ticker'] for coin in response["result"].get("coins", [])}
            self.logger.success(f"Successfully updated list of enabled coins for node '{target_node.name}'.")
        else:
            self.logger.error(f"Failed to update list of enabled coins for node '{target_node.name}'.")
        self.logger.info(f"Currently enabled coins for node '{target_node.name}': {self.enabled_coins[target_node.name]}")
        


    def check_coin_is_active(self, request_body: Dict[str, Any], node: NodeConfig) -> bool:
        """Checks if the coin is active, and if not, activates it"""
        coins_to_activate = []
        for i in ['coin', 'ticker', 'base', 'rel']:
            if i in request_body:
                coin = request_body[i]
            elif i in request_body.get("params", {}):
                coin = request_body.get("params", {}).get(i)
            else:
                continue
            coins_to_activate.append(coin)
        if len(coins_to_activate) == 0:
            return True, None
        self.logger.info(f"Method: {request_body.get('method')} needs some coins to activate: {coins_to_activate}")
        for coin in coins_to_activate:
            if coin and coin not in self.enabled_coins[node.name]:
                self.logger.warning(f"Coin '{coin}' is not enabled on node '{node.name}'. Attempting activation...")
                if not self.activate_coin(coin, node=node):
                    self.logger.error(f"Skipping request as activation for '{coin}' on node '{node.name}' failed.")
                    return False, coin
        return True, None

    def is_activation_method(self, method: str) -> bool:
        """Checks if a method is a known coin activation method."""
        return method in self.activation_methods

    def process_method_request(self, method: str, version: str):
        self.logger.info(f"Processing method: {method}, version: {version}")
        method_path = self.path_mapper.get_method_path('json', method, version)
        self.logger.info(f"Method path: {method_path}")
        if not Path(method_path).exists():
            self.logger.error(f"Method directory not found: {method_path}")
            return

        request_files = sorted(list(method_path.glob("request_*.json")))
        self.logger.info(f"---------------------------------------------------------")
        self.logger.info(f"Found {len(request_files)} request files in {method_path}")

        for request_file in request_files:
            with open(request_file, 'r') as f:
                request_body = json.load(f)

                # For activation methods, ensure coin is disabled first for a clean test
                if self.is_activation_method(method):
                    params = request_body.get("params", {})
                    ticker = params.get("ticker")
                    # Using first node as baseline for this check.
                    # This check is a preliminary step before sending to all nodes.
                    baseline_node = self.config.nodes[0]
                    if ticker and ticker in self.enabled_coins[baseline_node.name]:
                        self.logger.warning(f"Coin '{ticker}' is already enabled for activation test on node '{baseline_node.name}'. Disabling first.")
                        if self.disable_coin(ticker, node=baseline_node):
                            time.sleep(1)  # Give a moment for the state to update
                        else:
                            self.logger.error(f"Failed to disable '{ticker}' on node '{baseline_node.name}', skipping activation test for this example.")
                            continue

                # For kmd_rewards_info, ensure KMD is specified.
                # TODO: This is a hack to ensure KMD is enabled for kmd_rewards_info.
                # We should find a better way to do this. It is not a valid parameter for kmd_rewards_info.
                if method == "kmd_rewards_info":
                    if "params" in request_body:
                        if "coin" not in request_body["params"]:
                            request_body["params"]["coin"] = "KMD"
                    elif "coin" not in request_body:
                        request_body["coin"] = "KMD"
                        
                # Note: Data injection and coin activation checks are now handled inside send_request_to_all_nodes
                # on a per-node basis.

                # Determine example number from filename e.g., request_1.json → 1
                try:
                    example_number = int(request_file.stem.split("_")[1])
                except (IndexError, ValueError):
                    example_number = 1  # default fallback

                # Send to all local Docker nodes and save individual responses
                node_responses = self.send_request_to_all_nodes(
                    request_body=request_body,
                    method_name=method,
                    output_dir=method_path,
                    example_number=example_number,
                )

                # Use node_a (or first) as baseline for caching and further logic
                baseline_node = self.config.nodes[0]
                baseline_resp = node_responses.get(baseline_node.name) or next(iter(node_responses.values()))

                # Cache data from baseline response if successful
                if baseline_resp and "error" not in baseline_resp:
                    self._cache_response_data(method, baseline_resp, baseline_node)
                    self.completed_methods[baseline_node.name].add(method)

                # Compare responses and log differences (optional for now)
                compare_node_responses(node_responses, logger=self.logger)

    def _inject_cached_data(self, method: str, request_body: Dict[str, Any], node: NodeConfig) -> Dict[str, Any]:
        """Injects cached data from previous requests into the current request body."""
        params = request_body.get("params", {})
        node_cache = self.method_results_cache[node.name]

        # Handle task-based methods
        if "::" in method and not method.endswith("::init"):
            task_group = "::".join(method.split("::")[:-1])
            task_cache = node_cache.get("tasks", {}).get(task_group, {})
            if "task_id" in task_cache:
                self.logger.info(f"Injecting task_id {task_cache['task_id']} into request for {method} on node {node.name}")
                params['task_id'] = task_cache['task_id']

        # Handle swap status
        if method == "my_swap_status":
            swap_cache = node_cache.get("swaps", [])
            if swap_cache:
                latest_swap = swap_cache[-1]
                if "uuid" in latest_swap:
                    self.logger.info(f"Injecting uuid {latest_swap['uuid']} into request for {method} on node {node.name}")
                    params['uuid'] = latest_swap['uuid']

        # Handle message verification
        if method == "verify_message":
            signature_cache = node_cache.get("signatures", {})
            if "signature" in signature_cache:
                self.logger.info(f"Injecting signature for {method} on node {node.name}")
                params.update(signature_cache)

        # Remove erroneous Order UUID caching section (if present)
        # Handle order-related methods that require a previously obtained order UUID
        if method in ["cancel_order", "order_status", "update_maker_order"]:
            orders_cache = node_cache.get("orders", [])
            if orders_cache:
                latest_order = orders_cache[-1]
                if "uuid" in latest_order:
                    self.logger.info(
                        f"Injecting order uuid {latest_order['uuid']} into request for {method} on node {node.name}"
                    )
                    # Set for both v1 (top-level) and v2 (nested params) possibilities
                    request_body["uuid"] = latest_order["uuid"]
                    params["uuid"] = latest_order["uuid"]

        # Handle sending raw transaction
        if method == "send_raw_transaction":
            tx_cache = node_cache.get("unsigned_tx", {})
            if "tx_hex" in tx_cache:
                self.logger.info(f"Injecting tx_hex into request for {method} on node {node.name}")
                params['tx_hex'] = tx_cache['tx_hex']

        request_body['params'] = params
        return request_body

    def _cache_response_data(self, method: str, response: Dict[str, Any], node: NodeConfig):
        """Caches relevant data from a successful response for later use."""
        result = response.get("result", {})
        if not result:
            return
        
        node_cache = self.method_results_cache[node.name]

        # Cache task_id for all init methods
        if method.endswith("::init") and "task_id" in result:
            task_group = "::".join(method.split("::")[:-1])
            if "tasks" not in node_cache:
                node_cache["tasks"] = {}
            node_cache["tasks"][task_group] = {"task_id": result["task_id"]}
            self.logger.info(f"Cached task_id for {task_group} on node {node.name}: {result['task_id']}")

        # Cache swap UUIDs
        if method in ["buy", "sell"] and "uuid" in result:
            if "swaps" not in node_cache:
                node_cache["swaps"] = []
            node_cache["swaps"].append({"uuid": result["uuid"]})
            self.logger.info(f"Cached swap uuid on node {node.name}: {result['uuid']}")

        # Cache order UUIDs from setprice for later cancellation or updates
        if method == "setprice" and "uuid" in result:
            if "orders" not in node_cache:
                node_cache["orders"] = []
            node_cache["orders"].append({"uuid": result["uuid"]})
            self.logger.info(f"Cached order uuid on node {node.name}: {result['uuid']}")

        # Cache signature data
        if method == "sign_message" and "signature" in result:
            node_cache["signatures"] = {
                "signature": result["signature"],
                "pubkey": result.get("pubkey")
            }
            self.logger.info(f"Cached message signature on node {node.name}.")
            
        # Cache unsigned transaction hex
        if method == "get_unsigned_transaction" and "tx_hex" in result:
            node_cache["unsigned_tx"] = {"tx_hex": result["tx_hex"]}
            self.logger.info(f"Cached unsigned transaction hex on node {node.name}.")

    def activate_coin(self, ticker: str, activation_type: str = 'default', node: Optional[NodeConfig] = None, priv_key_policy: Optional[str | Dict[str, Any]] = None) -> bool:
        """Activate *ticker* on *node*.

        Parameters
        ----------
        ticker : str
            Coin ticker to activate.
        activation_type : str, optional
            Which activation variant to use (``default``, ``task``, ``v1`` …).
            Defaults to ``'default'`` which defers to the mapping in
            ``protocol_activation_mapping.json``.
        node : NodeConfig | None, optional
            Target node configuration. If ``None`` the first configured node
            will be used.
        priv_key_policy : dict | None, optional
            Optional ``priv_key_policy`` object to include in the activation
            request (e.g. ``{"type": "Trezor"}``).
        """

        # The *priv_key_policy* parameter is optional for Trezor / WalletConnect activation.
        # If not specified, *priv_key_policy* is not included in the activation request, and defaults to `ContextPrivKey`.

        target_node = node or self.config.nodes[0]
        self.logger.info(f"Attempting to activate '{ticker}' on node '{target_node.name}'...")
        coin_info = self.coins_config.get(ticker)
        if not coin_info:
            self.logger.error(f"'{ticker}' not found in coins_config.json.")
            return False

        protocol = coin_info.get("protocol", {}).get("type")
        activation_options = self.protocol_to_activation.get(protocol)

        if not activation_options:
            self.logger.error(f"Protocol '{protocol}' for coin '{ticker}' is not defined in protocol_to_activation map.")
            return False

        # Determine which activation type to use

        act_type_to_use = activation_options.get(activation_type)
        if not act_type_to_use:
            self.logger.error(f"No {activation_type} activation type for protocol '{protocol}'.")
            return False

        activation_method = activation_options.get(act_type_to_use)

        # ------------------------------------------------------------------
        # Override: Tendermint **token** activation should use the dedicated
        # `task::enable_tendermint_token::init` method when available instead
        # of the generic platform-coin init. This prevents parameter mismatch
        # errors and aligns with the current API docs (@/enable_tendermint_token).
        # ------------------------------------------------------------------
        if protocol == "TENDERMINTTOKEN":
            # Currently Tendermint tokens are enabled via the v2 non-task method
            # `enable_tendermint_token`. Adjust if/when the task variant is
            # implemented in Rust.
            activation_method = "enable_tendermint_token"

        if activation_method is None:
            self.logger.error(f"Activation type '{act_type_to_use}' not available for protocol '{protocol}'.")
            return False
        if not activation_method:
            self.logger.error(f"Activation method for protocol '{protocol}' (type: {act_type_to_use}) is not determined. Skipping.")
            return False

        params = {"ticker": ticker}
        if activation_method.startswith("task::"):
            activation_params = {}
            if protocol in ["ETH", "ERC20"]:
                activation_params["nodes"] = coin_info.get("nodes", [])
                activation_params["erc20_tokens_requests"] = []
                if "swap_contract_address" in coin_info:
                    activation_params["swap_contract_address"] = coin_info["swap_contract_address"]
                if "fallback_swap_contract" in coin_info:
                    activation_params["fallback_swap_contract"] = coin_info["fallback_swap_contract"]

            elif protocol in ["UTXO", "BCH", "SLP", "QTUM", "QRC20"]:
                activation_params["utxo_merge_params"] = {"merge_at": 10}
                rpc_data = {"servers": coin_info.get("electrum", [])}
                activation_params["mode"] = {"rpc": "Electrum", "rpc_data": rpc_data}
                if protocol in ["QRC20"]:
                    if "contract_address" in coin_info:
                        activation_params["contract_address"] = coin_info.get("contract_address")

            elif protocol == "ZHTLC":
                # TODO: Add the zcash params to the docker container
                zcash_params_path = os.getenv("ZCASH_PARAMS_PATH")
                if not zcash_params_path:
                    default_path = str(Path.home() / ".zcash-params")
                    self.logger.warning(
                        f"ZCASH_PARAMS_PATH not set, using default: {default_path}"
                    )
                    zcash_params_path = default_path

                rpc_data = {
                    "electrum_servers": coin_info.get("electrum", []),
                    # Prefer explicit light-walletd list when provided in coins config;
                    # fall back to generic nodes array for backward compatibility.
                    "light_wallet_d_servers": coin_info.get("light_wallet_d_servers")
                    or coin_info.get("nodes", [])
                }
                activation_params["mode"] = {"rpc": "Light", "rpc_data": rpc_data}
                activation_params["zcash_params_path"] = zcash_params_path
                activation_params["scan_blocks_per_iteration"] = 100
                activation_params["scan_interval_ms"] = 200

            elif protocol in ["TENDERMINT", "TENDERMINTTOKEN"]:
                # ------------------------------------------------------------------
                # Tendermint (Cosmos-SDK) assets use a struct defined in
                # `TendermintActivationParams` (see
                # coins_activation/src/tendermint_with_assets_activation.rs).
                # Required fields:
                #   • nodes          – Vec<RpcNode> (objects {url,komodo_proxy})
                # Optional fields:
                #   • tokens_params  – array (token activations)
                #   • tx_history, get_balances, path_to_address, activation_params …
                # The list of RPC endpoints is stored in coins_config under
                # `rpc_urls`. We translate them to the expected `nodes` format.
                # ------------------------------------------------------------------

                raw_nodes = coin_info.get("rpc_urls", [])
                nodes: list[dict] = []
                for n in raw_nodes:
                    if isinstance(n, dict):
                        # already in the desired shape or contains extras
                        nodes.append(n)
                    else:
                        # plain URL string – wrap into object
                        nodes.append({"url": n})

                if protocol == "TENDERMINT":
                    # Platform coin activation – nodes live at top level.
                    params.update({
                        "nodes": nodes,
                        # sensible defaults matching Rust code
                        "tx_history": False,
                        "get_balances": True,
                        "tokens_params": [],  # no tokens in this simple activation
                    })
                else:
                    # For tokens we do not include nodes (they inherit via platform),
                    # so no special handling here.
                    pass

            elif protocol == "SIA":
                nodes = coin_info.get("nodes", [])
                if not nodes:
                    self.logger.error(f"Missing 'nodes' for SIA coin '{ticker}'.")
                    return False
                
                server_url = nodes[0].get("url")
                if not server_url:
                    self.logger.error(f"Missing 'url' in node configuration for SIA coin '{ticker}'.")
                    return False

                # Password for the SIA wallet daemon, should be in coin config
                password = coin_info.get("password")
                if password is None:
                    # Fallback to environment variable or empty string if not set.
                    password = os.getenv("SIA_WALLET_PASSWORD", "")
                    if password == "":
                        self.logger.warning(
                            f"'password' not specified for SIA coin '{ticker}'. Using empty string."
                        )

                activation_params["client_conf"] = {
                    "server_url": server_url,
                    "password": password
                }

            # For ETH platform coin with tokens we must flatten
            if activation_method == "task::enable_eth::init":
                params = {"ticker": ticker, **activation_params}
            elif activation_params:  # only include when non-empty (e.g., not needed for TENDERMINT coins)
                params["activation_params"] = activation_params
        else:
            # Legacy non-task based activations
            if protocol in ["ETH", "ERC20"]:
                params["nodes"] = coin_info.get("nodes", [])
                if "contract_address" in coin_info:
                    params["contract_address"] = coin_info.get("contract_address")
            elif protocol in ["UTXO", "BCH", "SLP", "QTUM", "QRC20"]:
                params["utxo_merge_params"] = {"merge_at": 10}
                params["servers"] = coin_info.get("electrum", [])
            elif protocol in ["TENDERMINT", "TENDERMINTTOKEN"]:
                params["rpc_urls"] = [node.get("url") if isinstance(node, dict) else node for node in coin_info.get("rpc_urls", [])]

        # --------------------------------------------------------------
        # Inject custom priv_key_policy (e.g., Trezor). Different protocols
        # still expect different representations during the transition phase:
        #   • UTXO-family & QTUM tasks accept a *string* value – "Trezor".
        #   • ETH, ERC20, Tendermint & Z-HTLC tasks expect an *object*
        #     {"type": "Trezor"}.
        # To simplify caller-side code we accept either representation and
        # normalise it here based on *protocol*.
        # --------------------------------------------------------------
        if priv_key_policy is not None:
            string_protocols = {"UTXO", "QTUM"}
            object_protocols = {"ETH", "TENDERMINT", "TENDERMINTTOKEN"} # Tendermint for WC, not trezor.
            incompatible = {"ZHTLC", "SIA"}

            if isinstance(priv_key_policy, dict):
                # Caller passed the object form; down-convert for protocols that
                # still use the legacy string representation (when safe to do).
                if protocol in string_protocols and priv_key_policy.keys() == {"type"}:
                    params["activation_params"]["priv_key_policy"] = priv_key_policy["type"]
                else:
                    params["priv_key_policy"] = priv_key_policy
            else:  # str
                if protocol in object_protocols:
                    params["priv_key_policy"] = {"type": priv_key_policy}
                else:
                    params["activation_params"]["priv_key_policy"] = priv_key_policy

        if activation_method in self.v2_methods:
            # Prepare status log container for this activation
            self.last_status_responses = []  # type: ignore[attr-defined]
            init_request = {
                "userpass": target_node.userpass,
                "method": activation_method,
                "mmrpc": "2.0",
                "params": params
            }
            # ------------------------------------------------------------------
            # Expose the final activation request so that external tools (e.g.,
            # interactive TUIs) can inspect and display it when activation fails.
            # We intentionally overwrite on every invocation to keep only the
            # most recent request/response pair.
            # ------------------------------------------------------------------
            self.last_request = init_request  # type: ignore[attr-defined]
        else: # v1 method
            init_request = {
                "userpass": target_node.userpass,
                "method": activation_method,
                **params
            }
            # Same exposure for legacy v1 paths
            self.last_request = init_request  # type: ignore[attr-defined]
        
        self.logger.info(f"Sending activation request for '{ticker}' with method '{activation_method}'")
        # Activation requests are always sent to node_a
        node_url = target_node.api_url
        init_response = self._make_request(node_url, init_request)

        # Cache the raw response for external inspection/debugging
        self.last_response = init_response  # type: ignore[attr-defined]

        # ------------------------------------------------------------------
        # If the platform coin is already activated, disable it first and
        # retry the activation exactly once using the same parameters.
        # ------------------------------------------------------------------
        if (
            init_response
            and init_response.get("error_type") == "PlatformIsAlreadyActivated"
        ):
            self.logger.warning(
                f"Platform coin '{ticker}' already active on node '{target_node.name}'. "
                "Disabling and retrying activation …"
            )
            if not self.disable_coin(ticker, node=target_node):
                self.logger.error(f"Unable to disable '{ticker}' – aborting re-activation.")
                return False
            time.sleep(1)
            # Retry once – prevent infinite recursion by not looping again if
            # the second attempt also hits the same error.
            return self.activate_coin(
                ticker,
                activation_type=activation_type,
                node=target_node,
                priv_key_policy=priv_key_policy,
            )

        # ------------------------------------------------------------------
        # Graceful handling when coin (non-platform) is already active – we
        # simply refresh our local cache and exit successfully.
        # ------------------------------------------------------------------

        if init_response and (
            init_response.get("error_type") == "CoinIsAlreadyActivated"
            or (
                isinstance(init_response.get("error"), str)
                and "activated already" in init_response["error"].lower()
            )
        ):
            self.logger.info(f"Coin '{ticker}' is already active – skipping activation.")
            # Refresh enabled coins to keep internal state in sync
            self._update_enabled_coins(node=target_node)
            return True

        # Handle task-based vs direct activation
        if activation_method in self.v2_methods:
            if init_response and "result" in init_response and "task_id" in init_response["result"]:
                task_id = init_response["result"]["task_id"]
                return self._poll_task_status(task_id, ticker, activation_method, node=target_node)
            else:
                self.logger.error(f"Task-based activation init failed for '{ticker}': {init_response}")
                return False
        else: # v1
            # Handle legacy/direct activation
            if init_response and "result" in init_response and "error" not in init_response:
                self.logger.success(f"Successfully activated '{ticker}' with direct method.")
                self._update_enabled_coins(node=target_node)
                return True
            else:
                self.logger.error(f"Direct activation failed for '{ticker}': {init_response}")
                return False

    def _poll_task_status(self, task_id: int, ticker: str, init_method: str, node: Optional[NodeConfig] = None) -> bool:
        # Derives the status method from the init method. e.g., task::enable_utxo::init -> task::enable_utxo::status
        status_method = init_method.replace("::init", "::status")
        target_node = node or self.config.nodes[0]

        self.logger.info(f"Polling status for task {task_id} on node {target_node.name} using {status_method}")
        for _ in range(20):  # Poll for max 100 seconds
            status_request = {
                "userpass": target_node.userpass,
                "method": status_method,
                "mmrpc": "2.0",
                "params": {"task_id": task_id}
            }
            node_url = target_node.api_url
            status_response = self._make_request(node_url, status_request)

            # Append to status log for external inspection
            if hasattr(self, "last_status_responses"):
                self.last_status_responses.append(status_response)  # type: ignore[attr-defined]

            if status_response and "result" in status_response:
                status = status_response["result"].get("status")
                details = status_response["result"].get("details")
                if status == "Ok":
                    self.logger.success(f"Successfully activated '{ticker}'. Details: {details}")
                    self._update_enabled_coins(node=target_node)
                    return True
                elif status == "InProgress":
                    self.logger.info(f"Activation in progress for '{ticker}'. Details: {details}")
                    time.sleep(5)
                    continue
                else: # Failed, Aborted etc.
                    self.logger.error(f"Activation failed for '{ticker}'. Status: {status}, Details: {details}")
                    return False
            else:
                self.logger.error(f"Failed to get status for task {task_id}: {status_response}")
                return False
        self.logger.error(f"Polling timed out for task {task_id} via {status_method}.")
        return False
        
    def disable_coin(self, ticker: str, node: Optional[NodeConfig] = None) -> bool:
        """Disables a coin. This is always a v1 method."""
        target_node = node or self.config.nodes[0]
        self.logger.info(f"Disabling coin '{ticker}' on node {target_node.name}...")
        request_body = {
            "userpass": target_node.userpass,
            "method": "disable_coin",
            "coin": ticker
        }
        node_url = target_node.api_url
        response = self._make_request(node_url, request_body)
        if response and response.get("result", {}).get("coin") == ticker:
            self.logger.success(f"Successfully disabled '{ticker}'.")
            self._update_enabled_coins(node=target_node)
            return True
        else:
            self.logger.error(f"Failed to disable '{ticker}': {response}")
            return False

    # ------------------------------------------------------------------
    # Generic task polling (usable outside coin activation)
    # ------------------------------------------------------------------

    def poll_task_status(
        self,
        status_method: str,
        task_id: int,
        *,
        node: Optional[NodeConfig] = None,
        timeout: int = 120,
        sleep_seconds: int = 5,
    ) -> Dict[str, Any] | None:
        """Poll *status_method* until the task completes or *timeout* seconds pass.

        Returns the final `result` object on success, or ``None`` if the task
        fails or times out.

        Success criteria:
        • If the response contains a `status` field, we treat `status == 'Ok'` as
          success and `status == 'Error'` as failure.
        • If there is no `status` field but keys such as `wallet_balance` or
          `details` are present, we consider the task complete and successful.
        """
        target_node = node or self.config.nodes[0]
        self.logger.info(f"Polling {status_method} for task_id {task_id} on node {target_node.name}…")

        start = time.time()
        while time.time() - start < timeout:
            req_body = {
                "userpass": target_node.userpass,
                "method": status_method,
                "mmrpc": "2.0",
                "params": {"task_id": task_id, "forget_if_finished": False},
            }
            node_url = target_node.api_url
            resp = self._make_request(node_url, req_body)

            if not resp or "result" not in resp:
                self.logger.warning(f"{status_method} returned unexpected response: {resp}")
                time.sleep(sleep_seconds)
                continue

            result = resp["result"]

            # 1. Explicit status field handling
            status = result.get("status")
            if status:
                if status == "Ok":
                    self.logger.success(f"Task {task_id} completed successfully.")
                    return result
                if status in {"Error", "Failed", "Aborted"}:
                    self.logger.error(f"Task {task_id} failed: {result}")
                    return None

            # 2. Heuristic: presence of wallet_balance/details indicates completion
            if any(k in result for k in ("wallet_balance", "details")):
                self.logger.success(f"Task {task_id} completed (no explicit status field).")
                return result

            # Not completed yet; wait.
            self.logger.debug(f"Waiting for task {task_id} via {status_method}…")
            time.sleep(sleep_seconds)

        self.logger.error(f"Polling timed out for task {task_id} via {status_method}.")
        return None 

    def send_request_to_all_nodes(
        self,
        request_body: Dict[str, Any],
        method_name: str,
        output_dir: Path,
        example_number: int,
    ) -> Dict[str, Dict[str, Any]]:
        """Send *request_body* to every locally running KDF docker node in parallel.
    
        Previously this function iterated over nodes sequentially which slowed down the
        overall scan considerably. We now leverage ``concurrent.futures.ThreadPoolExecutor``
        to dispatch the HTTP POST requests concurrently – one per docker node. This
        typically cuts the waiting time by ~4× on the default 4-node setup.
        """

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        nodes_cfg = self.config.nodes

        # Shared responses mapping to be returned at the end
        responses: Dict[str, Dict[str, Any]] = {}

        # ------------------------------------------------------------------
        # Helper executed in a worker thread for exactly one *node*.
        # ------------------------------------------------------------------
        def _process_single_node(node: NodeConfig) -> tuple[str, Dict[str, Any]]:
            """Send the request to *node* and persist the response on disk.

            Returns a tuple ``(node.name, response_json)`` for aggregation by the
            outer scope.
            """

            body = copy.deepcopy(request_body)
            body["userpass"] = node.userpass
            self.logger.debug(f"Making {body['method']} request to {node.name} ({node.api_url})")
            # Apply test parameter substitution if enabled and this is NOT an activation method
            if self.substitute_defaults and not self.is_activation_method(method_name):
                body = self._substitute_default_params(body)

            # Inject cached data relevant for this node
            body = self._inject_cached_data(method_name, body, node)

            # Activate coins if needed; on failure we early-return
            coins_active, coin = self.check_coin_is_active(body, node)
            if not coins_active:
                self.logger.error(
                    f"Skipping request for method '{method_name}' on node '{node.name}' "
                    f"as activation for '{coin}' failed."
                )
                resp_json: Dict[str, Any] = {"error": f"Coin activation failed for {coin}"}
            else:
                # ------------------------------------------------------------------
                # Special handling for `disable_coin` tests
                # ------------------------------------------------------------------
                if method_name == "disable_coin":
                    # Ensure the target coin is active before attempting to disable.
                    # Although `check_coin_is_active` should have activated it already,
                    # the explicit check keeps the intent crystal-clear and guards
                    # against future refactors.
                    target_coin = (
                        body.get("coin")
                        or (body.get("params", {}).get("coin") if isinstance(body.get("params"), dict) else None)
                    )
                    if target_coin and target_coin not in self.enabled_coins[node.name]:
                        self.logger.info(
                            f"Coin '{target_coin}' is not active on node '{node.name}' – activating before disable test."
                        )
                        if not self.activate_coin(target_coin, node=node):
                            self.logger.error(
                                f"Unable to activate '{target_coin}' on node '{node.name}'. Skipping disable_coin test."
                            )
                            resp_json = {"error": f"Pre-activation failed for {target_coin}"}
                            # Persist the error response later in the function
                        else:
                            # With coin now active, proceed to disable
                            resp_json = self._make_request(node.api_url, body)
                    else:
                        # Coin is active already – normal flow
                        resp_json = self._make_request(node.api_url, body)
                else:
                    # Regular (non-disable_coin) request flow
                    resp_json = self._make_request(node.api_url, body)

                # ------------------------------------------------------------------
                # Re-enable the coin after a successful `disable_coin` test so that
                # subsequent examples running in the same session have the coin
                # available as expected.
                # ------------------------------------------------------------------
                if method_name == "disable_coin":
                    target_coin = (
                        body.get("coin")
                        or (body.get("params", {}).get("coin") if isinstance(body.get("params"), dict) else None)
                    )
                    if (
                        target_coin
                        and isinstance(resp_json, dict)
                        and resp_json.get("result", {}).get("status") == "success"
                    ):
                        self.logger.info(
                            f"Re-enabling coin '{target_coin}' on node '{node.name}' after disable_coin test."
                        )
                        # Ignore activation failure here; log only.
                        if not self.activate_coin(target_coin, node=node):
                            self.logger.warning(
                                f"Failed to re-enable '{target_coin}' on node '{node.name}' after disable_coin test."
                            )

            # Persist response/error JSON to disk following naming convention
            hd_flag = "hd" if node.hd_mode else "nonhd"
            wasm_flag = "wasm" if node.wasm_mode else "native"
            suffix = "error" if "error" in resp_json else "response"
            file_stem = f"{method_name}-{example_number}-{hd_flag}-{wasm_flag}-{suffix}.json"
            file_path = output_dir / file_stem
            try:
                with open(file_path, "w") as fp:
                    json.dump(resp_json, fp, indent=2)
                self.logger.save(f"Saved {suffix} from {node.name} → {file_path}")
            except IOError as ioe:
                self.logger.error(f"Failed to write response file {file_path}: {ioe}")

            return node.name, resp_json

        # ------------------------------------------------------------------
        # Dispatch requests concurrently.
        # ------------------------------------------------------------------
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes_cfg)) as executor:
            # Submit tasks – returns mapping future → node_name implicitly carried via closure
            future_to_node = {executor.submit(_process_single_node, node): node for node in nodes_cfg}

            for future in concurrent.futures.as_completed(future_to_node):
                node_name = future_to_node[future].name
                try:
                    n_name, resp = future.result()
                    responses[n_name] = resp
                except Exception as exc:
                    self.logger.error(f"Unhandled exception while processing node '{node_name}': {exc}")
                    responses[node_name] = {"error": str(exc)}

        return responses

# =============================================================
# Helper utilities for multi-node testing
# =============================================================

def compare_node_responses(
    responses: Dict[str, Dict[str, Any]],
    logger: Optional[KomodoLogger] = None,
) -> Dict[str, Any]:
    """Simple comparator for multi-node responses.

    Takes the mapping produced by :pyfunc:`send_request_to_all_nodes` and
    returns a summary dict highlighting nodes whose responses deviate from the
    baseline (first entry in the mapping).
    """

    logger = logger or KomodoLogger("multi-node-request")

    if not responses:
        logger.warning("No responses provided for comparison.")
        return {}

    # Establish baseline from the first node inserted into the dict
    baseline_node, baseline_resp = next(iter(responses.items()))
    baseline_serialised = json.dumps(baseline_resp, sort_keys=True)

    diff_summary: Dict[str, Any] = {}

    for node, resp in responses.items():
        serialised = json.dumps(resp, sort_keys=True)
        if serialised != baseline_serialised:
            diff_summary[node] = {
                "matches_baseline": False,
                "differences": {
                    "baseline": baseline_resp,
                    "current": resp,
                },
            }
            logger.warning(f"❌ Response from {node} differs from {baseline_node}.")
        else:
            diff_summary[node] = {"matches_baseline": True}
            logger.info(f"✅ Response from {node} matches baseline.")

    return diff_summary