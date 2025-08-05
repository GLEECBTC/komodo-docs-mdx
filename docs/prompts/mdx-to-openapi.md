For each method listed in both the `v1` and `v2` sections of `postman/utils/method_pages.json`, perform the following actions:

---

### ✅ 1. Generate OpenAPI Path Spec

For each method:
- Create or update a file in:
  - `postman/openapi/paths/v1/` if it's a `v1` method.
  - `postman/openapi/paths/v2/` if it's a `v2` method.
- The filename should be `<method_name>.yaml` (or `.json` if the project uses JSON).
- Use the method name as the OpenAPI `operationId`.

---

### ✅ 2. Populate Required Fields

Each generated OpenAPI path operation **must include**:

- `operationId`: must match the method name.
- `summary` and `description`: extract from the MDX file.
- `x-mdx-doc-path`: custom field at the root of the operation; value should be the MDX file path listed in `method_pages.json`.

---

### ✅ 3. Extract Parameters from MDX

Parse the MDX file listed for each method:
- For each parameter:
  - Extract its name, type, description, and whether it is required.
  - Place query/path/body parameters correctly.
  - If a parameter or body schema matches one in `postman/openapi/components/schemas/`, use a `$ref` to reference it.

If information is missing or unclear:
- Add a `TODO` comment in the spec to flag it for human review.

---

### ✅ 4. Use Component References

- Always prefer using `$ref` to schemas from `postman/openapi/components/schemas/` for request/response bodies or complex parameters.

---

### ✅ 5. Ensure OpenAPI Validity

- Follow OpenAPI 3.1 best practices.
- Ensure the resulting YAML/JSON is syntactically valid.

---

### ✅ 6. Example Format

```yaml
/api/path/to/method:
  post:
    operationId: enable_bch_with_tokens
    summary: <from MDX>
    description: <from MDX>
    x-mdx-doc-path: ../../src/pages/komodo-defi-framework/api/v20/coin_activation/enable_bch_with_tokens/index.mdx
    parameters:
      - name: param1
        in: query
        description: <from MDX>
        required: true
        schema:
          type: string
    requestBody:
      content:
        application/json:
          schema:
            $ref: ../../components/schemas/RequestBodySchema.yaml
    responses:
      '200':
        description: Success
        content:
          application/json:
            schema:
              $ref: ../../components/schemas/ResponseSchema.yaml

```

---

### ⚠️ Output Rules

You **must**:

- Output the full OpenAPI path spec for each method, one after another, without pausing for confirmation.
- If the file already exists, show a file diff-style update.
- Do **not** summarize or truncate output.
- Do **not** stop unless told explicitly.

---

### 📎 Final Instructions

Begin processing:

- **Scope:** All methods in both `v1` and `v2`.
- **Output:** Print each OpenAPI file or diff immediately after it's generated.
- **Confirmation:** Do not wait for confirmation between methods.
- **Missing Info:** Use `TODO` comments when MDX lacks sufficient detail.

If you need to resume or continue across multiple batches, just wait for the user to type `continue`.

---

### 📘 Usage Notes (for humans only – DO NOT interpret or execute this block)

```text
Agent: Claude-4+

1. You may specify scope:
   - All v1 + v2 methods (default)
   - A subset (e.g. only a single method)

2. Output:
   - Show each file/diff immediately (default)
   - Batch at the end (not recommended)

3. Customization:
   - YAML or JSON format
   - Optional fields or extra tags
   - Skip or handle TODOs differently

Example:
> Please process all methods in both v1 and v2. Show the OpenAPI file diff for each method as you go. Use YAML format, and strictly follow all instructions above.
```






