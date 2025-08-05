# Grouped collections of Komodo DeFi Framework RPC method names that are
# commonly used together in higher-level flows or tools.
#
# NOTE: Group memberships purposely overlap – a method can appear in more than
# one list if it belongs to several functional flows.

class KdfMethods:
    """Pre-defined method groupings for convenience/look-ups."""

    # ------------------------------------------------------------------
    # Methods currently exercised by utils/py/tui/trezor.py
    # ------------------------------------------------------------------
    trezor = [
        # --- Trezor device initialisation & connection ---
        "trezor_connection_status",
        "task::init_trezor::init",
        "task::init_trezor::status",
        "task::init_trezor::user_action",
        "task::init_trezor::cancel",

        # --- Task-based coin activation (UI builds these dynamically) ---
        # UTXO coins
        "task::enable_utxo::init",
        "task::enable_utxo::status",
        "task::enable_utxo::user_action",
        "task::enable_utxo::cancel",
        # EVM / ERC20 coins
        "task::enable_eth::init",
        "task::enable_eth::status",
        "task::enable_eth::user_action",
        "task::enable_eth::cancel",
        # QTUM / QRC20
        "task::enable_qtum::init",
        "task::enable_qtum::status",
        "task::enable_qtum::user_action",
        "task::enable_qtum::cancel",
        # Tendermint platform coins
        "task::enable_tendermint::init",
        "task::enable_tendermint::status",
        "task::enable_tendermint::user_action",
        "task::enable_tendermint::cancel",
        # ZHTLC coins (Pirate, Zombie…)
        "task::enable_z_coin::init",
        "task::enable_z_coin::status",
        "task::enable_z_coin::user_action",
        "task::enable_z_coin::cancel",

        # --- Wallet-level task methods ---
        # Account balance
        "task::account_balance::init",
        "task::account_balance::status",
        "task::account_balance::cancel",
        # HD account creation
        "task::create_new_account::init",
        "task::create_new_account::status",
        "task::create_new_account::user_action",
        "task::create_new_account::cancel",
        # HD address generation
        "task::get_new_address::init",
        "task::get_new_address::status",
        "task::get_new_address::user_action",
        "task::get_new_address::cancel",
        # Address scanning
        "task::scan_for_new_addresses::init",
        "task::scan_for_new_addresses::status",
        "task::scan_for_new_addresses::cancel",
        # Withdrawals
        "task::withdraw::init",
        "task::withdraw::status",
        "task::withdraw::user_action",
        "task::withdraw::cancel",
    ]

    # ------------------------------------------------------------------
    # WalletConnect-related RPC methods (session control + activation flow)
    # ------------------------------------------------------------------
    walletconnect = [
        # Core WalletConnect session management
        "wc_new_connection",
        "wc_get_sessions",
        "wc_get_session",
        "wc_ping_session",
        "wc_delete_session",

        # Coin activation flows that typically rely on WalletConnect (EVM)
        "task::enable_eth::init",
        "task::enable_eth::status",
        "task::enable_eth::user_action",
        "task::enable_eth::cancel",

        # Tendermint platform coins, which can be activated via WalletConnect
        "task::enable_tendermint::init",
        "task::enable_tendermint::status",
        "task::enable_tendermint::user_action",
        "task::enable_tendermint::cancel",
    ]

    # ------------------------------------------------------------------
    # Balance-related queries (legacy + task-based)
    # ------------------------------------------------------------------
    balances = [
        # Legacy single-shot balance check
        "my_balance",

        # Task-based account balance for HD wallets / hardware wallets
        "task::account_balance::init",
        "task::account_balance::status",
        "task::account_balance::cancel",
    ]

    # ------------------------------------------------------------------
    # Withdrawal / transaction generation, signing and broadcasting
    # ------------------------------------------------------------------
    withdraws = [
        # Task-based flow
        "task::withdraw::init",
        "task::withdraw::status",
        "task::withdraw::user_action",
        "task::withdraw::cancel",

        # Direct v2 withdraw RPC (non-task)
        "withdraw",

        # Raw transaction signing & broadcasting
        "sign_raw_transaction",
        "send_raw_transaction",
    ]

    # ------------------------------------------------------------------
    # v2 RPC methods that EXPECT an explicit empty `params` object. Omitting
    # it triggers `InvalidRequest` errors (see kdf issue #2498).
    # ------------------------------------------------------------------
    no_params_v2 = [
        "wc_get_sessions",  # session listing
        "stop_version_stat_collection",
        "get_public_key_hash",
        "get_public_key",
        "get_enabled_coins",
        "get_shared_db_id",
        "stop_simple_market_maker_bot",
        "get_enabled_account",
        "get_accounts",
        "get_wallet_names",
        # Additional param-less v2 RPCs can be appended here as they are
        # confirmed in the Rust source. Keeping the list centralised allows
        # UI helpers (e.g. walletconnect TUI) to handle the quirk uniformly.
    ]

    no_auth = {
        "version",
        "orderbook",
        "help",
        "metrics",
        "stats_swap_status",
    }

    removed = {
        "autoprice",
        "fundvalue",
        "inventory",
    }