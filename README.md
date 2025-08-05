# Komodo Developer Docs Content

Content for the Komodo Developer Docs lives in this repo in `.mdx` format. This repository is then used as a submodule to build and deploy the Komodo Developer Docs website.

## Getting Started

- **[Style Guide](docs/STYLE_GUIDE.md)** - Complete documentation standards including KDF API methods, table formats, and example best practices
- **[Contribution Guide](docs/CONTRIBUTION_GUIDE.md)** - Pull request submission process
- **[Sidebar Configuration](https://github.com/KomodoPlatform/komodo-docs-mdx/blob/main/src/data/sidebar.json)** - Add new pages to site navigation
- **[Code of Conduct](docs/CODE_OF_CONDUCT.md)** - Community guidelines

## JSON Example Structure

API method examples are organized using a simplified **1:1 method:folder** structure aligned with our MDX example standards:

### Structure Convention

```
postman/json/kdf/
├── v1/                                    # Legacy API examples
└── v2/                                    # Current API examples
    ├── task-enable_utxo-init/             # Task-based methods
    │   ├── task-enable_utxo-init-btc_electrum_activation-request.json
    │   ├── task-enable_utxo-init-eth_native_mode-request.json
    │   └── task-enable_utxo-init-kmd_with_rewards-request.json
    ├── my_balance/                        # Simple methods
    │   ├── my_balance-single_coin_check-request.json
    │   └── my_balance-portfolio_overview-request.json
    └── orderbook/                         # Trading methods
        ├── orderbook-btc_kmd_pair-request.json
        └── orderbook-high_volume_filter-request.json
```

### Naming Conventions

**Method Directories:**
- Use kebab-case with underscores preserved: `task-enable_utxo-init`, `my_balance`, `orderbook`
- Convert filesystem-safe hyphens back to API format: `task-enable_utxo-init` → `task::enable_utxo::init`

**Example Files:**
- Format: `{method-name}-{semantic_description}-{type}.json`
- Use **semantic descriptions** that reflect actual use cases (not generic numbers)
- Types: `request`, `response`
- Examples: 
  - `task-enable_utxo-init-btc_electrum_activation-request.json`
  - `my_balance-single_coin_check-request.json`
  - `orderbook-btc_kmd_pair-request.json`

### Rationale

This structure provides:

1. **Semantic Clarity**: Example names reflect actual use cases, not arbitrary numbers
2. **MDX Alignment**: Matches the descriptive naming standards in our Style Guide
3. **Maintainability**: Easy to identify what each example demonstrates
4. **Consistency**: One method = one folder, predictable structure
5. **Tool Compatibility**: Works with Postman, Newman, and automation scripts

### Adding Examples

When adding new JSON examples:

1. **Follow semantic naming**: Use descriptive names that reflect the use case
2. **Avoid numbered examples**: Use `btc_electrum_activation` not `example-1`
3. **Check for duplicates**: Review existing examples before adding new ones
4. **Align with MDX**: Ensure JSON examples match the examples in MDX documentation

Refer to the **[Style Guide MDX Example Standards](STYLE_GUIDE.md#mdx-example-standards)** for complete guidelines on creating meaningful, non-duplicate examples.

## Hardware Wallet Support (Trezor)

The Docker stack now ships a dedicated **`trezord`** service.  It mounts the host's USB bus and exposes the familiar Bridge API on `http://127.0.0.1:21325`.

```bash
# start everything (including trezord side-car)
docker compose -f utils/docker/docker-compose.yml up -d --build
```

Nothing inside the KDF containers needs to change – they continue to discover the bridge at `127.0.0.1:21325` (or `host.docker.internal:21325` on non-Linux Docker engines).

If you unplug / plug the Trezor the side-car will pick it up automatically.

### Linux udev Rule (required for real devices)

On Linux the Trezor's USB interfaces are created with root-only permissions.  Install the official rule once so that non-root processes (and our `trezord` side-car) can access the device:

```bash
# 1. Download the rule
sudo curl -fsSL \
  https://raw.githubusercontent.com/trezor/trezor-common/master/udev/51-trezor.rules \
  -o /etc/udev/rules.d/51-trezor.rules

# 2. Reload udev and re-plug the device
sudo udevadm control --reload-rules && sudo udevadm trigger

# 3. (Optional) make sure your user is in the plugdev group
sudo usermod -aG plugdev $USER
```

After re-plugging the Trezor you should see something like:

```bash
ls -l /dev/hidraw* | grep trezor
# crw-rw-r-- 1 root plugdev 237, 0 Jun 30 15:42 /dev/hidraw0
```

Once this is in place the `trezord` container can talk to the hardware without "No such device" errors.
