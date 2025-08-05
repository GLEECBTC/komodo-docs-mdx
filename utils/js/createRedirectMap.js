import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.resolve(__dirname, './data');

const pagesDir = path.resolve(__dirname, '../../src/pages');

function walkDir(dirPath, callback) {
  fs.readdirSync(dirPath).forEach((file) => {
    const filePath = path.join(dirPath, file);
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) {
      walkDir(filePath, callback);
    } else {
      callback(filePath);
    }
  });
}

const fileNames = [];
const getFileNames = (filepath) => {
  fileNames.push(filepath);
};

walkDir(pagesDir, getFileNames);

const mapDirObj = {
  "/antara/api/": "/basic-docs/antara/antara-api/",
  "/antara/setup/": "/basic-docs/antara/antara-setup/",
  "/antara/tutorials/": "/basic-docs/antara/antara-tutorials/",
  "/komodo-defi-framework/changelog/": "/basic-docs/atomicdex/changelog/",
  "/komodo-defi-framework/api/legacy/": "/basic-docs/atomicdex-api-legacy/",
  "/komodo-defi-framework/api/v20/": "/basic-docs/atomicdex-api-20/",
  "/komodo-defi-framework/api/v20-dev/": "/basic-docs/atomicdex-api-20-dev/",
  "/komodo-wallet/mobile/": "/basic-docs/atomicdex/atomicdex-beta/",
  "/komodo-defi-framework/setup/": "/basic-docs/atomicdex/atomicdex-setup/",
  "/komodo-defi-framework/tutorials/":
    "/basic-docs/atomicdex/atomicdex-tutorials/",
  "/historical/cc-jl/": "/cc-jl/",
  "/historical/whitepaper/": "/whitepaper/",
  "/smart-chains/api/": "/basic-docs/smart-chains/smart-chain-api/",
  "/smart-chains/changelog/": "/basic-docs/smart-chains/changelog/",
  "/smart-chains/setup/": "/basic-docs/smart-chains/smart-chain-setup/",
  "/smart-chains/tutorials/": "/basic-docs/smart-chains/smart-chain-tutorials/",
  "/start-here/": "/basic-docs/start-here/",
  "/komodo/": "/komodo/",
  "/notary/": "/notary/",
  "/qa/": "/qa/",
  "/resources/": "/resources/",
};

let pathObj = {};
fileNames.forEach((filePath) => {
  for (const newPath in mapDirObj) {
    if (filePath.includes(pagesDir + newPath)) {
      pathObj[
        filePath
          .replace(pagesDir + newPath, mapDirObj[newPath])
          .replace(pagesDir, "")
          .replace("index.mdx", "")
          .slice(0, -1) + ".html"
      ] = filePath.replace(pagesDir, "").replace("index.mdx", "");
    }
  }
});

const nameChangedMap = {
  "/basic-docs/antara/introduction-to-antara.html": "/antara/",
  "/basic-docs/smart-chains/smart-chain-tutorials/subatomic.html":
    "/komodo-defi-framework/",
  "/basic-docs/smart-chains/introduction-to-smart-chain-documentation.html":
    "/smart-chains/",
  "/basic-docs/atomicdex/atomicdex-methods.html": "/komodo-defi-framework/api/",
  "/": "/",
  "/basic-docs/atomicdex/atomicdex-beta/create-a-new-wallet-using-atomicdex-mobile.html":
    "/komodo-wallet/mobile/create-a-new-wallet/",
  "/basic-docs/atomicdex/atomicdex-setup/get-started-atomicdex.html":
    "/komodo-defi-framework/setup/",
  "/basic-docs/atomicdex/atomicdex-tutorials/introduction-to-atomicdex.html":
    "/komodo-defi-framework/tutorials/",
  "/basic-docs/atomicdex/introduction-to-atomicdex.html":
    "/komodo-defi-framework/tutorials/",
  "/mmV2/LP/atomicdex-api-docker-telegram.html":
    "/komodo-defi-framework/tutorials/api-docker-telegram/",
  "/basic-docs/atomicdex/atomicdex-tutorials/add-coin-to-atomicdex-desktop.html":
    "/komodo-defi-framework/tutorials/listing-a-new-coin/",
  "/basic-docs/atomicdex/atomicdex-tutorials/listing-a-coin-on-atomicdex.html":
    "/komodo-defi-framework/tutorials/listing-a-new-coin/",
  "/basic-docs/atomicdex-api-20-dev/account_balance_tasks.html":
    "/komodo-defi-framework/api/v20-dev/task_account_balance/",
  "/basic-docs/atomicdex-api-20-dev/coin_activation_tasks.html":
    "/komodo-defi-framework/api/v20/coin_activation/task_managed/task_enable_qtum/",
  "/basic-docs/atomicdex-api-20-dev/trezor_initialisation.html":
    "/komodo-defi-framework/api/v20/utils/task_init_trezor/",
  "/basic-docs/atomicdex-api-20-dev/withdraw_tasks.html":
    "/komodo-defi-framework/api/v20-dev/task_withdraw/",
  "/basic-docs/atomicdex-api-20-dev/zhtlc_coins.html":
    "/komodo-defi-framework/api/v20-dev/zhtlc_coins/",
  "/basic-docs/smart-chains/smart-chain-tutorials/betdapp.html":
    "/smart-chains/setup/dexp2p/",
  "/basic-docs/smart-chains/smart-chain-tutorials/checklist-new-coin.html":
    "/smart-chains/tutorials/smart-chain-api-basics/",
  "/basic-docs/smart-chains/smart-chain-tutorials/introduction-to-smart-chain-tutorials.html":
    "/smart-chains/tutorials/",
  "/basic-docs/start-here/core-technology-discussions/introduction.html":
    "/start-here/core-technology-discussions/",
  "/basic-docs/start-here/core-technology-discussions/atomicdex.html":
    "/start-here/core-technology-discussions/komodo-defi-framework/",
  "/basic-docs/start-here/learning-launchpad/learning-path-outline.html":
    "/start-here/learning-launchpad/",
  "/basic-docs/start-here/about-komodo-platform/about-komodo-platform.html":
    "/start-here/about-komodo-platform/",
  "/cc-jl/introduction.html": "/historical/cc-jl/",
  "/whitepaper/introduction.html": "/historical/whitepaper/",
  "/komodo/installation.html": "/komodo/",
  "/komodo/access-remote-daemon-ssh.html":
    "/komodo-defi-framework/tutorials/setup-komodefi-api-aws/",
  "/komodo/info.html": "/smart-chains/setup/ecosystem-launch-parameters/",
  "/komodo/multisig-transactions-on-komodo-or-assetchains.html":
    "/komodo/multisig-transactions-on-komodo-or-smartchains/",
  "/notary/setup-Komodo-Notary-Node.html": "/notary/",
  "/notary/generate-privkeys-third-party-coins-from-passphrase.html":
    "/notary/generate-privkeys-for-third-party-coins-from-passphrase/",
  "/notary/update-Komodo-manually.html": "/notary/update-komodo-manually/",
  "/notary/useful-commands-Komodo-Notary-Node.html":
    "/notary/useful-commands-for-komodo-notary-node/",
  "/komodo/block-1M-changes.html": "/komodo/block-1m-changes/",
  "/komodo/dPoW-conf.html": "/komodo/dpow-conf/",
  "/komodo/setup-electrumX-server.html": "/komodo/setup-electrumx-server/",
  "/komodo/using-Key-Value.html": "/komodo/using-key-value/",
  "/qa/atomicDEX-PRO/build.html": "/qa/komodo-desktop-wallet-build/",
  "/qa/atomicDEX-quickstart.html": "/qa/komodefi-api-quickstart/",
  "/qa/debug-Komodo.html": "/qa/debug-komodo/",
  "/qa/extract-swap-data-atomicDEX-log.html":
    "/qa/extract-swap-data-komodo-wallet-log/",
  "/qa/recover-atomicDEX-mobile-swap-desktop.html":
    "/qa/recover-komodo-mobile-wallet-swap-on-desktop/",
  "/resources/third-party-repos-resources.html": "/resources/third-party/",
  "/resources/list-all-KomodoPlatform-repos-links.html": "/resources/",
  "/basic-docs/antara/activate-antara-smartchain.html":
    "/antara/tutorials/activate-antara-smartchain/",
  "/basic-docs/antara/test-use-write-integrate-antara.html":
    "/antara/tutorials/test-use-write-integrate-antara/",
  "/basic-docs/atomicdex/atomicdex-tutorials/atomicdex-walkthrough.html":
    "/komodo-defi-framework/tutorials/api-walkthrough/",
  "/basic-docs/atomicdex/atomicdex-tutorials/atomicdex-metrics.html":
    "/komodo-defi-framework/tutorials/api-metrics/",
  "/basic-docs/atomicdex/atomicdex-tutorials/setup-atomicdex-aws.html":
    "/komodo-defi-framework/tutorials/setup-komodefi-api-aws/",
  "/basic-docs/atomicdex/atomicdex-tutorials/additional-information-about-atomicdex.html":
    "/komodo-defi-framework/tutorials/additional-information/",
  "/basic-docs/atomicdex/atomicdex-beta/restore-wallet-using-atomicdex-mobile.html":
    "/komodo-wallet/mobile/restore-a-wallet/",
  "/basic-docs/atomicdex/atomicdex-beta/add-and-activate-coins-on-atomicdex-mobile.html":
    "/komodo-wallet/mobile/add-and-activate-coins/",
  "/basic-docs/atomicdex/atomicdex-beta/withdraw-or-send-funds-using-atomicdex-mobile.html":
    "/komodo-wallet/mobile/withdraw-or-send-funds/",
  "/basic-docs/atomicdex/atomicdex-beta/perform-cross-chain-atomic-swaps-using-atomicdex-mobile.html":
    "/komodo-wallet/mobile/perform-cross-chain-atomic-swaps/",
  "/basic-docs/atomicdex/atomicdex-beta/view-ongoing-orders-and-swap-history-on-atomicdex-mobile.html":
    "/komodo-wallet/mobile/view-ongoing-orders-and-swap-history/",
  "/basic-docs/atomicdex/atomicdex-beta/view-your-receiving-address-to-send-funds-for-trading.html":
    "/komodo-wallet/mobile/view-your-receiving-address-to-send-funds-for-trading/",
  "/basic-docs/atomicdex/atomicdex-beta/recover-seed-on-atomicdex-mobile.html":
    "/komodo-wallet/mobile/recover-seed-phrase/",
  "/basic-docs/atomicdex/atomicdex-beta/delete-seed-from-atomicdex-mobile.html":
    "/komodo-wallet/mobile/delete-seed-phrase/",
  "/basic-docs/atomicdex/atomicdex-tutorials/how-to-compile-mm2-from-source.html": "/komodo-defi-framework/api/",
  "/basic-docs/atomicdex-api-20/add_delegation.html": "/komodo-defi-framework/api/v20/wallet/staking/add_delegation/",
  "/basic-docs/atomicdex-api-20/add_node_to_version_stat.html": "/komodo-defi-framework/api/v20/utils/add_node_to_version_stat/",
  "/basic-docs/atomicdex-api-20/best_orders.html": "/komodo-defi-framework/api/v20/swaps_and_orders/best_orders/",
  "/basic-docs/atomicdex-api-20/enable_bch_with_tokens.html": "/komodo-defi-framework/api/v20/coin_activation/enable_bch_with_tokens/",
  "/basic-docs/atomicdex-api-20/enable_erc20.html": "/komodo-defi-framework/api/v20/coin_activation/enable_erc20/",
  "/basic-docs/atomicdex-api-20/enable_eth_with_tokens.html": "/komodo-defi-framework/api/v20/coin_activation/enable_eth_with_tokens/",
  "/basic-docs/atomicdex-api-20/enable_slp.html": "/komodo-defi-framework/api/v20/coin_activation/enable_slp/",
  "/basic-docs/atomicdex-api-20/enable_tendermint_token.html": "/komodo-defi-framework/api/v20/coin_activation/enable_tendermint_token/",
  "/basic-docs/atomicdex-api-20/enable_tendermint_with_assets.html": "/komodo-defi-framework/api/v20/coin_activation/enable_tendermint_with_assets/",
  "/basic-docs/atomicdex-api-20/get_public_key.html": "/komodo-defi-framework/api/v20/utils/get_public_key/",
  "/basic-docs/atomicdex-api-20/get_public_key_hash.html": "/komodo-defi-framework/api/v20/utils/get_public_key_hash/",
  "/basic-docs/atomicdex-api-20/get_raw_transaction.html": "/komodo-defi-framework/api/v20/wallet/tx/get_raw_transaction/",
  "/basic-docs/atomicdex-api-20/get_staking_infos.html": "/komodo-defi-framework/api/v20/wallet/staking/get_staking_infos/",
  "/basic-docs/atomicdex-api-20/message_signing.html": "/komodo-defi-framework/api/v20/utils/message_signing/sign_message/",
  "/basic-docs/atomicdex-api-20/my_tx_history.html": "/komodo-defi-framework/api/v20/wallet/tx/my_tx_history/",
  "/basic-docs/atomicdex-api-20/recreate_swap_data.html": "/komodo-defi-framework/api/v20/swaps_and_orders/recreate_swap_data/",
  "/basic-docs/atomicdex-api-20/remove_delegation.html": "/komodo-defi-framework/api/v20/wallet/staking/remove_delegation/",
  "/basic-docs/atomicdex-api-20/remove_node_from_version_stat.html": "/komodo-defi-framework/api/v20/utils/remove_node_from_version_stat/",
  "/basic-docs/atomicdex-api-20/start_simple_market_maker_bot.html": "/komodo-defi-framework/api/v20/swaps_and_orders/start_simple_market_maker_bot/",
  "/basic-docs/atomicdex-api-20/start_version_stat_collection.html": "/komodo-defi-framework/api/v20/utils/start_version_stat_collection/",
  "/basic-docs/atomicdex-api-20/stop_simple_market_maker_bot.html": "/komodo-defi-framework/api/v20/swaps_and_orders/stop_simple_market_maker_bot/",
  "/basic-docs/atomicdex-api-20/stop_version_stat_collection.html": "/komodo-defi-framework/api/v20/utils/stop_version_stat_collection/",
  "/basic-docs/atomicdex-api-20/telegram_alerts.html": "/komodo-defi-framework/api/v20/utils/telegram_alerts/",
  "/basic-docs/atomicdex-api-20/trade_preimage.html": "/komodo-defi-framework/api/v20/swaps_and_orders/trade_preimage/",
  "/basic-docs/atomicdex-api-20/update_version_stat_collection.html": "/komodo-defi-framework/api/v20/utils/update_version_stat_collection/",
  "/basic-docs/atomicdex-api-20/withdraw.html": "/komodo-defi-framework/api/v20/wallet/tx/withdraw/",
  "/basic-docs/atomicdex-api-20-dev/get_current_mtp.html": "/komodo-defi-framework/api/v20/utils/get_current_mtp/",
  "/basic-docs/atomicdex-api-20-dev/get_locked_amount.html": "/komodo-defi-framework/api/v20/swaps_and_orders/get_locked_amount/",
  "/basic-docs/atomicdex-api-20-dev/hd_address_management.html": "/komodo-defi-framework/api/",
  "/basic-docs/atomicdex-api-20-dev/hd_wallets_overview.html": "/komodo-defi-framework/api/",
  "/basic-docs/atomicdex-api-20-dev/max_maker_vol.html": "/komodo-defi-framework/api/v20/swaps_and_orders/max_maker_vol/",
  "/basic-docs/atomicdex-api-legacy/get_peers_info.html": "/komodo-defi-framework/api/",
};

for (const path in nameChangedMap) {
  pathObj[path] = nameChangedMap[path];
}


const oldDocsRedirects = {
  "/basic-docs/cryptoconditions/cc-tokens.html":
    "/basic-docs/antara/antara-api/tokens.html",
  "/basic-docs/cryptoconditions/cc-channels.html":
    "/basic-docs/antara/antara-api/channels.html",
  "/basic-docs/cryptoconditions/cc-momom.html":
    "/basic-docs/smart-chains/smart-chain-api/crosschain.html",
  "/basic-docs/cryptoconditions/cc-custom.html":
    "/basic-docs/antara/antara-tutorials/advanced-series-2.html",
  "/basic-docs/cryptoconditions/cc-sudoku.html":
    "/basic-docs/antara/antara-api/sudoku.html",
  "/basic-docs/cryptoconditions/cc-heir.html":
    "/basic-docs/antara/antara-api/heir.html",
  "/basic-docs/cryptoconditions/cc-musig.html":
    "/basic-docs/antara/antara-api/musig.html",
  "/basic-docs/cryptoconditions/cryptoconditions-tutorial.html":
    "/basic-docs/antara/antara-tutorials/introduction-to-antara-tutorials.html",
  "/basic-docs/cryptoconditions/cc-gateways.html":
    "/basic-docs/antara/antara-api/gateways.html",
  "/basic-docs/cryptoconditions/cc-rewards.html":
    "/basic-docs/antara/antara-api/rewards.html",
  "/basic-docs/cryptoconditions/cc-faucet.html":
    "/basic-docs/antara/antara-api/faucet.html",
  "/basic-docs/cryptoconditions/cc-dice.html":
    "/basic-docs/antara/antara-api/dice.html",
  "/basic-docs/cryptoconditions/cryptoconditions-instructions.html":
    "/basic-docs/antara/antara-tutorials/understanding-antara-addresses.html",
  "/basic-docs/cryptoconditions/dynamic-modules-instructions.html":
    "/basic-docs/antara/antara-tutorials/understanding-antara-addresses.html",
  "/basic-docs/cryptoconditions/cc-assets.html":
    "/basic-docs/antara/antara-api/assets.html",
  "/basic-docs/cryptoconditions/cc-oracles.html":
    "/basic-docs/antara/antara-api/oracles.html",
  "/basic-docs/cryptoconditions/cc-rogue.html":
    "/basic-docs/antara/antara-api/rogue.html",
  "/basic-docs/cryptoconditions/cc-dilithium.html":
    "/basic-docs/antara/antara-api/dilithium.html",
  "/basic-docs/start-here/cc-overview.html":
    "/basic-docs/antara/introduction-to-antara.html",
  "/basic-docs/customconsensus/tokens.html":
    "/basic-docs/antara/antara-api/tokens.html",
  "/basic-docs/customconsensus/channels.html":
    "/basic-docs/antara/antara-api/channels.html",
  "/basic-docs/customconsensus/momom.html":
    "/basic-docs/smart-chains/smart-chain-api/crosschain.html",
  "/basic-docs/customconsensus/custom.html":
    "/basic-docs/antara/antara-tutorials/advanced-series-2.html",
  "/basic-docs/customconsensus/sudoku.html":
    "/basic-docs/antara/antara-api/sudoku.html",
  "/basic-docs/customconsensus/heir.html":
    "/basic-docs/antara/antara-api/heir.html",
  "/basic-docs/antara/antara-tutorials/heir-module-tutorial.html":
    "/basic-docs/antara/antara-tutorials/advanced-series-5.html",
  "/basic-docs/antara/antara-tutorials/overview-of-development-on-komodo-part-1.html":
    "/basic-docs/antara/antara-tutorials/overview-of-antara-modules-part-i.html",
  "/basic-docs/antara/antara-tutorials/overview-of-development-on-komodo-part-2.html":
    "/basic-docs/antara/antara-tutorials/understanding-antara-addresses.html",
  "/basic-docs/antara/antara-tutorials/pegs.html":
    "/basic-docs/antara/antara-api/pegs.html",
  "/basic-docs/customconsensus/musig.html":
    "/basic-docs/antara/antara-api/musig.html",
  "/basic-docs/customconsensus/custom-consensus-tutorial.html":
    "/basic-docs/antara/antara-tutorials/introduction-to-antara-tutorials.html",
  "/basic-docs/customconsensus/gateways.html":
    "/basic-docs/antara/antara-api/gateways.html",
  "/basic-docs/customconsensus/rewards.html":
    "/basic-docs/antara/antara-api/rewards.html",
  "/basic-docs/customconsensus/faucet.html":
    "/basic-docs/antara/antara-api/faucet.html",
  "/basic-docs/customconsensus/dice.html":
    "/basic-docs/antara/antara-api/dice.html",
  "/basic-docs/customconsensus/custom-consensus-instructions.html":
    "/basic-docs/antara/antara-tutorials/understanding-antara-addresses.html",
  "/basic-docs/customconsensus/dynamic-modules-instructions.html":
    "/basic-docs/antara/antara-tutorials/understanding-antara-addresses.html",
  "/basic-docs/customconsensus/assets.html":
    "/basic-docs/antara/antara-api/assets.html",
  "/basic-docs/customconsensus/oracles.html":
    "/basic-docs/antara/antara-api/oracles.html",
  "/basic-docs/customconsensus/rogue.html":
    "/basic-docs/antara/antara-api/rogue.html",
  "/basic-docs/antara/customconsensus/rogue.html":
    "/basic-docs/antara/antara-api/rogue.html",
  "/basic-docs/start-here/custom-consensus-overview.html":
    "/basic-docs/antara/introduction-to-antara.html",
  "/basic-docs/installations/asset-chain-parameters.html":
    "/basic-docs/antara/antara-setup/antara-customizations.html",
  "/basic-docs/komodo-api/address.html":
    "/basic-docs/smart-chains/smart-chain-api/address.html",
  "/basic-docs/komodo-api/blockchain.html":
    "/basic-docs/smart-chains/smart-chain-api/blockchain.html",
  "/basic-docs/basic-docs/smart-chains/smart-chain-api/blockchain.html":
    "/basic-docs/smart-chains/smart-chain-api/blockchain.html",
  "/basic-docs/komodo-api/cclib.html":
    "/basic-docs/smart-chains/smart-chain-api/cclib.html",
  "/basic-docs/komodo-api/control.html":
    "/basic-docs/smart-chains/smart-chain-api/control.html",
  "/basic-docs/komodo-api/crosschain.html":
    "/basic-docs/smart-chains/smart-chain-api/crosschain.html",
  "/basic-docs/komodo-api/disclosure.html":
    "/basic-docs/smart-chains/smart-chain-api/disclosure.html",
  "/basic-docs/komodo-api/generate.html":
    "/basic-docs/smart-chains/smart-chain-api/generate.html",
  "/basic-docs/komodo-api/jumblr.html":
    "/basic-docs/smart-chains/smart-chain-api/jumblr.html",
  "/basic-docs/komodo-api/mining.html":
    "/basic-docs/smart-chains/smart-chain-api/mining.html",
  "/basic-docs/komodo-api/network.html":
    "/basic-docs/smart-chains/smart-chain-api/network.html",
  "/basic-docs/komodo-api/wallet.html":
    "/basic-docs/smart-chains/smart-chain-api/wallet.html",
  "/basic-docs/komodo-api/rawtransactions.html":
    "/basic-docs/smart-chains/smart-chain-api/rawtransactions.html",
  "/basic-docs/antara/komodo-api/rawtransactions.html":
    "/basic-docs/smart-chains/smart-chain-api/rawtransactions.html",
  "/basic-docs/komodo-api/util.html":
    "/basic-docs/smart-chains/smart-chain-api/util.html",
  "/basic-docs/antara/komodo-api/wallet.html":
    "/basic-docs/smart-chains/smart-chain-api/wallet.html",
  "/basic-docs/installations/common-runtime-parameters.html":
    "/basic-docs/smart-chains/smart-chain-setup/common-runtime-parameters.html",
  "/basic-docs/installations/creating-asset-chains.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/create-a-default-smart-chain.html",
  "/basic-docs/basic-docs/smart-chains/smart-chain-setup/installing-from-source.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/create-a-default-smart-chain.html",
  "/basic-docs/smart-chains/smart-chain-tutorials/create-a-":
    "/basic-docs/smart-chains/smart-chain-tutorials/create-a-default-smart-chain.html",
  "/basic-docs/installations/basic-instructions.html":
    "/basic-docs/smart-chains/smart-chain-setup/interacting-with-smart-chains.html",
  "/basic-docs/start-here/custom-consensus-overview.html":
    "/basic-docs/start-here/about-komodo-platform/product-introductions.html#smart-chains-antara",
  "/basic-docs/start-here/outline-for-new-developers.html":
    "/basic-docs/start-here/about-komodo-platform/orientation.html",
  "/cc/index-book-jl.html": "/cc-jl/introduction.html",
  "/komodo/install-Komodo-manually.html":
    "/basic-docs/smart-chains/smart-chain-setup/installing-from-source.html",
  "/barterDEX/barterDEX-API.html": "/mmV1/api/introduction.html",
  "/komodo/komodo-API.html":
    "/basic-docs/smart-chains/smart-chain-api/address.html",
  "/agama/add-Bitcoin-Compatible-coin-Agama-Desktop.html":
    "/gui/agama/desktop/add-Bitcoin-Compatible-coin-Agama-Desktop.html",
  "/agama/add-ERC20-token-Agama-Desktop.html":
    "/gui/agama/desktop/add-ERC20-token-Agama-Desktop.html",
  "/agama/add-Komodo-Assetchains-Agama-Desktop.html":
    "/gui/agama/desktop/add-Komodo-Assetchains-Agama-Desktop.html",
  "/agama/mobile/add-Bitcoin-Compatible-coin-Agama-Mobile.html":
    "/gui/agama/mobile/add-Bitcoin-Compatible-coin-Agama-Mobile.html",
  "/agama/mobile/add-ERC20-token-Agama-Mobile.html":
    "/gui/agama/mobile/add-ERC20-token-Agama-Mobile.html",
  "/agama/mobile/add-Komodo-Assetchains-Agama-Mobile.html":
    "/gui/agama/mobile/add-Komodo-Assetchains-Agama-Mobile.html",
  "/general/third-party-repos-resources.html":
    "/resources/third-party-repos-resources.html",
  "/general/list-all-KomodoPlatform-Project-links.html":
    "/resources/list-all-KomodoPlatform-repos-links.html",
  "/cc/activate-cc-independent-chain.html":
    "/basic-docs/antara/activate-antara-smartchain.html",
  "/basic-docs/customconsensus/activate-custom-consensus-assetchain.html":
    "/basic-docs/antara/activate-antara-smartchain.html",
  "/coins/info.html": "/komodo/info.html",
  "/cc/faq.html": "/cc-jl/faq.html",
  "/basic-docs/customconsensus/test-use-write-integrate-cc.html":
    "/basic-docs/antara/test-use-write-integrate-antara.md",
  "/barterDEX/trade.html": "/mmV1/usage/trade.html",
  "/barterDEX/list-of-all-coins-tradable.html":
    "/mmV1/coin-integration/list-of-all-coins-tradable.html",
  "/barterDEX/install-barterDEX-CLI.html":
    "/mmV1/installation/install-marketmakerV1.html",
  "/mmV1/install-marketmakerV1.html":
    "/mmV1/installation/install-marketmakerV1.html",
  "/mmV1/install-ETOMIC-marketmakerV1.html":
    "/mmV1/installation/install-marketmakerV1.html",
  "/mmV1/installation/electrum-servers-list.html":
    "/mmV1/coin-integration/electrum-servers-list.html",
  "/barterDEX/add-coin-barterDEX.html":
    "/mmV1/coin-integration/info-add-coin.html",
  "/barterDEX/get-listed-barterDEX.html":
    "/mmV1/coin-integration/coin-integration.html",
  "/home-cc.html": "/basic-docs/antara/introduction-to-antara.html",
  "/basic-docs/customconsensus/custom-consensus-instructions.html":
    "/basic-docs/antara/introduction-to-antara.html",
  "/komodo/create-Komodo-Assetchain.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/create-a-default-smart-chain.html",
  "/basic-docs/installations/creating-asset-chains.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/create-a-default-smart-chain.html",
  "/komodo/example-asset-chains.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/example-smart-chains.html",
  "/assetchains/example-asset-chains.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/example-smart-chains.html",
  "/komodo/checklist-new-coins.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/checklist-new-coin.html",
  "/assetchains/checklist-new-coin.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/checklist-new-coin.html",
  "/assetchains/create-asset-chain-single-node.html":
    "/basic-docs/smart-chains/smart-chain-tutorials/creating-a-smart-chain-on-a-single-node.html",
  "/komodo/assetchain-params.html":
    "/basic-docs/antara/antara-setup/antara-customizations.html",
  "/basic-docs/installations/asset-chain-parameters.html":
    "/basic-docs/antara/antara-setup/antara-customizations.html",
  "/komodo/installation.html":
    "/basic-docs/smart-chains/smart-chain-setup/installing-from-source.html",
  "/mmV2/LP/walkthrough.html":
    "/basic-docs/atomicdex/atomicdex-tutorials/how-to-become-a-liquidity-provider.html",
  "/komodo/debug-Komodo.html": "/qa/debug-Komodo.html",
  "/komodo/test-komodo-source-jl777-branch.html":
    "/qa/test-komodo-source-jl777-branch.html",
  "/nspv/": "/basic-docs/smart-chains/smart-chain-setup/nspv.html",
  "/basic-docs/smart-chains/komodo/setup-electrumX-server.html":
    "/komodo/setup-electrumX-server.html",
  "/notary/assetchains-guide-Komodo-Notary-Node.md":
    "/notary/smartchains-guide-Komodo-Notary-Node.md",
  "/basic-docs/basic-docs/start-here/about-komodo-platform/product-introductions.html":
    "/basic-docs/start-here/about-komodo-platform/product-introductions.html",
  "/basic-docs/atomicdex/atomicdex-beta/how-to-recover-seed-on-atomicdex-mobile.html":
    "/basic-docs/atomicdex/atomicdex-beta/recover-seed-on-atomicdex-mobile.html",
  "/basic-docs/atomicdex/atomicdex-beta/how-to-view-your-receiving-address-to-send-funds-for-trading.html":
    "/basic-docs/atomicdex/atomicdex-beta/view-your-receiving-address-to-send-funds-for-trading.html",
  "/basic-docs/atomicdex/atomicdex-beta/how-to-add-and-activate-coins-on-atomicdex-mobile.html":
    "/basic-docs/atomicdex/atomicdex-beta/add-and-activate-coins-on-atomicdex-mobile.html",
  "/basic-docs/start-here/core-technology-discussions/creating-and-distributing-a-new-komodo-smart-chain.html":
    "/basic-docs/start-here/core-technology-discussions/initial-dex-offering.html",
  "/basic-docs/atomicdex/atomicdex-api.html":
    "/basic-docs/atomicdex-api-common_structures/rational_number_note.html",
  "/basic-docs/atomicdex-api-legacy/electrum.html":
    "/basic-docs/atomicdex-api-legacy/coin_activation.html#electrum",
  "/basic-docs/atomicdex-api-legacy/enable.html":
    "/basic-docs/atomicdex-api-legacy/coin_activation.html#enable",
}

for (const oldRedirectedPath in oldDocsRedirects) {
  pathObj[oldRedirectedPath] = pathObj[oldDocsRedirects[oldRedirectedPath].split("#")[0]];
}

fs.writeFileSync(path.join(dataDir, "Redirect-map.json"), JSON.stringify(pathObj, null, 2));

const baseUrl = "https://komodoplatform.com/en/docs";
let arrRedirects = [];
const transformPaths = (obj) => {
  const lowerCaseKeys = new Set();
  const deletionTargets = new Set();

  for (const key of Object.keys(obj)) {
    const lowerKey = key.toLowerCase();
    if (lowerCaseKeys.has(lowerKey)) {
      deletionTargets.add(lowerKey); // Store the lowercase key for deletion
    } else {
      lowerCaseKeys.add(lowerKey);
    }
  }

  for (const key of deletionTargets) {
    delete obj[key];
  }

  Object.entries(obj).forEach(([key, value]) => {
    const outputString = `${key} ${baseUrl}${value};`;
    arrRedirects.push(outputString);
  });
};

transformPaths(pathObj);
fs.writeFileSync(path.join(dataDir, "Redirect-map.txt"), arrRedirects.join("\n"));
