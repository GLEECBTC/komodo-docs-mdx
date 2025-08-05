//import { visit, EXIT } from 'unist-util-visit'
import { EXIT, visitParents } from 'unist-util-visit-parents'

import { promises as fs } from 'fs';
import path from 'path'
import { remark } from 'remark'
import remarkGfm from "remark-gfm";
import remarkMdx from "remark-mdx";
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pagesDir = path.resolve(__dirname, '../../src/pages');

(async function () {

    await walkDir(pagesDir, async (filePath) => {
        try {
            const markdown = await fs.readFile(filePath, 'utf-8');
            //console.log(filePath)
            const file = await remark()
                .use(remarkGfm)
                .use(remarkMdx)
                .use(() => (tree) => {
                    let documentContainsTitleHeading = false;
                    let numH1s = 0
                    visitParents(tree, 'heading', (node, ancestors) => {
                        let nodeHasLinks = node.children.some(child => child.type === "link")
                        if (nodeHasLinks) {
                            throw new Error(`${JSON.stringify(node, null, 2)} 
in file:${filePath} has a link. Please remove it.`)
                        }
                        if (node.depth === 1 && !ancestors.some((ancestor) => ancestor.name === "DevComment")) {
                            documentContainsTitleHeading = true;
                            numH1s = numH1s + 1
                            if (numH1s > 1) {
                                throw new Error(`Document must contain only one <h1>: ${filePath}
node: ${JSON.stringify(node, null, 2)}`);
                            }
                            //EXIT; 
                        }
                    });
                    if (!documentContainsTitleHeading) {
                        throw new Error("Document must contain a <h1>: " + filePath);
                    }
                })
                .process(markdown);

        } catch (error) {
            if (error) {
                throw new Error(`Error in file: ${filePath} \n ${error}`);
            };
        }
    });

})()

async function walkDir(dir, callback) {
    let files = await fs.readdir(dir);
    await Promise.all(files.map(async (file) => {
        const filePath = path.join(dir, file);
        const stats = await fs.stat(filePath);
        if (stats.isDirectory()) {
            await walkDir(filePath, callback);
        } else if (stats.isFile() && !filePath.toLowerCase().includes(".ds_store")) {
            await callback(filePath);
        }
    }));
}