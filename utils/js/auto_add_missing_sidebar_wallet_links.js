import fs from "fs";
import path from "path";

const SIDEBAR_FILE = "./src/data/sidebar.json";
const PAGES_ROOT = "./src/pages";
const V20_WALLET_PREFIX = "/komodo-defi-framework/api/v20/wallet/";
const V20_ROOT_KEY = "/komodo-defi-framework/api/v20/";
const NAV_ROOT = "komodefiApi20MasterPageNavigation";
const TARGET_SECTION_TITLE = "Wallet";

function walkDir(dirPath, onFile) {
  fs.readdirSync(dirPath).forEach((file) => {
    const filePath = path.join(dirPath, file);
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) {
      walkDir(filePath, onFile);
    } else {
      onFile(filePath);
    }
  });
}

function collectAllPageHrefsFromSidebar(sidebarData) {
  const hrefs = new Set();
  Object.keys(sidebarData).forEach((navKey) => {
    const navigation = sidebarData[navKey];
    Object.keys(navigation).forEach((basePath) => {
      const sections = navigation[basePath];
      sections.forEach((section) => {
        if (section.titleLink) {
          hrefs.add(section.titleLink);
        }
        if (Array.isArray(section.links)) {
          section.links.forEach((l) => {
            if (l && l.href) hrefs.add(l.href);
          });
        }
      });
    });
  });
  return hrefs;
}

function ensureTrailingSlash(s) {
  return s.endsWith("/") ? s : s + "/";
}

function deriveTitleFromHref(href) {
  const parts = href.split("/").filter(Boolean);
  return parts[parts.length - 1] || href;
}

function findWalletSection(sidebarData) {
  if (!sidebarData[NAV_ROOT] || !sidebarData[NAV_ROOT][V20_ROOT_KEY]) return null;
  const sections = sidebarData[NAV_ROOT][V20_ROOT_KEY];
  for (const section of sections) {
    if (section.title === TARGET_SECTION_TITLE && Array.isArray(section.links)) {
      return section;
    }
  }
  return null;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.log("[auto-add-sidebar] No target hrefs provided. No changes made.");
    console.log(`[auto-add-sidebar] Usage: node ${path.basename(process.argv[1])} /komodo-defi-framework/api/v20/wallet/fetch_utxos/ [/komodo-defi-framework/api/v20/wallet/another/]`);
    return;
  }

  const sidebarData = JSON.parse(fs.readFileSync(SIDEBAR_FILE, "utf8"));
  const allSidebarHrefs = collectAllPageHrefsFromSidebar(sidebarData);
  const walletSection = findWalletSection(sidebarData);
  if (!walletSection) {
    console.warn(
      `[auto-add-sidebar] Could not find '${TARGET_SECTION_TITLE}' section under ${NAV_ROOT}.${V20_ROOT_KEY}. No changes made.`
    );
    return;
  }

  const additions = [];
  for (let rawHref of args) {
    let href = ensureTrailingSlash(rawHref.trim());
    if (!href.startsWith(V20_WALLET_PREFIX)) {
      console.warn(`[auto-add-sidebar] Skipping non-wallet href: ${href}`);
      continue;
    }
    if (allSidebarHrefs.has(href)) {
      console.log(`[auto-add-sidebar] Already present, skipping: ${href}`);
      continue;
    }
    const title = deriveTitleFromHref(href);
    walletSection.links.push({ title, href });
    additions.push({ title, href });
  }

  if (additions.length > 0) {
    fs.writeFileSync(SIDEBAR_FILE, JSON.stringify(sidebarData, null, 2) + "\n");
    additions.forEach(({ href }) => {
      console.log(
        `[auto-add-sidebar] Added missing page to sidebar (derived placement): ${href} -> ${NAV_ROOT}.${V20_ROOT_KEY}['${TARGET_SECTION_TITLE}']`
      );
    });
  } else {
    console.log("[auto-add-sidebar] No additions needed. No changes made.");
  }
}

main();

