import * as fs from "fs";
import dotenv from "dotenv";
import path from "path";

dotenv.config();

const GH_TOKEN = process.env.GH_TOKEN; // Replace with your token
const REPO = "KomodoPlatform/komodo-docs-mdx";               // Replace with "owner/repository"
const PR_NUMBER = "391";         // Replace with the pull request number
const BASE_URL = `https://api.github.com/repos/${REPO}/pulls/${PR_NUMBER}/files`;
const dataDir = path.resolve(__dirname, './data');

const fetchAllFiles = async () => {
    let page = 1;
    const perPage = 100;
    let allFiles = [];

    while (true) {
        const response = await fetch(`${BASE_URL}?per_page=${perPage}&page=${page}`, {
            headers: {
                "Authorization": `token ${GH_TOKEN}`,
                "Accept": "application/vnd.github.v3+json",
            },
        });

        if (!response.ok) {
            console.error(`Error: ${response.status} - ${response.statusText}`);
            break;
        }

        const files = await response.json();

        // Break if no more files
        if (files.length === 0) break;

        allFiles = allFiles.concat(files);
        page++;
    }

    // Filter renamed files
    const renamedFiles = allFiles
        .filter(file => file.status === "renamed")
        .map(file => ({
            filename: file.filename,
            previous_filename: file.previous_filename,
        }));

    return renamedFiles;
};

function convertPathToRoute(filePath) {
    // Remove src/pages prefix and file extension, handle index files
    return '/' + filePath
        .replace(/^src\/pages\//, '')
        .replace(/(\/index)?\.mdx?$/, '');
}

// Function to merge contributors without duplicates
function mergeContributors(contributors1 = [], contributors2 = []) {
    const allContributors = [...contributors1, ...contributors2];
    return allContributors.filter((contributor, index) =>
        index === allContributors.findIndex(c =>
            c.name === contributor.name && c.email === contributor.email
        )
    );
}

// Function to get the earliest date from an array of dates
function getEarliestDate(dates) {
    return dates
        .filter(Boolean) // Remove null/undefined
        .sort()[0]; // Sort and take first (earliest) date
}

// Function to update redirect maps
function updateRedirectMaps(oldPath, newPath) {
    // Read existing redirect maps
    let redirectMapJson = {};
    let redirectMapText = [];

    try {
        redirectMapJson = JSON.parse(fs.readFileSync(path.join(dataDir, "New-Redirect-map.json"), 'utf8'));
        redirectMapText = fs.readFileSync(path.join(dataDir, "New-Redirect-map.txt"), 'utf8').split('\n').filter(line => line.trim());
    } catch (error) {
        console.warn("Could not read existing redirect maps, creating new ones");
    }

    // Format paths for redirect maps
    const oldHtmlPath = oldPath.replace(/\/$/, '');
    const newDocsPath = newPath.replace(/\/$/, '') + '/';
    const newFullPath = 'https://komodoplatform.com/en/docs' + newDocsPath;

    // Check if redirect already exists
    if (!redirectMapJson[oldHtmlPath] || !redirectMapText.includes(`/en/docs${oldHtmlPath} ${newFullPath};`)) {
        // Add to JSON map
        redirectMapJson[oldHtmlPath] = newDocsPath;

        // Add to text map
        redirectMapText.push(`/en/docs${oldHtmlPath} ${newFullPath};`);
        redirectMapText.push(`/en/docs${oldHtmlPath}/ ${newFullPath};`);

        // Write updated maps
        fs.writeFileSync(path.join(dataDir, "New-Redirect-map.json"), JSON.stringify(redirectMapJson, null, 2));
        fs.writeFileSync(path.join(dataDir, "New-Redirect-map.txt"), redirectMapText.join('\n') + '\n');

        console.log(`Added redirect: ${oldHtmlPath} → ${newDocsPath}`);
    }
}

(async () => {
    try {
        // Get list of renamed files from PR
        const renamedFiles = await fetchAllFiles();
        console.log("Renamed Files:", renamedFiles);

        // Read the current file data
        const fileData = JSON.parse(fs.readFileSync(path.join(dataDir, "_fileData.json"), 'utf8'));
        const oldFileData = JSON.parse(fs.readFileSync(path.join(dataDir, "_fileData_old_documentation_mod.json"), 'utf8'));

        // Read existing renamed paths data if it exists
        let existingRenamedPathsData = {};
        try {
            if (fs.existsSync(path.join(dataDir, "_renamedPathsData.json"))) {
                existingRenamedPathsData = JSON.parse(fs.readFileSync(path.join(dataDir, "_renamedPathsData.json"), 'utf8'));
            }
        } catch (error) {
            console.warn("No existing renamed paths data found, starting fresh.");
        }

        // Create a new object to store the merged data for renamed files
        const renamedPathsData = { ...existingRenamedPathsData };

        // Process each renamed file
        for (const file of renamedFiles) {
            const newRoute = convertPathToRoute(file.filename);
            const oldRoute = convertPathToRoute(file.previous_filename);

            // Get old file data from both current and old file data
            const oldFileInfo = oldFileData[oldRoute] || {};
            const currentFileInfo = fileData[oldRoute] || {};

            // If this is a rename of an already renamed path, we need to chain the history
            const existingRenamedInfo = existingRenamedPathsData[oldRoute] || {};

            // Merge all contributors from the chain
            const mergedContributors = mergeContributors(
                mergeContributors(
                    oldFileInfo.contributors,
                    currentFileInfo.contributors
                ),
                existingRenamedInfo.contributors
            );

            // Get the earliest date from all sources
            const dateCreated = getEarliestDate([
                oldFileInfo.dateCreated,
                currentFileInfo.dateCreated,
                existingRenamedInfo.dateCreated
            ]);

            // Store the mapping and merged data
            renamedPathsData[newRoute] = {
                oldRoute,
                previousRoutes: [
                    oldRoute,
                    ...(existingRenamedInfo.previousRoutes || []),
                    ...(existingRenamedInfo.oldRoute ? [existingRenamedInfo.oldRoute] : [])
                ],
                contributors: mergedContributors,
                dateCreated
            };

            // If the old route was in the renamed paths data, we should remove it
            // as it's now part of the chain in the new route
            if (renamedPathsData[oldRoute]) {
                delete renamedPathsData[oldRoute];
            }

            // Update redirect maps for the current rename and all previous routes
            updateRedirectMaps(oldRoute, newRoute);
            for (const prevRoute of renamedPathsData[newRoute].previousRoutes || []) {
                updateRedirectMaps(prevRoute, newRoute);
            }
        }

        // Save the renamed paths data to a new file
        fs.writeFileSync(path.join(dataDir, "_renamedPathsData.json"), JSON.stringify(renamedPathsData, null, 2));
        console.log("Renamed paths data saved successfully!");

    } catch (error) {
        console.error("Error processing files:", error);
    }
})();


