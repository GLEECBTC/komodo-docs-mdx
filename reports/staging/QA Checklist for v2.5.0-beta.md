# QA Checklist – Komodo DeFi Framework v2.5.0-beta (RC)

> Branch / PR under test: [komodo-defi-framework#2491](https://github.com/KomodoPlatform/komodo-defi-framework/pull/2491)
>
> Changelog reference: utils/docker/komodo-defi-framework/CHANGELOG.md – section **v2.5.0-beta – 2025-06-23**

This document enumerates every manual & automated test that *must* pass before the 2.5.0-beta release candidate can be signed-off.  
Tests are grouped by functional area and are mapped 1-to-1 with planned **pytest** modules (listed at the end of the file).  
Please tick every ☐ once the corresponding step passes.

---

## 0. Pre-Requisites

- [ ] Latest `v2.5.0-beta` docker image built locally (`kdf:2.5.0-beta-<hash>`)
- [ ] Feature flags: `ibc-routing-for-swaps` **enabled** for IBC validation tests; **disabled** for cross-check
- [ ] Two local nodes (`node-A`, `node-B`) + `ganache` (EVM mock) + `ibc-mock-grpc` on default ports
- [ ] Python venv activated: `source utils/py/.venv/bin/activate`
- [ ] Repo root added to `PYTHONPATH`

---

## 1. Wallet & Security

### 1.1 `delete_wallet` Extended Scenarios
- [ ] ☐ Attempt deletion while wallet has an **open order** → expect `WalletIsActive`
- [ ] ☐ Deletion when wallet file locked by **second KDF instance** → expect `WalletLocked`

### 1.2 HD Multi-Address Message Signing
- [ ] ☐ Sign/verify **3 derived addresses** emits correct **event-stream** payload (`signature`, `derivation_path`)
- [ ] ☐ Same test under **WASM** build in headless Chrome

### 1.3 Expirable Pubkey Bans
- [ ] ☐ Ban pubkey with `duration_min=0.05` → auto-unban after 3 s
- [ ] ☐ Persistence across restart (ban -> restart -> list)

---

## 2. WalletConnect v2 Integration

- [ ] ☐ `wc_new_connection` returns valid `wc:` URI
- [ ] ☐ EIP-155 session established via testing bridge; can call `eth_signTransaction`
- [ ] ☐ Cosmos session established; can call `cosmos_signDirect`
- [ ] ☐ `wc_ping_session` round-trips OK
- [ ] ☐ `wc_delete_session` removes topic & SSE closes

---

## 3. IBC & Cosmos Enhancements

### 3.1 Pre-Swap Validation (`ibc-routing-for-swaps` **ON**)
- [ ] ☐ Maker `sell` for non-HTLC coin **without** healthy channel → `RouteUnavailable`
- [ ] ☐ Repeat **with** healthy channel → order succeeds
- [ ] ☐ Flag **OFF** → validation skipped

### 3.2 Unconfirmed Z-Coin Notes
- [ ] ☐ Create Z-coin tx with change → `my_balance` subtracts change until confirmation

---

## 4. Trading Protocol & Volume Rules

- [ ] ☐ `min_trading_vol` ≥ 0.0001 **removed** for BTC (now matches others)
- [ ] ☐ Orders below protocol min still rejected
- [ ] ☐ DEX-fee calculation unaffected

---

## 5. Event Streaming & Networking

### 5.1 StreamerId Format Change
- [ ] ☐ Subscribe to `BALANCE:ETH`, `ORDERBOOK:KMD/BTC` – payload uses *colon* format
- [ ] ☐ Old JSON streamer id → returns `InvalidStreamerId`

### 5.2 Seednode Removal & DNS Enhancements
- [ ] ☐ Node fails gracefully when `seednodes` empty
- [ ] ☐ IPv6-only hostname ignored, IPv4 picked from multi-A record

---

## 6. RPC Interface Unification / Breaking Changes

- [ ] ☐ `get_enabled_coins` (v1) vs `wallet::get_enabled_coins` (v2) parity
- [ ] ☐ Old EVM `priv_key_policy` format fails; new enum `{ "type": "ContextPrivKey" }` passes

---

## 7. TRON Groundwork (Smoke)

- [ ] ☐ `enable_tron` returns stub response, no panic

---

## 8. Manual / Exploratory

- [ ] ☐ Try WalletConnect with real MetaMask mobile
- [ ] ☐ Attempt Trezor activation error path – confirm `HwError` docs
- [ ] ☐ DNS mis-configuration produces user-readable error

---

## 9. Regression Sanity

- [ ] ☐ Run full v2.4.0 regression script against 2.5.0 binary – only expected breaks

---

## Planned **pytest** Modules

> Create each file inside `utils/py/tests/` unless stated otherwise.

1. `test_delete_wallet_extended.py`
2. `test_hd_signing_wasm.py`
3. `test_pubkey_ban_expiry.py`
4. `test_walletconnect_sessions.py`
5. `test_ibc_pre_swap_validation.py`
6. `test_zcoin_unconfirmed_notes.py`
7. `test_min_trading_volume.py`
8. `test_streamer_id_format.py`
9. `test_dns_seednode_logic.py`
10. `test_rpc_interface_unification.py`
11. `test_tron_enable_stub.py`

*(Optional, manual runner)*  
12. `scripts/manual_walletconnect_mobile.md` – step-by-step guide for mobile WC validation.

> Tackle the list sequentially; checkboxes above mirror the module order.

---

**Last updated:** <!--STAMP--> 