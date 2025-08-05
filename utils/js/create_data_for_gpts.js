import * as fs from "fs";
//import { EXIT, visitParents } from 'unist-util-visit-parents'
import { visit, EXIT } from 'unist-util-visit'
import path from 'path'
import { remark } from 'remark'
import remarkGfm from "remark-gfm";
import remarkMdx from "remark-mdx";
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const gptDir = path.resolve(__dirname, '../../data-for-gpts');
const pagesDir = path.resolve(__dirname, '../../src/pages');
async function walkDir(dir, callback, ...callbackArgs) {
    let files = fs.readdirSync(dir);

    for (const file of files) {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);

        if (stat.isDirectory()) {
            await walkDir(filePath, callback, ...callbackArgs);
        } else if (stat.isFile() && !filePath.toLowerCase().includes(".ds_store")) {
            await callback(filePath, ...callbackArgs);
        }
    }
}

async function readFileProcessItAndAddContentToFile(filePath, contentHolder) {
    const fileContent = fs.readFileSync(filePath, 'utf8')
    const processedFileContent = await convertMdxToMd(fileContent, filePath)
    contentHolder.content += processedFileContent;
}

const pathsNames = [["", "all"], ["komodo-defi-framework", "komodo-defi-framework"], ["historical", "historical"], ["smart-chains", "smart-chains"], ["antara", "antara"], ["start-here", "start-here"], ["komodo-defi-framework/api", "komodefi-api/all-api"], ["komodo-defi-framework/api/legacy", "komodefi-api/legacy-api"], ["komodo-defi-framework/api/v20", "komodefi-api/v20-api"], ["komodo-defi-framework/api/v20-dev", "komodefi-api/v20-dev-api"]]

for (let index = 0; index < pathsNames.length; index++) {
    const element = pathsNames[index];
    let contentHolder = { content: "" };
    await walkDir(path.join(pagesDir, element[0]), readFileProcessItAndAddContentToFile, contentHolder)
    fs.writeFileSync(path.join(gptDir, `${element[1]}-content.txt`), contentHolder.content)
}

async function convertMdxToMd(fileContent, filePath) {
    try {
        const mdContent = await remark()
            .use(remarkGfm)
            .use(remarkMdx)
            .use(() => (tree) => {

                visit(tree, 'mdxJsxFlowElement', (node, index, parent) => {

                    if (node.name === 'BulletPoints') {
                        const titleProp = node.attributes.find(attr => attr.name === 'title');
                        const descProp = node.attributes.find(attr => attr.name === 'desc');

                        const newContent = [];

                        if (titleProp && titleProp.value) {
                            newContent.push({
                                type: 'heading',
                                depth: 3,
                                children: [{ type: 'text', value: titleProp.value }]
                            });
                        }


                        if (descProp && descProp.value && descProp.value.type === 'mdxJsxAttributeValueExpression') {
                            try {
                                const markdown = convertHtmlToMd(descProp.value.value);
                                newContent.push({
                                    type: 'paragraph',
                                    children: [{ type: 'text', value: markdown }]
                                });
                            } catch (error) {
                                console.error(error)
                                throw new Error(`Error parsing descProp in file: ${filePath}`, error);
                            }
                        }

                        if (newContent.length > 0) {
                            parent.children.splice(index, 1, ...newContent);
                            return [visit.SKIP, index];
                        } else {
                            parent.children.splice(index, 1);
                            return [visit.SKIP, index];
                        }
                    }

                    if (node.children && node.children.length > 0) {
                        parent.children.splice(index, 1, ...node.children);
                        return [visit.SKIP, index];
                    } else {
                        parent.children.splice(index, 1);
                        return [visit.SKIP, index];
                    }
                });

                visit(tree, 'mdxJsxTextElement', (node, index, parent) => {
                    if (node.children && node.children.length > 0) {
                        parent.children.splice(index, 1, ...node.children);
                        return [visit.SKIP, index];
                    } else {
                        parent.children.splice(index, 1);
                        return [visit.SKIP, index];
                    }
                });



            })
            .process(fileContent);

        return String(mdContent)
    } catch (error) {
        if (error) {
            throw new Error(`Error in file: ${filePath} \n ${error}`);
        };
    }
}

function convertHtmlToMd(html) {
    // Remove leading/trailing whitespace and newlines
    html = html.trim();

    // Replace <ul> and </ul> tags
    html = html.replace(/<\/?ul>/g, '');

    // Replace <li> tags with Markdown list items
    html = html.replace(/<li>/g, '- ');

    // Remove </li> tags
    html = html.replace(/<\/li>/g, '');

    // Trim each line and remove empty lines
    const lines = html.split('\n').map(line => line.trim()).filter(line => line !== '');

    // Join the lines with newline characters
    return lines.join('\n');
}