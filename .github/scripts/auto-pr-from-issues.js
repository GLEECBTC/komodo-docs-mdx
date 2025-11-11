#!/usr/bin/env node

/**
 * Auto PR from Issues Script
 * Scans issues labeled with "auto PR" and creates pull requests with required documentation updates
 * 
 * IMPORTANT: This script follows the AI Agent Reference Guide for KDF documentation.
 * 
 * Key principles:
 * 1. NEVER edit auto-generated files (src/pages/komodo-defi-framework/api/index.mdx, filepathSlugs.json)
 * 2. Include required {{label}} attributes for method parsing
 * 3. Use proper directory structure and naming conventions
 * 4. Let build scripts handle slug generation and API index updates
 * 5. Manual updates: sidebar.json, changelog, and documentation files only
 */

const { Octokit } = require("@octokit/core");
const { retry } = require("@octokit/plugin-retry");
const { throttling } = require("@octokit/plugin-throttling");
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Enhanced Octokit with retry and throttling
const MyOctokit = Octokit.plugin(retry, throttling);

class AutoPRManager {
  constructor() {
    this.config = this.validateConfig();
    this.octokit = this.initializeOctokit();
    this.stats = {
      processed: 0,
      created: 0,
      skipped: 0,
      errors: 0
    };
    this.repoRoot = process.cwd().replace('/.github', '');
  }
  
  validateConfig() {
    const { 
      TARGET_OWNER, TARGET_REPO, AUTO_PR_LABEL, 
      DRY_RUN, SPECIFIC_ISSUES 
    } = process.env;
    
    const requiredVars = [TARGET_OWNER, TARGET_REPO, AUTO_PR_LABEL];
    const missing = requiredVars.filter(v => !v);
    
    if (missing.length > 0) {
      throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
    }
    
    return {
      targetOwner: TARGET_OWNER,
      targetRepo: TARGET_REPO,
      autoPrLabel: AUTO_PR_LABEL,
      dryRun: DRY_RUN === 'true',
      specificIssues: SPECIFIC_ISSUES ? SPECIFIC_ISSUES.split(',').map(n => parseInt(n.trim())).filter(n => !isNaN(n)) : null
    };
  }
  
  initializeOctokit() {
    const auth = process.env.GITHUB_TOKEN;
    if (!auth) {
      throw new Error("No authentication token available");
    }
    
    return new MyOctokit({
      auth,
      throttle: {
        onRateLimit: (retryAfter, options, octokit) => {
          console.warn(`Request quota exhausted for request ${options.method} ${options.url}`);
          if (options.request.retryCount === 0) {
            console.info(`Retrying after ${retryAfter} seconds!`);
            return true;
          }
        },
        onSecondaryRateLimit: (retryAfter, options, octokit) => {
          console.warn(`Secondary rate limit hit for request ${options.method} ${options.url}`);
        },
      },
      retry: {
        doNotRetry: ["abuse"],
      },
    });
  }
  
  async listCandidateIssues() {
    try {
      // If specific issues are requested, fetch them directly
      if (this.config.specificIssues) {
        const issues = [];
        for (const issueNumber of this.config.specificIssues) {
          try {
            const issue = await this.octokit.request("GET /repos/{owner}/{repo}/issues/{issue_number}", {
              owner: this.config.targetOwner,
              repo: this.config.targetRepo,
              issue_number: issueNumber
            });
            
            // Check if issue has the required label
            const hasLabel = issue.data.labels?.some(l => 
              (l.name || "").toLowerCase() === this.config.autoPrLabel.toLowerCase()
            );
            
            if (hasLabel && issue.data.state === "open") {
              issues.push(issue.data);
            } else {
              console.info(`Issue #${issueNumber} does not have required label or is not open`);
            }
          } catch (error) {
            console.warn(`Error fetching issue #${issueNumber}: ${error.message}`);
          }
        }
        return issues;
      }
      
      // Otherwise, search for issues with the label
      const q = [
        `repo:${this.config.targetOwner}/${this.config.targetRepo}`,
        "is:issue",
        "is:open",
        `label:"${this.config.autoPrLabel}"`
      ].join(" ");
      
      let page = 1;
      const all = [];
      const maxPages = 10;
      
      while (page <= maxPages) {
        const res = await this.octokit.request("GET /search/issues", {
          q,
          sort: "updated",
          order: "desc",
          per_page: 50,
          page,
          headers: {
            'X-GitHub-Api-Version': '2022-11-28'
          }
        });
        
        all.push(...res.data.items);
        
        if (!res.data.items.length || all.length >= res.data.total_count) {
          break;
        }
        page++;
      }
      
      return all;
    } catch (error) {
      console.error(`Error listing candidate issues: ${error.message}`);
      return [];
    }
  }
  
  parseIssueContent(issue) {
    const body = issue.body || "";
    const title = issue.title || "";
    
    // Extract KDF method information from issue content
    const methodPattern = /(?:method|function|rpc)[:\s]*`?([a-zA-Z0-9_:]+)`?/gi;
    const pathPattern = /(?:path|file)[:\s]*`?([a-zA-Z0-9_\/\-\.]+)`?/gi;
    const typePattern = /(?:type|category)[:\s]*`?([a-zA-Z0-9_\-]+)`?/gi;
    
    let methods = [];
    let paths = [];
    let types = [];
    
    let match;
    while ((match = methodPattern.exec(body)) !== null) {
      methods.push(match[1]);
    }
    
    while ((match = pathPattern.exec(body)) !== null) {
      paths.push(match[1]);
    }
    
    while ((match = typePattern.exec(body)) !== null) {
      types.push(match[1]);
    }
    
    // Try to extract from title as well
    const titleMethodMatch = title.match(/([a-zA-Z0-9_:]+)/);
    if (titleMethodMatch && !methods.includes(titleMethodMatch[1])) {
      methods.push(titleMethodMatch[1]);
    }

    // Extract structured method information if available (from enhanced sync script)
    const structuredMethods = this.extractStructuredMethods(body);
    const codeExamples = this.extractCodeExamples(body);
    
    return {
      methods: [...new Set(methods)],
      paths: [...new Set(paths)],
      types: [...new Set(types)],
      description: body,
      title: title,
      structuredMethods: structuredMethods,
      codeExamples: codeExamples
    };
  }

  /**
   * Extract structured method information from issue body (created by sync script)
   */
  extractStructuredMethods(body) {
    const methods = [];
    const methodSections = body.split('#### Method:').slice(1);
    
    methodSections.forEach(section => {
      const lines = section.split('\n');
      const methodMatch = lines[0].match(/`([^`]+)`/);
      if (!methodMatch) return;
      
      const methodName = methodMatch[1];
      const method = { name: methodName, parameters: [] };
      
      let inParams = false;
      let currentExample = '';
      let inExample = false;
      
      lines.forEach(line => {
        if (line.includes('**Request Parameters:**')) {
          inParams = true;
        } else if (line.includes('**Example Request:**')) {
          inParams = false;
          inExample = true;
        } else if (line.startsWith('```json')) {
          currentExample = '';
        } else if (line.startsWith('```') && inExample) {
          try {
            method.example = JSON.parse(currentExample);
          } catch (e) {
            // Invalid JSON, skip
          }
          inExample = false;
        } else if (inExample) {
          currentExample += line + '\n';
        } else if (inParams && line.startsWith('- ')) {
          const paramMatch = line.match(/- `([^`]+)` \(([^)]+)\): Example value `([^`]+)`/);
          if (paramMatch) {
            method.parameters.push({
              name: paramMatch[1],
              type: paramMatch[2],
              example: paramMatch[3]
            });
          }
        }
      });
      
      methods.push(method);
    });
    
    return methods;
  }

  /**
   * Extract JSON code examples from text
   */
  extractCodeExamples(text) {
    const examples = [];
    const codeBlockPattern = /```json\s*\n([\s\S]*?)\n```/gi;
    
    let match;
    while ((match = codeBlockPattern.exec(text)) !== null) {
      try {
        const parsed = JSON.parse(match[1]);
        examples.push(parsed);
      } catch (e) {
        // Skip invalid JSON
      }
    }
    
    return examples;
  }
  
  convertMethodToPath(method) {
    // Convert KDF method format to filesystem path [[memory:353920]]
    // e.g., "task::enable_utxo::init" -> "task-enable_utxo-init"
    return method.replace(/::/g, '-');
  }
  
  determineApiVersion(method) {
    // Determine API version based on method pattern
    if (method.includes('::')) {
      return 'v20-dev'; // New format methods go to v20-dev
    } else if (method.startsWith('lightning') || method.startsWith('task')) {
      return 'v20';
    } else {
      return 'legacy';
    }
  }
  
  async generateMethodDocumentation(issueData, method) {
    const apiVersion = this.determineApiVersion(method);
    const methodPath = this.convertMethodToPath(method);
    
    // Determine category from method name
    let category = 'misc';
    if (method.includes('lightning')) category = 'lightning';
    else if (method.includes('task')) category = 'task_managed';
    else if (method.includes('wallet')) category = 'wallet';
    else if (method.includes('swap')) category = 'swap';
    else if (method.includes('orderbook')) category = 'orderbook';
    
    const fileName = `${methodPath}.mdx`;
    const dirPath = path.join(this.repoRoot, 'src', 'pages', 'komodo-defi-framework', 'api', apiVersion, category);
    const filePath = path.join(dirPath, fileName);
    
    // Generate method documentation using AI if available
    const aiContent = await this.generateAIDocumentation(issueData, method, category);
    
    const content = aiContent || this.generateTemplateDocumentation(method, issueData, category);
    
    return {
      path: filePath,
      content: content,
      category: category,
      apiVersion: apiVersion,
      methodName: method
    };
  }
  
  async generateAIDocumentation(issueData, method, category = 'misc') {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      console.info("No OpenAI API key provided, using template documentation");
      return null;
    }

    try {
      const prompt = `Generate comprehensive MDX documentation for the KDF method "${method}" based on this issue description:

Title: ${issueData.title}
Description: ${issueData.description}

CRITICAL REQUIREMENTS (AI Agent Reference Guide):
1. MUST include {{label : '${method}', tag : 'API-v2'}} in the main heading
2. MUST include label="${method}" in the CodeGroup component
3. MUST use CompactTable components for request/response parameter tables
4. MUST include the CompactTable import statement
5. Follow this exact structure:

export const title = "...";
export const description = "...";
import CompactTable from '@/components/mdx/CompactTable';

# ${method}

## ${method} {{label : '${method}', tag : 'API-v2'}}

Description...

### Request Parameters

<CompactTable source="v2/${category}.${method}Request" />

### Response Parameters

<CompactTable source="v2/${category}.${method}Response" />

#### 📌 Examples
<CodeGroup title="..." tag="POST" label="${method}" mm2MethodDecorate="true">

6. The {{label}} attributes are CRITICAL for auto-generation scripts
7. Use realistic KDF method parameters and response structures  
8. Be comprehensive but production-ready
9. CompactTable components reference JSON schema files in src/data/tables/

This documentation will be parsed by scripts to auto-generate API indexes and navigation.`;

      const fetch = (await import('node-fetch')).default;
      const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiKey}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [
            {
              role: "system",
              content: "You are a technical documentation expert specializing in API documentation. Generate complete, accurate MDX documentation following the provided patterns."
            },
            {
              role: "user",
              content: prompt
            }
          ],
          max_tokens: 2000,
          temperature: 0.3
        })
      });

      if (!response.ok) {
        console.warn(`OpenAI API failed: ${response.status} ${response.statusText}`);
        return null;
      }

      const data = await response.json();
      console.info("✅ Using OpenAI API for documentation generation");
      return data.choices?.[0]?.message?.content?.trim() || null;

    } catch (error) {
      console.warn(`OpenAI API error: ${error.message}`);
      return null;
    }
  }
  
  generateTemplateDocumentation(method, issueData, category = 'misc') {
    const methodTitle = method.replace(/::/g, ' ').replace(/_/g, ' ').toLowerCase()
      .replace(/\b\w/g, l => l.toUpperCase());
    
    // Find structured method info for this method
    const structuredMethod = issueData.structuredMethods?.find(m => m.name === method);
    const exampleFromIssue = structuredMethod?.example || 
                            issueData.codeExamples?.find(ex => ex.method === method);
    
    // Generate parameter documentation from extracted data
    let parameterDocs = '';
    if (structuredMethod?.parameters?.length > 0) {
      parameterDocs = '\n**Extracted Parameters:**\n\n';
      structuredMethod.parameters.forEach(param => {
        parameterDocs += `- **${param.name}** (${param.type}): Example: \`${param.example}\`\n`;
      });
      parameterDocs += '\n';
    }
    
    // Use real example if available, otherwise generate template
    const exampleRequest = exampleFromIssue || {
      "userpass": "RPC_UserP@SSW0RD",
      "mmrpc": "2.0",
      "method": method,
      "params": {},
      "id": 42
    };
    
    // Note: This template follows the AI Agent Reference Guide requirements
    // The {{label}} attribute is CRITICAL for script parsing and auto-generation
    return `export const title = "Komodo DeFi Framework Method: ${methodTitle}";
export const description = "Documentation for the ${method} method of the Komodo DeFi Framework.";
import CompactTable from '@/components/mdx/CompactTable';

# ${method}

## ${method} {{label : '${method}', tag : 'API-v2'}}

The \`${method}\` method ${this.extractMethodDescription(issueData, method)} 
${parameterDocs}
### Request Parameters

<CompactTable source="v2/${category}.${method}Request" />

### Response Parameters

<CompactTable source="v2/${category}.${method}Response" />

#### 📌 Examples

<CodeGroup title="${methodTitle}" tag="POST" label="${method}" mm2MethodDecorate="true">
  \`\`\`json
  ${JSON.stringify(exampleRequest, null, 2)}
  \`\`\`
</CodeGroup>

<Note>
  This documentation was auto-generated from issue #${issueData.number || 'N/A'}${structuredMethod ? ' with extracted parameter information from the source PR' : ''}. Please review and update as needed.
</Note>`;
  }

  /**
   * Extract method description from issue data
   */
  extractMethodDescription(issueData, method) {
    const description = issueData.description || '';
    
    // Try to find method-specific description
    const methodSection = description.split(`#### Method: \`${method}\``)[1];
    if (methodSection) {
      const lines = methodSection.split('\n').slice(1, 5); // Take first few lines
      return lines.join(' ').replace(/\*\*.*?\*\*/g, '').trim().slice(0, 200) + '...';
    }
    
    // Fall back to summary or generic description
    const summaryMatch = description.match(/### Summary\s*\n([^\n#]+)/);
    if (summaryMatch) {
      return summaryMatch[1].trim().slice(0, 200) + '...';
    }
    
    return 'provides functionality for the Komodo DeFi Framework.';
  }
  
  async createBranchAndCommit(issue, generatedDocs) {
    const branchName = `auto-pr/issue-${issue.number}`;
    const commitMessage = `docs: Add documentation for issue #${issue.number}`;
    
    try {
      // Create and checkout new branch
      execSync(`git checkout -b ${branchName}`, { 
        cwd: this.repoRoot, 
        stdio: 'inherit' 
      });
      
      // Create directories and files
      for (const doc of generatedDocs) {
        const dir = path.dirname(doc.path);
        if (!fs.existsSync(dir)) {
          fs.mkdirSync(dir, { recursive: true });
        }
        
        fs.writeFileSync(doc.path, doc.content);
        console.info(`📝 Created documentation: ${doc.path}`);
      }
      
      // Run build scripts to auto-generate API index and slugs
      console.info("🔧 Running build scripts to generate API index and file path slugs...");
      try {
        execSync(`source utils/py/.venv/bin/activate && ./utils/gen_api_methods_table.py`, { 
          cwd: this.repoRoot, 
          stdio: 'inherit',
          shell: '/bin/bash'
        });
        console.info("✅ Auto-generation completed successfully");
      } catch (buildError) {
        console.error(`❌ Build script failed: ${buildError.message}`);
        throw buildError;
      }
      
      // Stage only specific files (exclude auto-generated files that shouldn't be committed manually)
      const filesToCommit = [
        ...generatedDocs.map(doc => doc.path.replace(this.repoRoot + '/', '')),
        'src/data/sidebar.json', // Only if it was updated
        'src/pages/komodo-defi-framework/changelog/index.mdx' // Only if it was updated
      ];
      
      for (const file of filesToCommit) {
        try {
          execSync(`git add "${file}"`, { cwd: this.repoRoot, stdio: 'inherit' });
        } catch (addError) {
          console.warn(`Could not add ${file} (may not exist or not modified)`);
        }
      }
      
      execSync(`git commit -m "${commitMessage}"`, { 
        cwd: this.repoRoot, 
        stdio: 'inherit' 
      });
      
      if (!this.config.dryRun) {
        // Push branch
        execSync(`git push origin ${branchName}`, { 
          cwd: this.repoRoot, 
          stdio: 'inherit' 
        });
      }
      
      return branchName;
    } catch (error) {
      console.error(`Git operations failed: ${error.message}`);
      throw error;
    }
  }
  
  async createPullRequest(issue, branchName, generatedDocs) {
    if (this.config.dryRun) {
      console.info(`📝 [DRY RUN] Would create PR for issue #${issue.number}`);
      console.info(`🔗 [DRY RUN] Branch: ${branchName}`);
      console.info(`📄 [DRY RUN] Files: ${generatedDocs.map(d => d.path).join(', ')}`);
      return { data: { number: 'DRY-RUN', html_url: 'https://github.com/test/dry-run' } };
    }
    
    const title = `docs: Add documentation for issue #${issue.number} - ${issue.title}`;
    const methodList = generatedDocs.map(doc => `- \`${doc.methodName}\``).join('\n');
    
    const body = `## 🤖 Auto-generated PR

This PR was automatically created from issue #${issue.number}.

### 📝 Changes

Added documentation for the following methods:
${methodList}

### 📂 Files Created/Modified

${generatedDocs.map(doc => `- \`${doc.path}\``).join('\n')}

### 🔗 Related Issue

Closes #${issue.number}

---

> This PR was generated automatically. Please review the content and make any necessary adjustments before merging.`;
    
    try {
      const pr = await this.octokit.request("POST /repos/{owner}/{repo}/pulls", {
        owner: this.config.targetOwner,
        repo: this.config.targetRepo,
        title,
        head: branchName,
        base: "dev", // Using dev branch as base per repository conventions
        body,
        draft: false
      });
      
      // Add labels to the PR
      await this.octokit.request("POST /repos/{owner}/{repo}/issues/{issue_number}/labels", {
        owner: this.config.targetOwner,
        repo: this.config.targetRepo,
        issue_number: pr.data.number,
        labels: ["docs", "auto-generated", "status: pending review"]
      });
      
      console.info(`🔗 Created PR: ${pr.data.html_url}`);
      return pr;
    } catch (error) {
      console.error(`Failed to create PR: ${error.message}`);
      throw error;
    }
  }
  
  async processIssue(issue) {
    try {
      this.stats.processed++;
      
      console.info(`\n🔍 Processing issue #${issue.number}: ${issue.title}`);
      
      // Verify issue still has the required label and is open
      const hasLabel = issue.labels?.some(l => 
        (l.name || "").toLowerCase() === this.config.autoPrLabel.toLowerCase()
      );
      
      if (!hasLabel || issue.state !== "open") {
        console.info(`Skipping issue #${issue.number}: missing label or not open`);
        this.stats.skipped++;
        return;
      }
      
      // Parse issue content
      const issueData = this.parseIssueContent(issue);
      issueData.number = issue.number;
      
      if (issueData.methods.length === 0) {
        console.warn(`No methods found in issue #${issue.number}`);
        this.stats.skipped++;
        return;
      }
      
      console.info(`📋 Found methods: ${issueData.methods.join(', ')}`);
      
      // Generate documentation for each method
      const generatedDocs = [];
      for (const method of issueData.methods) {
        try {
          const doc = await this.generateMethodDocumentation(issueData, method);
          generatedDocs.push(doc);
        } catch (error) {
          console.warn(`Failed to generate docs for method ${method}: ${error.message}`);
        }
      }
      
      if (generatedDocs.length === 0) {
        console.warn(`No documentation generated for issue #${issue.number}`);
        this.stats.skipped++;
        return;
      }
      
      // Create branch and commit changes
      const branchName = await this.createBranchAndCommit(issue, generatedDocs);
      
      // Create pull request
      const pr = await this.createPullRequest(issue, branchName, generatedDocs);
      
      console.info(`✅ Created PR #${pr.data.number} for issue #${issue.number}`);
      this.stats.created++;
      
      // Comment on the original issue
      if (!this.config.dryRun) {
        await this.octokit.request("POST /repos/{owner}/{repo}/issues/{issue_number}/comments", {
          owner: this.config.targetOwner,
          repo: this.config.targetRepo,
          issue_number: issue.number,
          body: `🤖 **Auto PR Created**: ${pr.data.html_url}\n\nThis pull request contains the requested documentation updates.`
        });
      }
      
    } catch (error) {
      console.error(`Error processing issue #${issue.number}: ${error.message}`);
      this.stats.errors++;
      
      // Try to cleanup any created branch
      try {
        execSync(`git checkout dev && git branch -D auto-pr/issue-${issue.number}`, { 
          cwd: this.repoRoot, 
          stdio: 'ignore' 
        });
      } catch (cleanupError) {
        console.warn(`Warning: Failed to cleanup branch 'auto-pr/issue-${issue.number}': ${cleanupError.message}`);
      }
    }
  }
  
  async run() {
    try {
      console.info(`🚀 Starting auto PR creation - DRY RUN: ${this.config.dryRun}`);
      
      // Ensure we're on the dev branch
      execSync(`git checkout dev`, { cwd: this.repoRoot, stdio: 'inherit' });
      execSync(`git pull origin dev`, { cwd: this.repoRoot, stdio: 'inherit' });
      
      const issues = await this.listCandidateIssues();
      console.info(`📋 Found ${issues.length} candidate issue(s) with label "${this.config.autoPrLabel}"`);
      
      // Process issues with some concurrency control
      const concurrency = 2; // Lower concurrency for PR creation
      for (let i = 0; i < issues.length; i += concurrency) {
        const batch = issues.slice(i, i + concurrency);
        await Promise.all(batch.map(issue => this.processIssue(issue)));
      }
      
      // Output final summary
      console.info(`\n📊 === AUTO PR SUMMARY ===`);
      console.info(`📈 Issues Processed: ${this.stats.processed}`);
      console.info(`✅ PRs Created: ${this.stats.created}`);
      console.info(`⏭️  Issues Skipped: ${this.stats.skipped}`);
      console.info(`❌ Errors: ${this.stats.errors}`);
      
      if (this.stats.errors > 0) {
        console.error(`❌ Auto PR creation completed with ${this.stats.errors} errors`);
        process.exit(1);
      } else {
        console.info(`🎉 Auto PR creation completed successfully!`);
      }
      
    } catch (error) {
      console.error(`💥 Auto PR creation failed: ${error.message}`);
      process.exit(1);
    }
  }
}

// Execute if run directly
if (require.main === module) {
  const manager = new AutoPRManager();
  manager.run().catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

module.exports = AutoPRManager;
