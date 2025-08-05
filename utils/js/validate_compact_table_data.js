#!/usr/bin/env node

/**
 * Comprehensive validation script for CompactTable data
 * 
 * This script validates:
 * 1. All CompactTable source references in MDX files exist in JSON files
 * 2. All JSON files have valid structure and value types (schema validation)
 * 3. All internal hyperlinks in descriptions within JSON files are valid
 */

import * as acorn from "acorn";
import { visit } from "unist-util-visit";
import { visitParents } from 'unist-util-visit-parents';
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
import Ajv from "ajv";

const TABLES_DIR = "./src/data/tables";
const PAGES_DIR = "./src/pages";
const SCHEMA_PATH = "./src/data/schemas/compact-table.schema.json";

let validationErrors = [];
let validationWarnings = [];

// Load the schema
let schema;
try {
  schema = JSON.parse(fs.readFileSync(SCHEMA_PATH, "utf-8"));
} catch (error) {
  console.error(`❌ Failed to load schema from ${SCHEMA_PATH}: ${error.message}`);
  process.exit(1);
}

/**
 * Walk directory recursively and collect files
 */
function walkDir(dirPath, callback) {
  if (!fs.existsSync(dirPath)) {
    return;
  }
  
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

/**
 * Load all JSON table files from the tables directory
 */
function loadTableFiles() {
  const tableFiles = {};
  
  walkDir(TABLES_DIR, (filePath) => {
    if (filePath.endsWith('.json')) {
      try {
        const relativePath = path.relative(TABLES_DIR, filePath);
        const content = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        
        // Use the filename without extension as the key
        const fileKey = path.basename(filePath, '.json');
        const dirPath = path.dirname(relativePath);
        
        // Create a unique key that includes subdirectory structure
        const fullKey = dirPath === '.' ? fileKey : `${dirPath.replace(/\//g, '-')}-${fileKey}`;
        
        // Store with the full key first to avoid conflicts
        if (fullKey !== fileKey) {
          tableFiles[fullKey] = {
            path: filePath,
            content: content,
            relativePath: relativePath
          };
        }
        
        // Store simple filename, but prefer common-structures over v2
        if (!tableFiles[fileKey] || relativePath.startsWith('common-structures/')) {
          tableFiles[fileKey] = {
            path: filePath,
            content: content,
            relativePath: relativePath
          };
        }
        
        console.log(`📋 Loaded table file: ${fileKey} (${relativePath})`);
      } catch (error) {
        validationErrors.push(`Failed to parse JSON file ${filePath}: ${error.message}`);
      }
    }
  });
  
  return tableFiles;
}

/**
 * Validate JSON structure against schema
 */
function validateJsonStructure(tableFiles) {
  console.log('\n🔍 Validating JSON structure against schema...');
  
  const ajv = new Ajv();
  const validate = ajv.compile(schema);
  
  let structureValid = true;
  
  Object.entries(tableFiles).forEach(([fileKey, fileData]) => {
    const isValid = validate(fileData.content);
    
    if (!isValid) {
      structureValid = false;
      validationErrors.push(`Schema validation failed for ${fileData.path}:`);
      validate.errors.forEach(error => {
        validationErrors.push(`  - ${error.instancePath}: ${error.message}`);
      });
    } else {
      const tableCount = Object.keys(fileData.content).length;
      const totalParams = Object.values(fileData.content).reduce((sum, table) => sum + table.data.length, 0);
      console.log(`  ✅ ${fileKey}: ${tableCount} tables, ${totalParams} parameters`);
    }
  });
  
  return structureValid;
}

/**
 * Find all CompactTable source references in MDX files
 */
function findCompactTableReferences() {
  console.log('\n🔍 Finding CompactTable references in MDX files...');
  
  const references = [];
  const mdxFiles = [];
  
  walkDir(PAGES_DIR, (filePath) => {
    if (filePath.endsWith('.mdx')) {
      mdxFiles.push(filePath);
    }
  });
  
  mdxFiles.forEach(filePath => {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      
      // Find CompactTable components with source attributes
      const sourceRegex = /<CompactTable[^>]*source="([^"]+)"[^>]*\/?>/g;
      let match;
      
      while ((match = sourceRegex.exec(content)) !== null) {
        const sourceRef = match[1];
        references.push({
          file: filePath,
          source: sourceRef,
          line: content.substring(0, match.index).split('\n').length
        });
      }
    } catch (error) {
      validationErrors.push(`Failed to read MDX file ${filePath}: ${error.message}`);
    }
  });
  
  console.log(`  📊 Found ${references.length} CompactTable references in ${mdxFiles.length} MDX files`);
  return references;
}

/**
 * Validate that all CompactTable references exist in JSON files
 */
function validateCompactTableReferences(references, tableFiles) {
  console.log('\n🔍 Validating CompactTable source references...');
  
  let referencesValid = true;
  
  references.forEach(ref => {
    const [fileName, tableName] = ref.source.split('.');
    
    if (!fileName || !tableName) {
      validationErrors.push(`Invalid source format "${ref.source}" in ${ref.file}:${ref.line} (expected format: "filename.tablename")`);
      referencesValid = false;
      return;
    }
    
    const tableFile = tableFiles[fileName];
    if (!tableFile) {
      validationErrors.push(`Table file "${fileName}" not found for reference "${ref.source}" in ${ref.file}:${ref.line}`);
      referencesValid = false;
      return;
    }
    
    if (!tableFile.content[tableName]) {
      validationErrors.push(`Table "${tableName}" not found in file "${fileName}" for reference "${ref.source}" in ${ref.file}:${ref.line}`);
      referencesValid = false;
      return;
    }
    
    console.log(`  ✅ ${ref.source} → ${tableFile.relativePath}`);
  });
  
  return referencesValid;
}

/**
 * Create file slugs for internal link validation (adapted from validate_update_internal_links_userpass.js)
 */
async function createFileSlugs() {
  console.log('\n🔍 Creating file slugs for internal link validation...');
  
  const filepaths = [];
  walkDir(PAGES_DIR, (filepath) => {
    if (filepath.endsWith('/index.mdx') && !filepath.toLowerCase().includes(".ds_store")) {
      filepaths.push(filepath);
    }
  });

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
      validationWarnings.push(`Failed to process file for slug generation: ${filePath} - ${error.message}`);
    }
  }

  return filepathSlugs;
}

/**
 * Process internal link (adapted from validate_update_internal_links_userpass.js)
 */
function processInternalLink(link, currFilePath, filepathSlugs) {
  if (link.startsWith("mailto:")) {
    return { valid: true };
  }

  let filePath = "src/pages";
  let strippedPath = link.split("#")[0];
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
    slug = slugify(correctUrlSplit[1]);
    correctUrl = correctUrlSplit[0] + "#" + slug;
  }

  if (!Object.hasOwn(filepathSlugs, internalLinkFile)) {
    return {
      valid: false,
      error: `Target file not found: ${internalLinkFile} for link: ${link}`
    };
  }

  if (slug !== "" && !filepathSlugs[internalLinkFile].some((slugO) => slug === slugO)) {
    return {
      valid: false,
      error: `Slug "${slug}" not found in file: ${internalLinkFile} for link: ${link}`
    };
  }

  try {
    fs.accessSync(internalLinkFile, constants.F_OK);
    return { valid: true };
  } catch (err) {
    return {
      valid: false,
      error: `Cannot access file: ${internalLinkFile} for link: ${link}`
    };
  }
}

/**
 * Extract and validate internal links from JSON descriptions
 */
function validateInternalLinksInDescriptions(tableFiles, filepathSlugs) {
  console.log('\n🔍 Validating internal links in table descriptions...');
  
  let linksValid = true;
  
  Object.entries(tableFiles).forEach(([fileKey, fileData]) => {
    Object.entries(fileData.content).forEach(([tableName, tableData]) => {
      if (tableData.data && Array.isArray(tableData.data)) {
        tableData.data.forEach((row, rowIndex) => {
          if (row.description) {
            // Find markdown links in descriptions
            const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
            let match;
            
            while ((match = linkRegex.exec(row.description)) !== null) {
              const linkText = match[1];
              const linkUrl = match[2];
              
              // Only validate internal links (not external URLs)
              const isExternalURL = /^https?:\/\//;
              if (!isExternalURL.test(linkUrl)) {
                // Use a dummy file path for validation context
                const dummyFilePath = "src/pages/komodo-defi-framework/api/common_structures/index.mdx";
                const linkValidation = processInternalLink(linkUrl, dummyFilePath, filepathSlugs);
                
                if (!linkValidation.valid) {
                  validationErrors.push(
                    `Invalid internal link in ${fileData.path} → ${tableName} → row ${rowIndex + 1} → parameter "${row.parameter}": ${linkValidation.error}`
                  );
                  linksValid = false;
                } else {
                  console.log(`  ✅ ${fileKey}.${tableName}.${row.parameter}: [${linkText}](${linkUrl})`);
                }
              }
            }
          }
        });
      }
    });
  });
  
  return linksValid;
}

/**
 * Main validation function
 */
async function main() {
  console.log('🔍 Starting CompactTable data validation...\n');
  
  try {
    // Step 1: Load all table files
    const tableFiles = loadTableFiles();
    if (Object.keys(tableFiles).length === 0) {
      console.error('❌ No table files found!');
      process.exit(1);
    }
    
    // Step 2: Validate JSON structure
    const structureValid = validateJsonStructure(tableFiles);
    
    // Step 3: Find CompactTable references in MDX files
    const references = findCompactTableReferences();
    
    // Step 4: Validate that all references exist
    const referencesValid = validateCompactTableReferences(references, tableFiles);
    
    // Step 5: Create file slugs for internal link validation
    const filepathSlugs = await createFileSlugs();
    
    // Step 6: Validate internal links in descriptions
    const linksValid = await validateInternalLinksInDescriptions(tableFiles, filepathSlugs);
    
    // Report results
    console.log('\n📊 Validation Summary:');
    console.log(`   - Table files loaded: ${Object.keys(tableFiles).length}`);
    console.log(`   - CompactTable references found: ${references.length}`);
    console.log(`   - Page files with slugs: ${Object.keys(filepathSlugs).length}`);
    
    if (validationWarnings.length > 0) {
      console.log('\n⚠️  Warnings:');
      validationWarnings.forEach(warning => console.log(`   ${warning}`));
    }
    
    if (validationErrors.length > 0) {
      console.log('\n❌ Validation Errors:');
      validationErrors.forEach(error => console.log(`   ${error}`));
      process.exit(1);
    }
    
    if (structureValid && referencesValid && linksValid) {
      console.log('\n🎉 All CompactTable data validation passed!');
    } else {
      console.log('\n💥 Validation failed!');
      process.exit(1);
    }
    
  } catch (error) {
    console.error(`❌ Validation failed with error: ${error.message}`);
    if (error.stack) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

// Run validation if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { main as validateCompactTableData };