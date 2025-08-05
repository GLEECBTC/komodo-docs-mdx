import fs from 'fs';
import https from 'https';
import path from 'path';
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '../../');
const pagesDir = path.resolve(__dirname, '../../src/pages');
const dataDir = path.resolve(__dirname, './data');
const imgDir = path.resolve(__dirname, '../../src/images');
const authorsData = JSON.parse(fs.readFileSync(path.join(projectRoot, 'authors.json'), 'utf8'));
const oldFileData = JSON.parse(fs.readFileSync(path.join(dataDir, '_fileData_old_documentation_mod.json'), 'utf8'));
import dotenv from 'dotenv';
dotenv.config();

const fileData = {};

(async function () {
    const allContributorsDataUrl = "https://api.github.com/repos/komodoplatform/komodo-docs-mdx/contributors"

    const latest100CommitsUrl = "https://api.github.com/repos/komodoplatform/komodo-docs-mdx/commits?sha=dev&per_page=100"

    const userDataUrl = (login) => `https://api.github.com/users/${login}`

    // Robust GitHub token selection
    const GITHUB_TOKEN =
        process.env.LOCAL_GH_TOKEN ||
        process.env.GH_TOKEN ||
        process.env.GITHUB_TOKEN;

    if (!GITHUB_TOKEN) {
        throw new Error('No GitHub token found in environment variables. Please set LOCAL_GH_TOKEN, GH_TOKEN, or GITHUB_TOKEN.');
    }

    const options = {
        headers: {
            'User-Agent': 'komodo-docs-mdx-ci',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Authorization': `Bearer ${GITHUB_TOKEN}`
        }
    };
    console.log(GITHUB_TOKEN)

    try {
        const { response: contributorsRes } = await httpsGet(allContributorsDataUrl, options)
        console.log(contributorsRes)
        const contributorData = JSON.parse(contributorsRes)
        const { response: commitsRes } = await httpsGet(latest100CommitsUrl, options)
        const commitData = JSON.parse(commitsRes)

        const contributorLogins = new Set();
        contributorData.forEach(contributor => contributorLogins.add(contributor.login))
        commitData.forEach(commit => commit.author && contributorLogins.add(commit.author.login))
        Object.values(authorsData).forEach(author => contributorLogins.add(author.username))
        for (const contributorLogin of Array.from(contributorLogins)) {
            const isMissingInContributorData = !Object.values(authorsData).find(author => author.username === contributorLogin) || !contributorData.find(contributor => contributor.login === contributorLogin)
            console.log(contributorLogin)

            const { response } = await httpsGet(`https://api.github.com/repos/komodoplatform/komodo-docs-mdx/commits?sha=dev&author=${contributorLogin}`, options)
            const contributorCommits = JSON.parse(response)
            const commit_emails = new Set();
            contributorCommits.forEach(commit => {
                if (commit.commit && commit.commit.author && commit.commit.author.email) {
                    commit_emails.add(commit.commit.author.email);
                }
            });

            authorsData[contributorLogin]?.commit_emails.forEach(email => commit_emails.add(email))


            authorsData[contributorLogin] = authorsData[contributorLogin] ?? {}

            //console.log(commit_emails)
            console.log(contributorLogin)

            authorsData[contributorLogin].username = contributorLogin
            authorsData[contributorLogin].commit_emails = Array.from(commit_emails).sort()
            const authorSocials = authorsData[contributorLogin].socials

            const { response: userDataRes } = await httpsGet(userDataUrl(contributorLogin), options)
            const userData = JSON.parse(userDataRes);

            if (userData.message === "Not Found" || userData.status === "404") {
                console.warn(`User data not found for: ${contributorLogin}`);
                continue; // Skip to next contributor
            }

            authorsData[contributorLogin].socials = {
                ...authorSocials,
                twitter: userData.twitter_username ?? authorSocials?.twitter ?? "",
                linkedin: authorSocials?.linkedin ?? ""
            }

            authorsData[contributorLogin].id = userData.id
            const imageUrl = userData.avatar_url
            authorsData[contributorLogin].avatar_url = imageUrl
            const imgName = await downloadImage(imageUrl, contributorLogin)
            authorsData[contributorLogin].image = imgName
        }
    } catch (error) {
        console.error(error)
        throw new Error(error)
    }

    fs.writeFileSync(path.join(projectRoot, 'authors.json'), JSON.stringify(authorsData, null, 4))


    walkDir(pagesDir, getAllFileData);

    // Merge renamed paths data if available
    try {
        if (fs.existsSync(path.join(dataDir, '_renamedPathsData.json'))) {
            const renamedPathsData = JSON.parse(fs.readFileSync(path.join(dataDir, '_renamedPathsData.json'), 'utf8'));

            // Process each renamed path
            for (const [newRoute, data] of Object.entries(renamedPathsData)) {
                if (fileData[newRoute]) {
                    // Merge contributors
                    const existingContributors = fileData[newRoute].contributors || [];
                    const oldContributors = data.contributors || [];

                    // Combine and remove duplicates
                    const allContributors = [...existingContributors, ...oldContributors];
                    fileData[newRoute].contributors = allContributors.filter((contributor, index) =>
                        index === allContributors.findIndex(c =>
                            c.name === contributor.name && c.email === contributor.email
                        )
                    );

                    // Update creation date if any date in the chain is earlier
                    if (data.dateCreated && (!fileData[newRoute].dateCreated || new Date(data.dateCreated) < new Date(fileData[newRoute].dateCreated))) {
                        fileData[newRoute].dateCreated = data.dateCreated;
                    }

                    // Store the rename history if not already present
                    fileData[newRoute].previousPaths = [
                        ...(fileData[newRoute].previousPaths || []),
                        ...(data.previousRoutes || [])
                    ].filter((value, index, self) => self.indexOf(value) === index); // Remove duplicates
                }
            }
        }
    } catch (error) {
        console.error("Error merging renamed paths data:", error);
    }

    fs.writeFileSync(path.join(dataDir, '_fileData.json'), JSON.stringify(fileData, null, 2));
})();

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

async function httpsGet(url, options) {
    return new Promise((resolve, reject) => {
        https.get(url, options, (resp) => {
            let data = '';

            // A chunk of data has been received.
            resp.on('data', (chunk) => {
                data += chunk;
            });

            // The whole response has been received. Resolve the promise.
            resp.on('end', () => {
                resolve({ response: data, headers: resp.headers });
            });

        }).on("error", (err) => {
            reject(err);
        });
    });
}

async function downloadImage(url, username) {
    const options = {
        headers: {
            'User-Agent': 'komodo-docs-mdx-ci'
        }
    };
    return new Promise((resolve, reject) => {
        let filename;
        https.get(url, options, (response) => {
            const fileExt = response.headers["content-type"].split("/")[1]
            filename = path.join(imgDir, 'authors', `${username}.${fileExt}`)
            const file = fs.createWriteStream(filename);

            response.pipe(file);
            file.on('finish', () => {
                file.close();
                console.log('Image downloaded successfully: ' + filename);
                resolve(path.basename(filename))
            });
        }).on('error', (error) => {
            fs.unlink(filename);
            reject(`Error downloading image for user, ${username}:`, error);
        });

    });

}

const getAllFileData = (filepath) => {
    //const gitDir = './komodo-docs-mdx'// path.join(__dirname, './komodo-docs-mdx')
    const getLastEditedTime = spawnSync("git", [
        "log",
        "-1",
        "--format=%ct",
        filepath,
    ]); //, { cwd: gitDir }

    const getCommitTimesInReverse = spawnSync("git", [
        "log",
        "--reverse",
        "--format=%ct",
        filepath,
    ]);

    if (getCommitTimesInReverse.error) {
        console.error(
            "An error occurred while executing the git command:",
            getCommitTimesInReverse.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${getCommitTimesInReverse.error.message}`
        );
    }

    if (getLastEditedTime.error) {
        console.error(
            "An error occurred while executing the git command:",
            getLastEditedTime.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${getLastEditedTime.error.message}`
        );
    }

    const firstCommitTime = getCommitTimesInReverse.stdout.toString().split("\n")[0]
    const firstCommitDate = new Date(parseInt(firstCommitTime) * 1000);

    if (
        firstCommitDate.toString() == "Invalid Date"
    ) {
        console.error(
            filepath + "firstCommitDate is invalid:",
            firstCommitDate
        );
        throw new Error(
            "firstCommitDate is invalid:",
            firstCommitDate
        );
    }

    const lastEditedDate = new Date(parseInt(getLastEditedTime.stdout.toString()) * 1000);

    if (
        lastEditedDate.toString() == "Invalid Date"
    ) {
        console.error(
            filepath + "lastEditedDate is invalid:",
            lastEditedDate
        );
        throw new Error(
            "lastEditedDate is invalid:",
            lastEditedDate
        );
    }

    let lastContributor = getLastContributor(filepath)
    let allContributors = getAllContributors(filepath)
    const fileRoute = filePathToRoute(filepath)
    fileData[fileRoute] = fileData[fileRoute] ? fileData[fileRoute] : {};
    fileData[fileRoute]["dateModified"] = lastEditedDate.toISOString();
    fileData[fileRoute]["contributors"] = allContributors;
    fileData[fileRoute]["dateCreated"] = firstCommitDate.toISOString();
    fileData[fileRoute]["lastContributor"] =
        lastContributor;

};

function filePathToRoute(filePath) {
    const route = filePath
        .replace(/(\/index)?\.[^.]+$/, "") // Remove the file extension and "index" suffix if present
        .replace(/^.*\/pages\/?/, ""); // Remove the "pages" directory prefix and add a leading slash
    return "/" + route;
}

function getLastContributor(filepath) {
    let nameCommand = spawnSync("git", [
        "log",
        "-n 1",
        '--format=%an',
        filepath,
    ]);
    if (nameCommand.error) {
        console.error(
            "An error occurred while executing the git command:",
            nameCommand.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${nameCommand.error.message}`
        );
    }
    let emailCommand = spawnSync("git", [
        "log",
        "-n 1",
        '--format=%ae',
        filepath,
    ]);
    if (emailCommand.error) {
        console.error(
            "An error occurred while executing the git command:",
            emailCommand.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${emailCommand.error.message}`
        );
    }
    let name = JSON.stringify(
        nameCommand.stdout.toString().replace("\n", "")
    );
    let email =
        emailCommand.stdout.toString().replace("\n", "")
    return { name, email }
}

function getAllContributors(filepath) {
    let nameCommand = spawnSync("git", [
        "log",
        '--format=%an',
        filepath,
    ]);
    if (nameCommand.error) {
        console.error(
            "An error occurred while executing the git command:",
            nameCommand.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${nameCommand.error.message}`
        );
    }
    let emailCommand = spawnSync("git", [
        "log",
        '--format=%ae',
        filepath,
    ]);
    if (emailCommand.error) {
        console.error(
            "An error occurred while executing the git command:",
            emailCommand.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${emailCommand.error.message}`
        );
    }
    let names =
        nameCommand.stdout.toString().split("\n").filter((el) => {
            return el !== "";
        }).map(name => JSON.stringify(name))

    let emails =
        emailCommand.stdout.toString().split("\n").filter((el) => {
            return el !== "";
        })
    if (names.length !== emails.length) {
        throw new Error("length of emails list and names list for allContributors isn't the same")
    }
    let contributorsArray = []
    for (let index = 0; index < names.length; index++) {
        let contributor = {
            name: names[index],
            email: emails[index]
        }
        contributorsArray.push(contributor)
    }
    let oldFileData_pathData = oldFileData[filepath.replace("/index.mdx", "").replace("src/pages", "")]
    let oldContributors = oldFileData_pathData ? oldFileData_pathData.contributors : []
    contributorsArray = [...contributorsArray, ...oldContributors]
    return contributorsArray.filter((item, index) => { //filter repeated entries
        return index === contributorsArray.findIndex(obj => {
            return JSON.stringify(obj) === JSON.stringify(item);
        });
    });
}