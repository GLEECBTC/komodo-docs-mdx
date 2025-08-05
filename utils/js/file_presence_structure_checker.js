import { fileURLToPath } from 'url';
import path from 'path';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
import * as fs from "fs";

const pagesDir = path.resolve(__dirname, '../../src/pages');
const dataDir = path.resolve(__dirname, '../../src/data');

const sidebarNavData = JSON.parse(fs.readFileSync(path.join(dataDir, 'sidebar.json'), 'utf8'))
const navbarNavData = JSON.parse(fs.readFileSync(path.join(dataDir, 'navbar.json'), 'utf8'))

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
const dirsWithNoIndex = [];
let filesOtherThanIndex = [];

function findMissingIndexInDirs(dirPath) {
  let foundIndexFile = false;
  let otherFilesInDir = [];
  const pathsInDir = fs.readdirSync(dirPath);
  for (let i = 0; i < pathsInDir.length; i++) {
    let curPath = path.join(dirPath, pathsInDir[i]);
    let stat = fs.statSync(curPath);
    if (stat.isDirectory()) {
      findMissingIndexInDirs(curPath);
    } else {
      if (curPath.endsWith("index.mdx")) {
        foundIndexFile = true;
      } else if (
        !(curPath.endsWith("/_app.tsx") || curPath.endsWith("/_document.tsx") || curPath.toLowerCase().includes(".ds_store"))
      ) {
        otherFilesInDir.push(curPath);
      }
    }
  }
  if (!foundIndexFile) {
    dirsWithNoIndex.push(dirPath + "/");
  }
  if (otherFilesInDir.length > 0) {
    filesOtherThanIndex = [...filesOtherThanIndex, ...otherFilesInDir];
  }
}

findMissingIndexInDirs(pagesDir);

// check if every dir contains a index.mdx file and if every page is present in sidebar.json

const fileNames = [];
const getFileNames = (filepath) => {
  if (
    !(filepath.endsWith("/_app.tsx") || filepath.endsWith("/_document.tsx") || filepath.toLowerCase().includes(".ds_store"))
  ) {
    let filePathURL = filepath
      .replace(pagesDir, "")
      .replace("index.mdx", "");
    fileNames.push(filePathURL);
  }
};

function isValidUrl(urlString) {
  try {
    new URL(urlString);
    return true;
  } catch (error) {
    return false;
  }
}

walkDir(pagesDir, getFileNames);

const invalidFilenames = fileNames.filter(fileName => {
  return isValidUrl("https://www.example.com" + fileName) && /[A-Z]/.test(fileName)
})

if (invalidFilenames.length > 0) {
  throw new Error("following file names are invalid. Either can't form valid url or has uppercase letters in them: " + JSON.stringify(invalidFilenames))
}

const sidebarPagesArray = [];
const navbarPagesArray = [];

function readTitleLinksAndHrefsNavbar(data) {
  Object.keys(data).forEach(function (key) {
    var dropdown = data[key];
    dropdown.items.forEach(function (item) {
      if (!item.link.endsWith("/")) {
        throw new Error(`In navbar.json, link: ${item.link} should end with /`)
      }
      navbarPagesArray.push(item.link)
    });
  });
}

function readTitleLinksAndHrefsSidebar(data) {
  Object.keys(data).forEach(function (key) {
    var navigation = data[key];
    Object.keys(navigation).forEach(function (navigationKey) {
      if (!navigationKey.endsWith("/")) {
        throw new Error(`In sidebar.json, navigationKey: ${navigationKey} should end with /`)
      }
      var sections = navigation[navigationKey];
      sections.forEach(function (page) {
        if (page.titleLink && page.links && page.links.length > 0) {
          throw new Error("To be able to have collapsible sections in left sidebar, title with titlelink can't have sub-items. 'page.titleLink': " + page.titleLink)
        }
        if (page.titleLink) {
          if (!page.titleLink.endsWith("/")) {
            throw new Error(`In sidebar.json, titleLink: ${page.titleLink} should end with /`)
          }
          sidebarPagesArray.push(page.titleLink);
        }
        if (page.links) {
          for (const link of page.links) {
            if (!link.href) {
              throw new Error(`In sidebar.json, link: ${JSON.stringify(link)}`)
            }
            if (!link.href.endsWith("/")) {
              throw new Error(`In sidebar.json, link: ${link.href} should end with /`)
            }
            sidebarPagesArray.push(link.href);
          }
        }
      });
    });
  });
}

// Read titleLinks and links.href values from antaraFrameworkPageNavigation

readTitleLinksAndHrefsSidebar(sidebarNavData);
readTitleLinksAndHrefsNavbar(navbarNavData);

function compareArrays(fileNames, pagesArray) {
  var differences = [];
  fileNames.forEach(function (fileName) {
    if (!pagesArray.includes(fileName)) {
      differences.push(fileName);
    }
  });

  return differences;
}

//pages present in the file system but not in sidebar
var pagesNotInSidebar = compareArrays(fileNames, sidebarPagesArray);
//pages present in the sidebar but not in file system
var pagesInSidebarNotInFileSystem = compareArrays(sidebarPagesArray, fileNames);

var pagesInNavbarNotInFileSystem = compareArrays(navbarPagesArray, fileNames)

function removeUndefinedStrings(array) {
  return array.filter(function (element) {
    return element !== undefined;
  });
}

let errorString = "";

if (pagesNotInSidebar.length > 0) {
  errorString =
    errorString +
    `\npages present in the file system but not in sidebar:
${pagesNotInSidebar.join("\n")}
`;
}

if (pagesInSidebarNotInFileSystem.length > 0) {
  errorString =
    errorString +
    `\npages present in the sidebar but not in file system:
${pagesInSidebarNotInFileSystem.join("\n")}
`;
}

if (pagesInNavbarNotInFileSystem.length > 0) {
  errorString =
    errorString +
    `\npages present in the navbar but not in file system:
${pagesInNavbarNotInFileSystem.join("\n")}
`;
}

if (dirsWithNoIndex.length > 0) {
  errorString =
    errorString +
    `\nDirectories without index file: 
${dirsWithNoIndex.join("\n")}
Create index.mdx files with the appropriate content for above directories.
`;
}

if (filesOtherThanIndex.length > 0) {
  errorString =
    errorString +
    `\nFiles other than index found:
${filesOtherThanIndex.join("\n")}
Replace these files with directories of same name and create index.mdx files inside them with the same content.\n
`;
}

if (errorString !== "") {
  throw new Error(errorString);
} else {
  console.log("file presence checker generated no errors.")
}