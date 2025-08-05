import * as acorn from "acorn";

import { SKIP, visit } from "unist-util-visit";
import { visitParents } from 'unist-util-visit-parents'

import { constants } from "fs";
import fs from "fs";
import http from "http";
import https from "https";
import { is } from "unist-util-is";
import { mdxAnnotations } from "mdx-annotations";
import path from "path";
import { remark } from "remark";
import remarkGfm from "remark-gfm";
import remarkMdx from "remark-mdx";
import slugify, { slugifyWithCounter } from "@sindresorhus/slugify";
import { toString } from "mdast-util-to-string";
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pagesDir = path.resolve(__dirname, '../../src/pages');
const dataDir = path.resolve(__dirname, './data');
const projectRoot = path.resolve(__dirname, '../../');

const manualLinkFile = "links-to-manually-check";
if (fs.existsSync(manualLinkFile)) {
  fs.unlinkSync(manualLinkFile);
}

(async function () {
  try {
    let filepaths = [];
    walkDir(pagesDir, (filepath) => {
      if (!filepath.toLowerCase().includes(".ds_store")) {
        filepaths.push(filepath)
      }
    });
    await createFileSlugs(filepaths); // can comment on repeat runs, while fixing internal links and not changing headings in content

    let filepathSlugs = JSON.parse(fs.readFileSync(path.join(dataDir, "filepathSlugs.json")));
    for (let index = 0; index < filepaths.length; index++) {
      const filePath = filepaths[index];
      await processFile(filePath, filepathSlugs);
    }
  } catch (error) {
    if (error) throw error;
  }
})();

async function createFileSlugs(filepaths) {
  const filepathSlugs = {};

  for (let index = 0; index < filepaths.length; index++) {
    const filePath = filepaths[index];
    try {
      await remark()
        .use(mdxAnnotations.remark)
        .use(remarkMdx)
        .use(() => (tree) => {
          const slugs = [];

          let slugify = slugifyWithCounter();
          // Visit all heading nodes and collect their values while rejecting the ones in DevComment
          visitParents(tree, "heading", (node, ancestors) => {
            if (!ancestors.some((ancestor) => ancestor.name === "DevComment")) {
              const slug = slugify(toString(node));
              slugs.push(slug);
            }
          });
          filepathSlugs[filePath] = slugs;
        })
        .process(fs.readFileSync(filePath, "utf-8"));
    } catch (error) {
      console.log(error);
      throw new Error(`filePath: ${filePath}`);
    }
  }

  fs.writeFileSync(
    path.join(dataDir, "filepathSlugs.json"),
    JSON.stringify(filepathSlugs, null, 2)
  );
}

async function processFile(filePath, filepathSlugs) {
  if (!filePath.endsWith("/index.mdx")) {
    throw new Error("File path doesn't end with '/index.mdx': " + filePath);
  }
  // if (filePath.includes("setup/dexp2p")) {
  //   throw new Error("dexp2p': " + filePath);
  // }
  // if (!filePath.includes("/smart-chains/setup/dexp2p")) {
  //   return
  // }
  console.log("Processing: " + filePath);
  const file = await remark()
    .use(remarkGfm)
    .use(remarkMdx)
    .use(() => (tree) => {
      hasValidTitleDescExportsImgImports(tree.children, filePath);
    })
    .use(() => (tree) => {
      visit(tree, "link", (node) => {
        //Process internal links
        const isExternalURL = /^https?:\/\//;
        if (!isExternalURL.test(node.url)) {
          node.url = processInternalLink(node.url, filePath, filepathSlugs);
        }
      });
    })
    .use(() => (tree) => {
      visit(tree, (node, nodeIndex, parentNode) => {
        // if (!filePath.includes("src/pages/komodo-defi-framework")) {
        //   return SKIP;
        // }

        try {
          if (
            is(node, { name: "CodeGroup" }) &&
            node.attributes.some(
              (attr) =>
                attr.type === "mdxJsxAttribute" &&
                attr.name === "mm2MethodDecorate" &&
                attr.value === "true"
            )
          ) {
            // console.log(node)
            const originalChild = node.children[0];
            if (node.children.length !== 1 || originalChild.lang !== "json") {
              throw new Error(
                `unexpected code block in file ${filePath} : ` +
                JSON.stringify()
              );
            }
            const clonedChild = JSON.parse(JSON.stringify(originalChild));
            let methodObj = JSON.parse(clonedChild.value);
            methodObj.userpass = "RPC_UserP@SSW0RD";
            clonedChild.value = JSON.stringify(methodObj, null, 2);
            //console.log(clonedChild)
            node.children = [clonedChild];
            return SKIP;
          } else if (node.type === "code" && node.lang === null) {
            console.log(`Code lang value missing in file: ${filePath}, line: ${node.position.start.line}`);
            throw new Error(`Code lang value missing
Filepath: ${filePath} 
code node: 
${JSON.stringify(node, null, 2)}`);
          }
        } catch (error) {
          throw new Error(`Error:
${JSON.stringify(error, null, 2)}         
Filepath: ${filePath} 
Node: 
${JSON.stringify(node, null, 2)}`);
        }
      });
    })
    .process(fs.readFileSync(filePath, "utf-8"));
  if (file) {
    fs.writeFileSync(filePath, String(file));
  }
}
// Function to process a link
function processInternalLink(link, currFilePath, filepathSlugs) {
  if (link.startsWith("mailto:")) {
    return link;
  }

  let filePath = pagesDir;
  let strippedPath = link.split("#")[0]; // strips hash
  if (strippedPath.endsWith("/")) {
    strippedPath = strippedPath.slice(0, -1);
  }
  const hash = link.split("#")[1];
  let correctUrl;
  let currNormalisedDir;
  const currentWorkingDirectory = process.cwd();
  currNormalisedDir = currFilePath.replace("/index.mdx", "").split("/");
  currNormalisedDir.pop();
  currNormalisedDir = currNormalisedDir.join("/");
  if (
    strippedPath.endsWith(".md") ||
    strippedPath.endsWith(".html") ||
    strippedPath.endsWith(".mdx")
  ) {
    let newStrippedPart = strippedPath.split(".");
    newStrippedPart.pop();
    newStrippedPart = newStrippedPart.join(".");
    newStrippedPart = newStrippedPart.split("/");
    let fileName = newStrippedPart.pop();
    if (fileName !== "index") {
      correctUrl = strippedPath
        .replace(".html", "/")
        .replace(".md", "/")
        .replace(".mdx", "/");
      correctUrl =
        path.join(path.resolve(currNormalisedDir, correctUrl) + "/") +
        (hash ? `#${hash}` : "");
    }
    newStrippedPart = newStrippedPart.join("/");
    strippedPath = newStrippedPart;
  }
  if (!correctUrl) {
    if (strippedPath === "") {
      correctUrl =
        currFilePath
          .replace("index.mdx", "")
          .replace(path.join(filePath + "/").slice(0, -1), "") +
        (hash ? `#${hash}` : "");
    } else {
      correctUrl =
        path.join(path.resolve(currNormalisedDir, strippedPath), "/") +
        (hash ? `#${hash}` : "");
    }
  }
  correctUrl = correctUrl.replace(
    path.join(currentWorkingDirectory, filePath),
    ""
  );
  const correctUrlSplit = correctUrl.split("#");
  const internalLinkFile = path.join(
    filePath,
    correctUrlSplit[0] + "index.mdx"
  );
  let slug = "";
  if (correctUrlSplit[1]) {
    //trying to fix slugs with _

    //slugifyWithCounter stuff was used as a mistake here earlier
    //let slugify = slugifyWithCounter();
    slug = slugify(correctUrlSplit[1]);
    correctUrl = correctUrlSplit[0] + "#" + slug;
  }

  // Enforce that main Komodo DeFi Framework API index links point to method headings, not subsections
  // Unlike the other sections, the slug is not based on path, but on the method heading
  if (currFilePath.endsWith("src/pages/komodo-defi-framework/api/index.mdx") && 
      (correctUrl.includes("/api/v20/") || correctUrl.includes("/api/v20-dev/") || correctUrl.includes("/api/legacy/"))) {
    console.log("correctUrl: " + correctUrl);
    const fileContent = fs.readFileSync(internalLinkFile, 'utf-8');
    const lines = fileContent.split('\n');
    let methodHeading = null;
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('## ')) {
        // Extract the heading text before any {{label ...}}
        methodHeading = trimmed.slice(3).split('{{')[0].trim();
        console.log("methodHeading: " + methodHeading);
        break;
      }
    }
    if (!methodHeading) {
      throw new Error(`Could not find main method heading (## ...) in file: ${internalLinkFile}`);
    }
    slug = slugify(methodHeading);
    correctUrl = correctUrlSplit[0] + "#" + slug;
  }

  if (!Object.hasOwn(filepathSlugs, internalLinkFile)) {
    console.log("#----------------------------------------------#");
    console.log("currNormalisedDir: " + currNormalisedDir);
    console.log("currFilePath: " + currFilePath);
    console.log("strippedPath: " + strippedPath);
    console.log("link: " + link);
    console.log("correctUrl: " + correctUrl);
    console.log("internalLinkFile: " + internalLinkFile);
    console.log("slug: " + slug);
    console.log("#----------------------------------------------#");
    throw new Error(
      `Processing file: ${currFilePath}, slug: ${slug} (original slug: ${correctUrlSplit[1]} ) has updated url: ${correctUrl} (original url: ${link}), but the file: ${internalLinkFile} is missing`
    );
  } else if (
    slug !== "" &&
    !filepathSlugs[internalLinkFile].some((slugO) => slug === slugO)
  ) {
    console.log("##------------------------------------------------##");
    console.log("currNormalisedDir: " + currNormalisedDir);
    console.log("currFilePath: " + currFilePath);
    console.log("strippedPath: " + strippedPath);
    console.log("link: " + link);
    console.log("correctUrl: " + correctUrl);
    console.log("internalLinkFile: " + internalLinkFile);
    console.log("slug: " + slug);
    console.log("##------------------------------------------------##");
    throw new Error(
      `Processing file: ${currFilePath}, slug: ${slug} (original slug: ${correctUrlSplit[1]} ) not present in file: ${internalLinkFile}`
    );
  }
  try {
    fs.accessSync(internalLinkFile, constants.F_OK);
  } catch (err) {
    console.log("currNormalisedDir:" + currNormalisedDir);
    console.log("currFilePath: " + currFilePath);
    console.log("strippedPath: " + strippedPath);
    console.log("link: " + link);
    console.log("correctUrl: " + correctUrl);
    console.log(
      "Internal link file doesn't exist/can't access it: " + internalLinkFile
    );
    throw new Error(err);
  }
  return correctUrl;
}

// needs import { promises as fs } from 'fs';
// async function asyncWalkDir(dir, callback) {
//     let files = await fs.readdir(dir);
//     await Promise.all(files.map(async (file) => {
//         const filePath = path.join(dir, file);
//         const stats = await fs.stat(filePath);
//         if (stats.isDirectory()) {
//             await walkDir(filePath, callback);
//         } else if (stats.isFile()) {
//             await callback(filePath);
//         }
//     }));
// }

export function walkDir(dirPath, callback) {
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

function hasValidTitleDescExportsImgImports(children, filePath) {
  const expImpChildren = children.filter((node) => node.type === "mdxjsEsm");
  let titleExportedCount = 0;
  let descriptionExportedCount = 0;
  let invalidImagePaths = [];
  let imagesNotFound = []

  for (const node of expImpChildren) {
    try {
      const parsed = acorn.parse(node.value, {
        sourceType: "module",
        ecmaVersion: 2020,
      });

      for (const node of parsed.body) {
        if (node.type === "ExportNamedDeclaration") {
          if (node.declaration && node.declaration.declarations) {
            for (const declaration of node.declaration.declarations) {
              if (
                declaration.id.name === "title" &&
                declaration.init.type === "Literal"
              ) {
                titleExportedCount = titleExportedCount + 1;
                // let numChars = declaration.init.value.length;
                // if (numChars > 60) {
                //   throw new Error(`Title: "${declaration.init.value}" has ${numChars} characters, which is greater than 60`)
                // }
              }
              if (
                declaration.id.name === "description" &&
                declaration.init.type === "Literal"
              ) {
                descriptionExportedCount = descriptionExportedCount + 1;
                // let numChars = declaration.init.value.length;
                // if (numChars > 160 || numChars < 140) {
                //   throw new Error(`Description: "${declaration.init.value}" has ${numChars} characters, which is not between 140 and 160`)
                // }
              }
            }
          }
        } else if (node.type === "ImportDeclaration" && node.source.type === "Literal") {
          const importImgPath = node.source.value
          if (!importImgPath.startsWith("@/public/images/docs")) {
            invalidImagePaths.push(importImgPath)
          } else {
            let imagePath = importImgPath.startsWith("@/public/images/docs")
                ? importImgPath.replace("@/public/images/docs", "src/images")
                : importImgPath;
            const absImagePath = path.resolve(projectRoot, imagePath);
            if (!fs.existsSync(absImagePath)) {
              imagesNotFound.push(absImagePath)
            }
          }
        }
      }
    } catch (e) {
      console.log(`Error in file: ${filePath}`);
      console.log(`Error in node: ${JSON.stringify(node, null, 2)}`);
      throw new Error(e);
    }
  }

  let errorString = `Processing file: ${filePath}
  ${titleExportedCount !== 1 ? `Title exported ${titleExportedCount} times` : ""}
  ${descriptionExportedCount !== 1 ? `Description exported ${descriptionExportedCount} times` : ""}
  ${invalidImagePaths.length > 0 ? `Invalid image paths (must start with '@/public/images/docs'): \n${invalidImagePaths.join(",\n")}` : ""}
  ${imagesNotFound.length > 0 ? `Images not found in filesystem: \n${imagesNotFound.join(",\n")}` : ""}
  
  `
  if (titleExportedCount !== 1 || descriptionExportedCount !== 1 || invalidImagePaths.length > 0 || imagesNotFound.length > 0) {
    throw new Error(errorString);
  }
}

function checkUrlStatusCode(url) {
  return new Promise((resolve, reject) => {
    let client;

    if (url.startsWith("https://")) {
      client = https;
    } else if (url.startsWith("http://")) {
      client = http;
    } else {
      reject(new Error("URL must start with http:// or https://"));
      return;
    }
    let requestOptions = new URL(url);
    requestOptions.headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.5",
      Referer: "https://www.google.com/",
    };

    const req = client.get(requestOptions, (response) => {
      if (
        response.statusCode >= 300 &&
        response.statusCode < 400 &&
        response.headers.location
      ) {
        resolve({
          newLocation: response.headers.location,
          statusCode: response.statusCode,
        });
      } else {
        resolve({
          newLocation: "",
          statusCode: response.statusCode,
        });
      }
    });
    req.on("error", (err) => {
      reject(err);
    });
    req.setTimeout(100, () => {
      req.destroy();
      reject(new Error("Request timed out " + url));
    });
  });
}

async function processExternalLink(link, currFilePath) {
  //TODO: check the ignore lists ocassionally to determine their status and maybe check for replacements
  let IgnoreURLs = [
    "https://moralis-proxy.komodo.earth",
    "https://nft.antispam.dragonhound.info",
    "https://www.digitalocean.com/community/tutorials/how-to-add-delete-and-grant-sudo-privileges-to-users-on-a-debian-vps",
    "https://www.virustotal.com/gui/"
  ];
  if (IgnoreURLs.some((ignoreLink) => link.includes(ignoreLink))) {
    fs.appendFileSync(manualLinkFile, link + "\n");
    return
  }
  if (
    link.startsWith("http://127.0.0.1") ||
    link.startsWith("https://127.0.0.1") ||
    link.startsWith("http://localhost") ||
    link.startsWith("https://localhost")
  ) {
    return;
  }
  if (
    link.startsWith("http://twitter.com") ||
    link.startsWith("https://twitter.com")
  ) {
    return;
  }
  if (
    link.startsWith("http://komodoplatform.com/discord") ||
    link.startsWith("https://komodoplatform.com/discord")
  ) {
    return;
  }
  if (
    link.startsWith("http://bitcointalk.org") ||
    link.startsWith("https://bitcointalk.org")
  ) {
    return;
  }
  if (
    link.startsWith("http://telegram.org/") ||
    link.startsWith("https://telegram.org/")
  ) {
    return;
  }
  if (
    link.startsWith("http://notarystats.info") ||
    link.startsWith("https://notarystats.info")
  ) {
    return;
  }

  try {
    const { newLocation, statusCode } = await checkUrlStatusCode(link);
    if (statusCode === 200) {
      //console.log("The external URL exists: " + link);
      return;
    } else if (
      statusCode === 301 ||
      statusCode === 302 ||
      statusCode === 308 ||
      statusCode === 307
    ) {
      throw new Error(
        `The link: ${link} has a ${statusCode} redirect to ${newLocation}`
      );
    } else if (statusCode === 403 || statusCode === 405 || statusCode === 500) {
      // console.log(
      //   `Check this link manually: [${link}] It responds with statuscode: ${statusCode} `
      // );
      fs.appendFileSync(manualLinkFile, link + "\n");
    } else {
      throw new Error(
        `The URL ${link} in the file ${currFilePath} returned a statuscode: ${statusCode}`
      );
    }
  } catch (err) {
    if (err.message.startsWith("Request timed out")) {
      console.log(
        `Request timed out when checking the URL ${link} in the file ${currFilePath}`
      );
      return;
    }
    else if (err.message.includes("ETIMEDOUT")) {
      console.log(`Request timed out when checking the URL ${link} in the file ${currFilePath}`);
      return;
    } else {
      console.error(`Error when checking the URL ${link} in the file ${currFilePath}`)
      fs.appendFileSync(manualLinkFile, link + "\n");
      fs.appendFileSync(manualLinkFile, JSON.stringify(err, null, 2) + "\n");
      fs.appendFileSync(manualLinkFile, "\n");

      //throw new Error(err);
    }
  }
}

function isValidJSON(str) {
  try {
    JSON.parse(str);
    return true; // Parsing succeeded, string is valid JSON
  } catch (e) {
    return false; // Parsing failed, string is not valid JSON
  }
}
