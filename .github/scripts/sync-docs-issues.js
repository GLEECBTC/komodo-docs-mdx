#!/usr/bin/env node

/**
 * Docs Issue Sync Script
 * Syncs documentation issues from KDF framework PRs
 */

const { Octokit } = require("@octokit/core");
const { retry } = require("@octokit/plugin-retry");
const { throttling } = require("@octokit/plugin-throttling");

// Enhanced Octokit with retry and throttling
const MyOctokit = Octokit.plugin(retry, throttling);

class DocsSyncManager {
  constructor() {
    this.config = this.validateConfig();
    this.octokit = this.initializeOctokit();
    this.stats = {
      processed: 0,
      created: 0,
      skipped: 0,
      errors: 0
    };
  }
  
  validateConfig() {
    const { 
      SOURCE_OWNER, SOURCE_REPO, TARGET_OWNER, TARGET_REPO, 
      PR_TRIGGER_LABEL, DRY_RUN, SPECIFIC_PRS 
    } = process.env;
    
    const requiredVars = [SOURCE_OWNER, SOURCE_REPO, TARGET_OWNER, TARGET_REPO, PR_TRIGGER_LABEL];
    const missing = requiredVars.filter(v => !v);
    
    if (missing.length > 0) {
      throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
    }
    
    return {
      sourceOwner: SOURCE_OWNER,
      sourceRepo: SOURCE_REPO,
      targetOwner: TARGET_OWNER,
      targetRepo: TARGET_REPO,
      triggerLabel: PR_TRIGGER_LABEL,
      dryRun: DRY_RUN === 'true',
      specificPRs: SPECIFIC_PRS ? SPECIFIC_PRS.split(',').map(n => parseInt(n.trim())).filter(n => !isNaN(n)) : null
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
  
  markerFor(prHtmlUrl) {
    return `<!-- source-pr:${prHtmlUrl} -->`;
  }
  
  async findExistingIssue(prHtmlUrl) {
    try {
      // Use the newer search API with explicit headers to avoid deprecation warnings
      const q = `repo:${this.config.targetOwner}/${this.config.targetRepo} in:body "source-pr:${prHtmlUrl}" type:issue`;
      const res = await this.octokit.request("GET /search/issues", { 
        q, 
        per_page: 5,
        headers: {
          'X-GitHub-Api-Version': '2022-11-28'
        }
      });
      const open = res.data.items.find(i => i.state === "open");
      return open || res.data.items[0] || null;
    } catch (error) {
      console.warn(`Error searching for existing issue: ${error.message}`);
      return null;
    }
  }
  
  async listCandidatePRs() {
    try {
      // If specific PRs are requested, fetch them directly
      if (this.config.specificPRs) {
        const prs = [];
        for (const prNumber of this.config.specificPRs) {
          try {
            const pr = await this.octokit.request("GET /repos/{owner}/{repo}/pulls/{pull_number}", {
              owner: this.config.sourceOwner,
              repo: this.config.sourceRepo,
              pull_number: prNumber
            });
            
            // Check if PR has the required label
            const hasLabel = pr.data.labels?.some(l => 
              (l.name || "").toLowerCase() === this.config.triggerLabel.toLowerCase()
            );
            
            if (hasLabel && pr.data.state === "open") {
              prs.push(pr.data);
            } else {
              console.info(`PR #${prNumber} does not have required label or is not open`);
            }
          } catch (error) {
            console.warn(`Error fetching PR #${prNumber}: ${error.message}`);
          }
        }
        return prs;
      }
      
      // Otherwise, search for PRs with the label
      const q = [
        `repo:${this.config.sourceOwner}/${this.config.sourceRepo}`,
        "is:pr",
        "is:open",
        `label:"${this.config.triggerLabel}"`
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
      
      // Convert to proper PR objects
      const prs = [];
      for (const item of all) {
        try {
          const pr = await this.octokit.request("GET /repos/{owner}/{repo}/pulls/{pull_number}", {
            owner: this.config.sourceOwner,
            repo: this.config.sourceRepo,
            pull_number: item.number
          });
          prs.push(pr.data);
        } catch (error) {
          console.warn(`Error fetching PR #${item.number}: ${error.message}`);
        }
      }
      
      return prs;
    } catch (error) {
      console.error(`Error listing candidate PRs: ${error.message}`);
      return [];
    }
  }
  
  async getPRFiles(prNumber) {
    try {
      const filesRes = await this.octokit.request("GET /repos/{owner}/{repo}/pulls/{pull_number}/files", {
        owner: this.config.sourceOwner,
        repo: this.config.sourceRepo,
        pull_number: prNumber,
        per_page: 300
      });
      return filesRes.data || [];
    } catch (error) {
      console.warn(`Error fetching files for PR #${prNumber}: ${error.message}`);
      return [];
    }
  }
  
  /**
   * Extract JSON code blocks from PR description and comments
   */
  extractCodeExamples(pr) {
    const text = pr.body || "";
    const codeBlocks = [];
    
    // Match JSON code blocks with various markdown formats
    const patterns = [
      /```json\s*\n([\s\S]*?)\n```/gi,
      /```\s*\n(\{[\s\S]*?\})\s*\n```/gi,
      /`{[^`]*}`/gi
    ];
    
    patterns.forEach(pattern => {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        try {
          const jsonText = match[1] || match[0];
          // Clean up the JSON (remove comments, fix common issues)
          let cleanJson = jsonText
            .replace(/\/\/.*$/gm, '') // Remove line comments
            .replace(/,(\s*[}\]])/g, '$1') // Remove trailing commas
            .trim(); // Remove extra whitespace
          
          // Handle template variables more carefully
          cleanJson = cleanJson.replace(/"{{[^}]*}}"/g, '"{{placeholder}}"');
          
          const parsed = JSON.parse(cleanJson);
          codeBlocks.push({
            raw: match[0],
            json: parsed,
            text: cleanJson
          });
        } catch (e) {
          // Not valid JSON, skip
        }
      }
    });
    
    return codeBlocks;
  }

  /**
   * Derive RPC method information from code examples
   */
  deriveMethodInfo(codeBlocks) {
    const methods = [];
    
    codeBlocks.forEach(block => {
      if (block.json && block.json.method) {
        const method = {
          name: block.json.method,
          params: block.json.params || {},
          example: block.json,
          hasUserpass: !!block.json.userpass,
          hasMmrpc: !!block.json.mmrpc
        };
        
        // Extract parameter structure
        if (method.params && typeof method.params === 'object') {
          method.requestParams = this.extractParameterStructure(method.params);
        }
        
        methods.push(method);
      }
    });
    
    return methods;
  }

  /**
   * Extract parameter structure for documentation
   */
  extractParameterStructure(params, prefix = '') {
    const structure = [];
    
    Object.entries(params).forEach(([key, value]) => {
      const param = {
        name: prefix ? `${prefix}.${key}` : key,
        type: this.inferType(value),
        example: value
      };
      
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        param.type = 'object';
        param.properties = this.extractParameterStructure(value, param.name);
      }
      
      structure.push(param);
    });
    
    return structure;
  }

  /**
   * Infer parameter type from example value
   */
  inferType(value) {
    if (value === null) return 'null';
    if (typeof value === 'boolean') return 'boolean';
    if (typeof value === 'number') return Number.isInteger(value) ? 'integer' : 'number';
    if (typeof value === 'string') return 'string';
    if (Array.isArray(value)) return 'array';
    if (typeof value === 'object') return 'object';
    return 'unknown';
  }

  async generateAISummary(pr, files) {
    // Use OpenAI API for AI summaries
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      console.info("No OpenAI API key provided, skipping AI summary");
      return null;
    }

    try {
      const changedList = files.slice(0, 40).map(f => `- ${f.status} ${f.filename}`).join("\n");
      const prBody = (pr.body || "").slice(0, 2000);

      const prompt = `Summarize this code PR for documentation work in <=120 words.
Focus on what needs docs: new/changed features, RPC methods, parameters/defaults, breaking changes, and example snippets to update.

PR title: ${pr.title}
Changed files:
${changedList}

PR description (trimmed):
${prBody}`;

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
              content: "You are a concise technical documentation assistant. Summarize code changes for documentation teams."
            },
            {
              role: "user",
              content: prompt
            }
          ],
          max_tokens: 200,
          temperature: 0.2
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.warn(`OpenAI API failed: ${response.status} ${response.statusText}`);
        console.warn(`Error details: ${errorText}`);
        return null;
      }

      const data = await response.json();
      console.info("✅ Using OpenAI API for AI summary");
      return data.choices?.[0]?.message?.content?.trim() || null;

    } catch (error) {
      console.warn(`OpenAI API error: ${error.message}`);
      return null;
    }
  }
  
  buildIssueBody(pr, files, aiSummary) {
    const prUrl = pr.html_url;
    const marker = this.markerFor(prUrl);
    const changed = files.map(f => 
      `- \`${f.filename}\`${f.status !== 'modified' ? ` (${f.status})` : ""}`
    ).join("\n");
    
    // Extract code examples and method information
    const codeBlocks = this.extractCodeExamples(pr);
    const methods = this.deriveMethodInfo(codeBlocks);
    
    const sections = [
      marker,
      `### Source`,
      `- PR: ${prUrl}`,
      `- Title: **${pr.title}**`,
      `- Author: @${pr.user?.login}`,
      ``,
      aiSummary ? `### Summary\n${aiSummary}\n` : "",
    ];

    // Add extracted method information
    if (methods.length > 0) {
      sections.push(`### Detected RPC Methods`);
      methods.forEach(method => {
        sections.push(`#### Method: \`${method.name}\``);
        sections.push(`**Request Parameters:**`);
        
        if (method.requestParams && method.requestParams.length > 0) {
          method.requestParams.forEach(param => {
            sections.push(`- \`${param.name}\` (${param.type}): Example value \`${JSON.stringify(param.example)}\``);
            if (param.properties) {
              param.properties.forEach(prop => {
                sections.push(`  - \`${prop.name}\` (${prop.type}): Example value \`${JSON.stringify(prop.example)}\``);
              });
            }
          });
        } else {
          sections.push(`- No parameters detected`);
        }
        
        sections.push(`**Example Request:**`);
        sections.push('```json');
        sections.push(JSON.stringify(method.example, null, 2));
        sections.push('```');
        sections.push('');
      });
    }

    sections.push(
      `### Suggested docs tasks`,
      `- [ ] Update relevant pages`,
      `- [ ] Add/adjust RPC docs: purpose, parameters (types/defaults), and examples`,
      `- [ ] Provide JSON-RPC request/response samples`,
      `- [ ] Update changelog/What's New (if applicable)`,
      ``
    );

    if (methods.length > 0) {
      sections.push(`### Method Documentation Requirements`);
      methods.forEach(method => {
        sections.push(`- [ ] Create documentation file for \`${method.name}\``);
        sections.push(`- [ ] Define parameter types and validation rules`);
        sections.push(`- [ ] Document response structure`);
        sections.push(`- [ ] Add CompactTable components for request/response`);
        sections.push(`- [ ] Include working code examples`);
      });
      sections.push('');
    }

    sections.push(
      `### Changed files (for scoping)`,
      changed || "_No file listing_",
      ``,
      `> _This issue was generated automatically from PR analysis. Code examples and parameters were extracted automatically._`
    );
    
    return sections.filter(Boolean).join("\n");
  }
  
  async createDocumentationIssue(pr, files, aiSummary) {
    if (this.config.dryRun) {
      const dryRunUrl = `https://github.com/${this.config.targetOwner}/${this.config.targetRepo}/issues`;
      console.info(`📝 [DRY RUN] Would create docs issue for PR #${pr.number}`);
      console.info(`🔗 [DRY RUN] Issue would be created at: ${dryRunUrl}`);
      return { data: { number: 'DRY-RUN', html_url: dryRunUrl } };
    }
    
    const title = `Docs: PR #${pr.number} – ${pr.title}`;
    const body = this.buildIssueBody(pr, files, aiSummary);
    
    const created = await this.octokit.request("POST /repos/{owner}/{repo}/issues", {
      owner: this.config.targetOwner,
      repo: this.config.targetRepo,
      title,
      body,
      labels: ["docs-needed", "auto-generated"]
    });
    
    // Add a comment with backlink
    await this.octokit.request("POST /repos/{owner}/{repo}/issues/{issue_number}/comments", {
      owner: this.config.targetOwner,
      repo: this.config.targetRepo,
      issue_number: created.data.number,
      body: `Source PR: ${pr.html_url}`
    });
    
    // Log the created issue URL
    console.info(`🔗 Created issue: ${created.data.html_url}`);
    
    return created;
  }
  
  async processPR(pr) {
    try {
      this.stats.processed++;
      
      // Verify PR still has the required label and is open
      const hasLabel = pr.labels?.some(l => 
        (l.name || "").toLowerCase() === this.config.triggerLabel.toLowerCase()
      );
      
      if (!hasLabel || pr.state !== "open") {
        console.info(`Skipping PR #${pr.number}: missing label or not open`);
        this.stats.skipped++;
        return;
      }
      
      // Check if issue already exists
      const existing = await this.findExistingIssue(pr.html_url);
      if (existing) {
        console.info(`Docs issue already exists for PR #${pr.number}: #${existing.number}`);
        this.stats.skipped++;
        return;
      }
      
      // Get PR files and generate summary
      const files = await this.getPRFiles(pr.number);
      const aiSummary = await this.generateAISummary(pr, files);
      
      // Create the documentation issue
      const created = await this.createDocumentationIssue(pr, files, aiSummary);
      
      console.info(`Created docs issue #${created.data.number} for PR #${pr.number}`);
      this.stats.created++;
      
    } catch (error) {
      console.error(`Error processing PR #${pr.number}: ${error.message}`);
      this.stats.errors++;
    }
  }
  
  async run() {
    try {
      console.info(`🚀 Starting docs sync - DRY RUN: ${this.config.dryRun}`);
      
      const prs = await this.listCandidatePRs();
      console.info(`📋 Found ${prs.length} candidate PR(s) with label "${this.config.triggerLabel}"`);
      
      // Process PRs with some concurrency control
      const concurrency = 3;
      for (let i = 0; i < prs.length; i += concurrency) {
        const batch = prs.slice(i, i + concurrency);
        await Promise.all(batch.map(pr => this.processPR(pr)));
      }
      
      // Output final summary
      console.info(`\n📊 === SYNC SUMMARY ===`);
      console.info(`📈 PRs Processed: ${this.stats.processed}`);
      console.info(`✅ Issues Created: ${this.stats.created}`);
      console.info(`⏭️  PRs Skipped: ${this.stats.skipped}`);
      console.info(`❌ Errors: ${this.stats.errors}`);
      
      if (this.stats.errors > 0) {
        console.error(`❌ Sync completed with ${this.stats.errors} errors`);
        process.exit(1);
      } else {
        console.info(`🎉 Sync completed successfully!`);
      }
      
    } catch (error) {
      console.error(`💥 Sync failed: ${error.message}`);
      process.exit(1);
    }
  }
}

// Execute if run directly
if (require.main === module) {
  const manager = new DocsSyncManager();
  manager.run().catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

module.exports = DocsSyncManager;
