import oldDocsFileData from './data/_fileData_old_documentation.json' assert { type: 'json' };
import redirectMap from './data/Redirect-map.json' assert { type: 'json' };

const oldDocsPaths = Object.keys(oldDocsFileData);
let oldDocsURLs = oldDocsPaths.map((url) => url.replace("/docs", "") + ".html");

function ignoreOldDocsURLs(url) {
  return (
    url.startsWith("/mmV1") ||
    url.startsWith("/notary/deprecated") ||
    url.startsWith("/mmV2/LP") ||
    url.startsWith("/basic-docs/antara/antara-tutorials/gaming-sdk-tutorial") ||
    url.endsWith("README.html")
  );
}
let relevantOldDocsURLs = oldDocsURLs.filter((url) => !ignoreOldDocsURLs(url));
const oldRedirectURLs = Object.keys(redirectMap);
const missingRedirectURLs = relevantOldDocsURLs.filter(
  (item) => !oldRedirectURLs.includes(item)
);
if (missingRedirectURLs.length > 0) {
  console.log("#### missingRedirectURLs ####");
  console.log(JSON.stringify(missingRedirectURLs, null, 2));
} else {
  console.log("No missing redirects found");
}