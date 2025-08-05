# Style Guide

## Table of Contents
1. [Document Version](#document-version)
2. [MDX File Requirements](#mdx-file-requirements)
3. [Structure](#structure)
4. [General Guidelines](#general-guidelines)
5. [Syntax](#syntax)
6. [Tables](#tables)
7. [Variables](#variables)
8. [Templates](#templates)
9. [How to Contribute](#how-to-contribute)
10. [Components](#components)
11. [New Rule: Use of Common Objects and Enums](#new-rule-use-of-common-objects-and-enums)
12. [Sidebar and Method Heading Naming Rules](#sidebar-and-method-heading-naming-rules)
13. [Overview Page Heading Hierarchy](#overview-page-heading-hierarchy)

## Document Version

**Last Updated:** June 2025
**Recent Changes:**
- Integrated API Documentation table standards (Request Arguments format)
- Added MDX example standards and best practices
- Consolidated multiple style documents into unified guide
- Updated KDF API Method Documentation Standard with table formatting requirements

---

# Introduction


From a user's perspective:
- If they can't find information about a feature in the documentation, it means that **the feature doesn't exist**.
- If there is information about a feature, but it's wrong or confusing, it means that **the feature is broken**.
- If the documentation is hard to read, it means that **the feature is hard to use**.

These guidelines are currently a work in progress. All new documentation should follow the guidelines below, and existing documentation should be updated to match when time permits.

## General Guidelines

- Use [American English spelling](https://www.thefreedictionary.com/American-English-vs-British-English-Spelling.htm)
- Use the [Oxford comma](https://www.youtube.com/watch?v=xUt7-B8IfxU)
- Use [Bluebook Title Case](https://titlecaseconverter.com/rules/#BB) for headings and products. All enum and common structure section headings must use Bluebook title case with no spaces (e.g. EthPrivKeyActivationPolicyEnum).
- Use [Sentence case](https://apastyle.apa.org/style-grammar-guidelines/capitalization/sentence-case) for menu items, tabs, buttons, links, and all other text.
- Use [kebab-case](https://developer.mozilla.org/en-US/docs/Glossary/Kebab_case) for anchor links and content slugs.
- Keep it concise: Stay on point. Avoid unnecessary words or phrases that do not add value to the content.
- Use simple language: Where possible, avoid jargon or technical terms that may be unfamiliar to the reader. When unavoidable, provide a link to a definition or explanation of the term.
- Use bullet points and numbered lists to break up long paragraphs to make the content more readable.
- Don't skimp on important detail: If a feature is complex, it's better to provide too much information than not enough. Where appropriate it may be better to split the additional information into its own page and add a link to it for those who want to dig deeper.
- Be generous with hyperlinks: Link to relevant documentation or resources, whether to somewhere else within our internal docs or to a respected external source. This will provide additional context and help users better understand the content.
- Use absolute links for internal docs: The `pages` folder is the root directory for internal docs. Us absolute links to reference other pages within the `pages` folder, for example: `[Komodo DeFi Framework API methods](/komodo-defi-framework/api/#sub-section-header)`. The url must end with a slash.
- If a user action requires a sequence of steps, consider using a flowchart to illustrate the process.
- Use images or diagrams to help explain complex concepts or processes. This will make the content more engaging and easier to understand.
- Proofread and test your content: Make sure to proofread your MDX file for errors and test any code snippets or examples to ensure they work as expected. Ask AI to review it for syntax and style compliance.

## Templates

Use the linked templates below as a starting point for new documentation pages.

- [Komodo DeFi Framework API method template](../../docs/templates/komodefi_method.mdx)
- [Komodo DeFi Framework API overview template](../../docs/templates/komodefi_overview.mdx)

## Syntax & Structure 

### General
- All MDX files must begin with `export const title = ...` and `export const description = ...`. These are required for build and navigation. Never remove these fields.
- Use `#` for page headings. These are generally method names, in human format (title case, no underscores). Remove `Komodo DeFi Framework Method: ` or other verbose preambles.
- Use `##` for subheadings. These are generally method names. This line should also include label/tag like `{{label : 'method_name', tag : 'API-v2'}}`.
- **IMPORTANT**: Method headings MUST use the complete API method name exactly as it appears in the request (e.g., `stream::orderbook::enable` not just `orderbook_enable`).
- Use `###` for request/response parameter table titles.
- Use `####` for request/response examples (like #### 📌 Examples and #### ⚠️ Error Responses)
- Use only the `<DevComment>` component tags for comments. No NOT use markdown comments.
- No markdown/mdx comments in tables' rows
- Use a 4-space indent in code blocks. This will make the parameters and values easier to read.

## KDF Methods
- For Komodo DeFi Framework API methods, the userpass variable should always be `RPC_UserP@SSW0RD`
- The `index.mdx` file should contain a heading with the method name and a description of the method.  
- All API methods should be placed in their own `index.mdx` file, within a folder named after the method.  
- Each file should contain a CodeGroup with at least one example of how to make a complete request, including all required parameters.
- Each request should be in a CodeGroup. Its response should be in a CollapsibleSection. There should only be one response per CollapsibleSection, but there may be multiple responses to a request. 
- Where a request includes optional parameters which will result in different response structures, the file should contain a CodeGroup for each possible request variation, followed by a CollapsibleSection for the response of each example.
- CollapsibleSection text should match the CodeGroup title for consistency (e.g., if CodeGroup title is "Method Name", CollapsibleSection should be "Hide/Show Method Name Response").
- Where a group of parameters are nested within a common structure, an anchor link to an exising common structure table should be used. If one does not exist, it should be created.
- Where a parameters has a finite set of valid values, an anchor link to an exising enum table should be used. If one does not exist, it should be created.
- Where a method or parameter is deprecated, this should be communicated in the method heading tag or request parameters table.
- Below the request/response examples, include a CollapsibleSection for each the methods error types. This should provide details on what causes the error and how it might be resolved.




### KDF Method Documentation Format

- **`export const title`**:
  - Format: `export const title = "Komodo DeFi Framework Method: [Human-Readable Title]";`
  - Example: `export const title = "Komodo DeFi Framework Method: Cancel Enable BCH Task";`

- **`export const description`**:
  - Provide a concise description of the method's purpose.
  - Example: `export const description = "Cancel the enable BCH task in the Komodo DeFi Framework API.";`

- **Main Heading (`#`)**:
  - Use a human-readable, title-cased phrase that describes the method's function.
  - Example: `# Cancel Enable BCH Task`

- **Subheading (`##`)**:
  - Use the exact API method name, with label and tag.
  - The `##` subheading and the `label` for every KDF method page must both be the exact API method name, exactly as it appears in the API, followed by a tag from the allowed list.
  - The `label` in the curly braces must also be the exact API method name, matching the visible heading, with no changes.
  - The `tag` must be one of the following, as appropriate for the page:
      - API-v1 (for v1/legacy methods)
      - API-v2 (for v2 methods)
      - deprecated (for deprecated methods)
      - overview (for overview pages)
      - struct (for common structures)
      - enum (for enums)
  - Example:`## lightning::payments::send_payment {{label : 'lightning::payments::send_payment', tag : 'API-v2'}}`

- **Request Parameter Tables**
  - Include a reference table listing all **request** parameters with the following 5 columns: Parameter, Type, Required, Default, Description
  - **IMPORTANT**: If there are no optional parameters (all parameters are required), you can use a 4-column format: Parameter, Type, Required, Description (omitting the Default column)
  - Parameters should be listed alphabetically within their groupings (required parameters first, then optional parameters)
  - The Required column should contain "✓" for required parameters and "✗" for optional parameters (centered alignment)
  - If no default values are defined for any parameter, omit the Default column entirely.
  - If any parameter has a default value, the Default column (centered alignment) must be present and all default values must be wrapped in backticks (e.g., `10`, `false`) .
  - Where specific parameters only apply for a specific action, this should be identified at the start of the parameter's description
  - Example:
    ```mdx
    | Parameter | Type    | Required | Default | Description                                                                                   |
    | --------- | ------- | :------: | :-----: | --------------------------------------------------------------------------------------------- |
    | coin      | string  | ✓        | -       | The name of the coin the user desires to activate.                                            |
    | amount    | float   | ✗*       | -       | The amount of balance to send. Required unless `max` is `true`.                               |
    | fee       | object  | ✗        | -       | A standard [FeeInfo](/komodo-defi-framework/api/common_structures/#FeeInfo) object.           |
    | max       | boolean | ✗        | `false` | Send whole balance.                                                                           |
    | memo      | string  | ✗        | -       | Used for ZHTLC and Tendermint coins only. Attaches a memo to the transaction.                |
    ```

- **Response Parameter Tables**
  - Include a reference table listing all **response** parameters with Parameter, Type, and Description columns
  - Parameters should be listed alphabetically

- **Examples**:
  - Include complete request examples in a `CodeGroup`.
  - Use `CollapsibleSection` for responses, matching the `CodeGroup` title for consistency.

### Error Responses

- The Error Types section should sit below the Request Parameter Tables, Response Parameter Tables and Examples sections (at the bottom of the page).
- Error types should be listed in a table format with columns for Parameter, Type, and Description.
- Error responses should be directly below the ErrorTypes table.
- Each error response should be enclosed within a `CollapsibleSection` with `expandedText` and `collapsedText` attributes set to "Hide Error Responses" and "Show Error Responses" respectively.

Example:

```mdx
### Error Types

| Parameter        | Type   | Description                                                              |
| ---------------- | ------ | ------------------------------------------------------------------------ |
| NoSuchCoin       | string | The specified coin was not found or is not activated yet                 |
| InvalidHashError | string | The specified `hash` is not valid                                        |
| Transport        | string | The request was failed due to a network error                            |
| HashNotExist     | string | The specified `hash` does not exist                                      |
| InternalError    | string | The request was failed due to a Komodo DeFi Framework API internal error |

<CollapsibleSection expandedText="Hide Error Responses" collapsedText="Show Error Responses">
  ##### Error Response (No Such Coin)

  ```json
  {
      "mmrpc": "2.0",
      "error": "No such coin KMD",
      "error_path": "lp_coins",
      "error_trace": "lp_coins:2234] lp_coins:2156]",
      "error_type": "NoSuchCoin",
      "error_data": {
          "coin": "KMD"
      },
      "id": 0
  }
  ```

  ##### Error (Invalid Hash)

  ```json
  {
      "mmrpc": "2.0",
      "error": "Invalid  hash: Invalid input length",
      "error_path": "utxo_common",
      "error_trace": "utxo_common:1809]",
      "error_type": "InvalidHashError",
      "error_data": "Invalid input length",
      "id": 1
  }
  ```
</CollapsibleSection>

### Method Group Overviews

- **`export const title`**:
  - Format: `export const title = "Komodo DeFi Framework Method Overview: [Human-Readable Title]";`
  - Example: `export const title = "Komodo DeFi Framework Method Overview: Enable UTXO Tasks";`

- **`export const description`**:
  - Provide a concise description of the method group's purpose.
  - Example: `export const description = "An overview of the Enable UTXO tasks in the Komodo DeFi Framework API.";`

- **Main Heading (`#`)**:
  - Use a human-readable, title-cased phrase that describes the method's function.
  - Example: `# Enable UTXO Tasks`

- **Subheading (`##`)**:
  - Use the exact API method name, with label and tag.
  - The `##` subheading and the `label` for every KDF method page must both be the exact API method name, exactly as it appears in the API, followed by a tag from the allowed list.
  - The `label` in the curly braces must also be the exact API method name, matching the visible heading, with no changes.
  - The `tag` must be `overview`
  - Example:`## task::enable_utxo {{label : 'task::enable_utxo', tag : 'overview'}}`

**Example Structure:**

```mdx
export const title = "Komodo DeFi Framework Overview: UTXO Activation";
export const description =
  "This section provides an overview of the task managed activation methods for UTXO coins like KMD, LTC, BTC & DOGE.";
  
# Enable UTXO Tasks

## task::enable_utxo {{label : 'task::enable_utxo', tag : 'overview'}}

This section provides an overview of the task managed activation methods for UTXO coins like KMD, LTC, BTC & DOGE. Each method is now documented in its own dedicated page:

*   [task::enable\_utxo::init](/komodo-defi-framework/api/v20/coin_activation/task_managed/enable_utxo/init/)
*   [task::enable\_utxo::status](/komodo-defi-framework/api/v20/coin_activation/task_managed/enable_utxo/status/)
*   [task::enable\_utxo::user\_action](/komodo-defi-framework/api/v20/coin_activation/task_managed/enable_utxo/user_action/)
*   [task::enable\_utxo::cancel](/komodo-defi-framework/api/v20/coin_activation/task_managed/enable_utxo/cancel/)

```


### Common Structures

- Look for opportunities to use or create common objects and enums.
- Enums and common structures should be used or created wherever possible. Dot notation is to be avoided.
- Common structure objects should be grouped by category and listed alphabetically in the file which contains them.
- Anchor links to all methods which use the structure should be listed under its table.
- Reference or define these enums in parameter/response tables and documentation whereever possible.


## Sidebar and Method Heading Naming Rules

- In `sidebar.json`, the `title` value for each method link must be the **exact API method name** (e.g., `lightning::payments::send_payment`), not a humanized or prettified version. The only exception is when the link does not point to a method (e.g., overview or non-method pages).




## Components

Pages are heavily [**MDX**](https://mdxjs.com/) ("markdown extension") based, which allows us to use JSX in markdown content. You can have imported components (JSX) within your content and more. Read more about MDX here [https://mdxjs.com/docs/what-is-mdx/](https://mdxjs.com/docs/what-is-mdx/).

### Note

The `Note` component displays an info/warning/error styled message with predefined icons and colors:

```mdx
<Note type="info">
  Information message here.
</Note>

<Note type="warning">
  Warning message here.
</Note>

<Note type="error">
  Error message here.
</Note>
```

### CollapsibleSection

This renders a button with a specified text based on its state (expanded or collapsed). You'll mostly use this for API responses:

```mdx
<CollapsibleSection expandedText='Hide Response' collapsedText='Show Response'>

```json
{
   "mmrpc": "2.0",
   "result": "success",
   "id": null
}
```

</CollapsibleSection>

### Images

Images should be added to the related subfolder within the `src/images` folder, and rendered using the `OptimizedImage` component:

```jsx
import komodefiManiq from "@/public/images/docs/komodefi-maniq.webp";

<OptimizedImage title="Komodo DeFi Framework" src={komodefiManiq} alt="Komodo DeFi Framework" classNaming="w-full" />
```
