# KDF Integration Test Suite

This directory contains an **integrated PyTest suite** for exercising several Komodo DeFi Framework (KDF) RPC methods in a running node.  The tests were consolidated from the original standalone scripts:

* `test_hd_wallet_msg_signing.py`
* `test_unified_rpc_interface.py`
* `test_zcoin_locked_notes.py`

and are now available as a single module: `test_kdf_methods.py`.

---

## Prerequisites

1. **Docker & Docker Compose** – the suite can automatically spin-up a KDF node using the compose file located at `utils/docker/docker-compose.yml`.
2. **Python 3.9+** – tests rely on the repository's virtual environment and the `pytest` package.

> **Tip** – The repository already contains a pre-configured virtual environment.  Activate it first[[memory:7886665871962470414]]:
>
> ```bash
> source utils/py/.venv/bin/activate
> ```

If you prefer to use your own environment, simply ensure `pytest` and `requests` are installed:

```bash
pip install pytest requests
```

---

## Environment Variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `START_KDF_CONTAINER` | `1` | When **`1`**, `pytest` will automatically run `docker compose up -d --build` <br/>and tear it down after the tests.  Set to **`0`** if you want to manage the node lifecycle yourself. |
| `RPC_URL` | `http://127.0.0.1` | Base URL where the daemon listens. |
| `RPC_PORT` | `7783` | RPC port exposed by the compose stack. |
| `RPC_PASSWORD` | `RPC_UserP@SSW0RD` | Authentication token used for every JSON-RPC call. |
| `WALLET_DIR` | – | Absolute path to the directory that stores the Z-coin wallet DB. <br/>Used by the *locked notes* test; omit to skip that test. |
| `ZCOIN_TICKER` | `ARRR` | Ticker used in the locked notes test. |
| `ZCOIN_WITHDRAW_AMOUNT` | `0.0001` | Withdrawal amount for the locked notes test. |

All variables (except `WALLET_DIR`) are already defined in **`utils/docker/kdf-config/.env`**.  You can source that file before running the suite:

```bash
export $(grep -v '^#' utils/docker/kdf-config/.env | xargs)
```

---

## Running the Tests

From the repository root:

```bash
# (Optionally) activate venv and export env-vars
source utils/py/.venv/bin/activate
export $(grep -v '^#' utils/docker/kdf-config/.env | xargs)

# Execute the full suite
pytest utils/py/kdf_test_cases
```

PyTest will:

1. Build and start the KDF container (unless `START_KDF_CONTAINER=0`).
2. Wait a few seconds for the daemon to become ready.
3. Execute the three tests contained in `TestKDFMethods`.
4. Shut the container down (unless `START_KDF_CONTAINER=0`).

---

## Selective Test Execution

Use PyTest's `-k` option to run a single test:

```bash
pytest -k test_hd_wallet_message_signing utils/py/kdf_test_cases
```

---

## Troubleshooting

* **Container fails to start** – make sure ports `7783`, `42845`, and `42855` are free or adjust them in `docker-compose.yml` and the corresponding environment variables.
* **RPC authentication errors** – confirm that the `RPC_PASSWORD` used by the tests matches the password in the container's `.env`.
* **Locked notes test skipped** – set `WALLET_DIR` to the directory holding the wallet database of your Z-coin wallet.  Example:

  ```bash
  export WALLET_DIR=$HOME/.kdf/z_coin_wallet
  ```

---

## Cleaning Up

If you started the container manually or set `START_KDF_CONTAINER=0`, stop it yourself:

```bash
docker compose -f utils/docker/docker-compose.yml down
```

---

Happy testing! 🚀 