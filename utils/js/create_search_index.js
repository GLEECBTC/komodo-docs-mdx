import * as fs from "fs";
import { compile } from "@mdx-js/mdx";
import { slugifyWithCounter } from "@sindresorhus/slugify";
import { mdxAnnotations } from "mdx-annotations";
import path from "path";
import remarkGfm from "remark-gfm";
import { visit } from "unist-util-visit";
import { fileURLToPath } from 'url';

import { removedWords } from "./_removed_search_words.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '../../');
const pagesDir = path.resolve(__dirname, '../../src/pages');
const dataDir = path.resolve(__dirname, '../../src/data');

const listOfAllowedElementsToCheck = [
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  // "a",
  "p",
  "li",
  // "ul", // enabling this means `ul` returns `li` content(text) causing duplicates
  "pre",
  "table",
];

const textContentElementArrayToCheck = [
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "p",
  "li",
  "pre",
  "code",
  "td",
];

const jsonFile = JSON.parse(fs.readFileSync(path.join(dataDir, 'sidebar.json'), 'utf8'));

const extractSidebarTitles = (jsonData, linksArray = []) => {
  Object.values(jsonData).forEach((data) => {
    if (!data.links) {
      extractSidebarTitles(data, linksArray);
    } else {
      data.links.forEach((data) => {
        data.href = data.href.substr(1, data.href.length - 2);
      });
      linksArray.push(...data.links);
    }
  });
  return linksArray;
};
const sidebarData = extractSidebarTitles(jsonFile);
const sidebarSearchData = {};
const allMdxFileContentTree = {};
sidebarData.forEach((data) => {
  // we're doing this so as to allow for key referencing without looping through
  // the entire list for every mdxPath where this sidebarSearchData is being used
  sidebarSearchData[data.href] = data;
});

function removeDuplicateWordsAndMerge(str1, str2) {
  // Split strings into arrays of words
  const words1 = str1.split(" ").map((word) => word.trim());
  const words2 = str2.split(" ").map((word) => word.trim());

  // Create a Set to store unique words
  const uniqueWords = new Set([...words1, ...words2]);

  // Convert Set back to an array and join words into a single string
  const mergedStr = Array.from(uniqueWords).join(" ");

  return mergedStr;
}

function getMDXFiles(dir, filesList = []) {
  const files = fs.readdirSync(dir);

  files.forEach((file) => {
    const filePath = path.join(dir, file);
    const isDirectory = fs.statSync(filePath).isDirectory();

    if (isDirectory) {
      getMDXFiles(filePath, filesList); // Recursively search through subdirectories
    } else if (filePath.endsWith(".mdx")) {
      filesList.push(filePath); // Add MDX files to the list
    }
  });

  return filesList;
}

function transformFilePath(filePath, start = "src/pages/", end = "/index.mdx") {
  // Remove the src/pages (start) prefix
  const startIndex = filePath.indexOf(start) + start.length;
  const trimmedPath = filePath.substring(startIndex);

  // Remove the /index.mdx (end) suffix
  const endIndex = trimmedPath.lastIndexOf(end);
  const finalPath = trimmedPath.substring(0, endIndex);

  return finalPath;
}

const mdxFileWordsResultsWithFilePaths = {};

const getStringContentFromElement = (elementTree, contentList = []) => {
  elementTree.forEach((node) => {
    if (node.children) {
      getStringContentFromElement(node.children);
    } else {
      if (node.type === "text" && node.value.trim() !== "") {
        contentList.push(node.value);
      }
    }
  });
  return contentList;
};

// Helper function to extract text from a node and its children
function extractTextFromNode(node) {
  if (node.type === "text") {
    return node.value;
  }

  if (node.children) {
    return node.children.map(extractTextFromNode).join(" ");
  }

  return "";
}

function elementTreeChecker(mdxFilePathToCompile) {
  return async (tree) => {
    let textContentOfElement = "";
    let closestElementReference = "";
    let slugify = slugifyWithCounter();
    let documentTree = [];
    const docPath = transformFilePath(mdxFilePathToCompile);

    if (tree)
      visit(tree, ["element"], (node) => {
        if (listOfAllowedElementsToCheck.includes(node.tagName)) {
          // For searchPreview
          if (["h1", "h2", "h3", "h4", "h5", "h6"].includes(node.tagName)) {
            visit(node, "text", (text) => {
              closestElementReference = slugify(text.value);
            });
          }
          // ...

          if (node.tagName === "h1") {
            // grab page title and merge with respective sidebar title for absolute pages
            const docsPageTitle = node.children[0].value;
            const sidebarTitle = sidebarSearchData[docPath]?.title ?? "";

            mdxFileWordsResultsWithFilePaths[mdxFilePathToCompile] = {
              searchTitle: removeDuplicateWordsAndMerge(
                docsPageTitle,
                sidebarTitle
              ),
              docsPageTitle,
              path: docPath,
            };
          }
          visit(node, "element", (elementNode) => {
            if (!textContentElementArrayToCheck.includes(node.tagName)) return;
            const completeText = extractTextFromNode(elementNode);
            if (!!completeText.trim()) {
              // For searchPreview
              let lineData = {
                text: completeText,
                tagName: elementNode.tagName,
                path: docPath,
                closestElementReference,
              };
              documentTree.push(lineData);
              // ...

              textContentOfElement = textContentOfElement.concat(
                " ",
                completeText
              );
            }
            return visit.SKIP;
          });
        }
      });

    allMdxFileContentTree[docPath] = documentTree;

    const finalText = textContentOfElement
      .toLocaleLowerCase()
      .trim()
      .replace(/[.]+/gm, " ")
      .replace(/[^a-z _-]+/gm, " ")
      .split(" ");

    const wordCountObj = {};
    finalText.forEach((word) => {
      if (
        !removedWords.some((removedWord) => removedWord === word) &&
        !hasOnlyHyphens(word)
      )
        if (word.length > 1)
          if (wordCountObj[word]) wordCountObj[word] = wordCountObj[word] + 1;
          else wordCountObj[word] = 1;
    });
    mdxFileWordsResultsWithFilePaths[mdxFilePathToCompile].content =
      wordCountObj;
  };
}

function hasOnlyHyphens(str) {
  return /^-+$/.test(str);
}

async function compileMdxFile(mdxFilePathToCompile) {
  const mdxFileResultString = fs.readFileSync(mdxFilePathToCompile, "utf8");
  return await compile(mdxFileResultString, {
    remarkPlugins: [mdxAnnotations.remark, remarkGfm],
    rehypePlugins: [
      mdxAnnotations.rehype,
      () => elementTreeChecker(mdxFilePathToCompile),
    ],
    recmaPlugins: [mdxAnnotations.recma],
  });
}

const runSearchIndexingOnAllMdxFiles = async () => {
  try {
    const mdxFiles = getMDXFiles(pagesDir);
    for (let index = 0; index < mdxFiles.length; index++) {
      const file = mdxFiles[index];
      try {
        await compileMdxFile(file);
      } catch (error) {
        throw new Error(`Processing file:${file} 
          ${error}`);
      }
    }
    fs.writeFileSync(path.join(projectRoot, '_searchIndex.json'), JSON.stringify(mdxFileWordsResultsWithFilePaths));
    fs.writeFileSync(path.join(projectRoot, '_allMdxFileContentTree.json'), JSON.stringify(allMdxFileContentTree));
  } catch (error) {
    throw new Error(error);
  }
};
runSearchIndexingOnAllMdxFiles();
