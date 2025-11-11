import fs from "fs";

const SIDEBAR_FILE = "./src/data/sidebar.json";

function main() {
  const sidebarData = JSON.parse(fs.readFileSync(SIDEBAR_FILE, "utf8"));
  let removed = 0;

  if (!sidebarData["komodefiApi20MasterPageNavigation"] || !sidebarData["komodefiApi20MasterPageNavigation"]["/komodo-defi-framework/api/v20/"]) {
    console.log("[cleanup-sidebar] v20 navigation not found. No changes made.");
    return;
  }
  const sections = sidebarData["komodefiApi20MasterPageNavigation"]["/komodo-defi-framework/api/v20/"];
  for (const section of sections) {
    if (section.title === "Wallet" && Array.isArray(section.links)) {
      const before = section.links.length;
      section.links = section.links.filter((l) => !(l && typeof l.href === "string" && l.href.startsWith("src/pages/")));
      removed += before - section.links.length;
    }
  }

  if (removed > 0) {
    fs.writeFileSync(SIDEBAR_FILE, JSON.stringify(sidebarData, null, 2) + "\n");
    console.log(`[cleanup-sidebar] Removed ${removed} bad wallet href entries starting with 'src/pages/'.`);
  } else {
    console.log("[cleanup-sidebar] No bad wallet href entries found. No changes made.");
  }
}

main();

