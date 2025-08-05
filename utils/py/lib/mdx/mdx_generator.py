#!/usr/bin/env python3
"""
This module contains the MdxGenerator class for generating
MDX documentation for Komodo DeFi Framework methods.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

from ..utils.logging_utils import get_logger
from .mdx_draft_generator import MethodDetails, Parameter

logger = get_logger(__name__)


class MdxGenerator:
    """
    Generates comprehensive MDX documentation for a given API method.
    """

    def __init__(self, template_path: Optional[Path] = None):
        if template_path:
            self.template_path = template_path
        else:
            # Default path relative to this file's location
            self.template_path = Path(__file__).parent.parent.parent.parent / "docs/templates/komodefi_method.mdx"
        
        if not self.template_path.exists():
            logger.error(f"Template file not found at: {self.template_path}")
            self.template_content = self.get_basic_template()
        else:
            self.template_content = self.template_path.read_text(encoding="utf-8")
        logger.info(f"MdxGenerator initialized with template: {self.template_path}")


    def get_basic_template(self) -> str:
        """Return a basic template if the template file is not found."""
        return '''export const title = "{title}";
export const description = "{description}";

# {human_title}

## {method_name} {{{{label : '{method_name}', tag : '{api_tag}'}}}}

{description}

### Request Parameters

{request_table}

#### 📌 Examples

<CodeGroup title="" tag="POST" label="{method_name}" mm2MethodDecorate="true">
```json
{example_request}
```
</CodeGroup>

### Response Parameters

{response_table}

<CollapsibleSection expandedText='Hide Response' collapsedText='Show Response'>

#### Response

```json
{example_response}
```
</CollapsibleSection>

### Error Types

{error_table}

<CollapsibleSection expandedText="Hide Error Responses" collapsedText="Show Error Responses">
{error_responses}
</CollapsibleSection>

<Note>
View the source code at: https://github.com/KomodoPlatform/komodo-defi-framework/blob/dev/{source_file}
</Note>'''

    def generate_parameter_table(self, parameters: List[Parameter], is_request: bool) -> str:
        """Generate a parameter table in markdown format."""
        if not parameters:
            return "No parameters."

        # For requests, we may show a 'Default' column.
        has_defaults = is_request and any(p.default_value is not None or not p.required for p in parameters)
        
        headers = ["Parameter", "Type", "Required"]
        if has_defaults:
            headers.append("Default")
        headers.append("Description")
        
        header_line = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join(["-" * len(h) for h in headers]) + " |"
        # Adjust alignment for "Required" and "Default"
        sep_parts = separator.split("|")
        sep_parts[3] = " :------: "  # Required
        if has_defaults:
            sep_parts[4] = " :-----: "  # Default
        separator = "|".join(sep_parts)

        table_lines = [header_line, separator]
        
        sorted_params = sorted(parameters, key=lambda p: (not p.required, p.name))
        
        for param in sorted_params:
            param_type = f"array of {param.param_type}s" if param.is_array and param.param_type != 'array' else param.param_type
            required_mark = "✓" if param.required else "✗"
            
            row_data = [param.name, param_type, required_mark]
            
            if has_defaults:
                default_val = "-"
                if param.default_value:
                    default_val = f"`{param.default_value}`"
                elif not param.required:
                    if param.param_type == 'boolean':
                        default_val = "`false`"
                row_data.append(default_val)

            row_data.append(param.description)
            table_lines.append("| " + " | ".join(row_data) + " |")
        
        return "\n".join(table_lines)

    def generate_error_table(self, error_types: List[str]) -> str:
        """Generate error types table."""
        if not error_types:
            return "No specific error types documented."
        
        headers = "| Parameter | Type | Description |"
        separator = "| --------- | ---- | ----------- |"
        table_lines = [headers, separator]
        
        error_descriptions = {
            "NoSuchCoin": "The specified coin was not found or is not activated yet",
            "InvalidParam": "One or more parameters are invalid or missing",
            "InternalError": "The request failed due to a Komodo DeFi Framework API internal error",
            "Transport": "The request failed due to a network error",
            "Timeout": "The operation timed out",
            "InvalidAddress": "The specified address is not valid",
            "InsufficientBalance": "Insufficient balance for the operation",
            "CoinIsNotActive": "The specified coin is not currently active",
            "RpcError": "An RPC error occurred during the operation"
        }
        
        for error_type in sorted(error_types):
            description = error_descriptions.get(error_type, f"Error related to {error_type.lower()} operation")
            row = f"| {error_type} | string | {description} |"
            table_lines.append(row)
        
        return "\n".join(table_lines)

    def generate_error_responses(self, error_types: List[str]) -> str:
        """Generate example error responses."""
        if not error_types:
            return "##### Generic Error\n\n```json\n{\n  \"mmrpc\": \"2.0\",\n  \"error\": \"Internal error\",\n  \"error_path\": \"method\",\n  \"error_trace\": \"method:123]\",\n  \"error_type\": \"InternalError\",\n  \"id\": null\n}\n```"
        
        error_examples = []
        
        common_errors = {
            "NoSuchCoin": lambda i: (
                "Error Response (No Such Coin)",
                {"mmrpc": "2.0", "error": "No such coin BTC", "error_path": "coin_activation", "error_trace": "coin_activation:123]", "error_type": "NoSuchCoin", "error_data": {"coin": "BTC"}, "id": i}
            ),
            "InvalidParam": lambda i: (
                "Error Response (Invalid Parameter)",
                {"mmrpc": "2.0", "error": "Invalid parameter: missing required field", "error_path": "method", "error_trace": "method:456]", "error_type": "InvalidParam", "id": i}
            ),
            "InternalError": lambda i: (
                "Error Response (Internal Error)",
                {"mmrpc": "2.0", "error": "Internal error occurred", "error_path": "method", "error_trace": "method:789]", "error_type": "InternalError", "id": i}
            )
        }

        for i, error_type in enumerate(error_types[:3]):  # Limit to 3 examples
            if error_type in common_errors:
                title, example = common_errors[error_type](i)
            else:
                title = f"Error Response ({error_type})"
                example = {"mmrpc": "2.0", "error": f"{error_type} error occurred", "error_path": "method", "error_trace": "method:999]", "error_type": error_type, "id": i}
            
            error_json = json.dumps(example, indent=2)
            error_examples.append(f"##### {title}\n\n```json\n{error_json}\n```")
        
        return "\n\n".join(error_examples)

    def generate_example_response(self, response_params: List[Parameter]) -> str:
        """Generate an example response based on response parameters."""
        if not response_params:
            return '{\n  "mmrpc": "2.0",\n  "result": "success",\n  "id": null\n}'
        
        result = {}
        for param in response_params:
            # Provide more meaningful default example values
            param_type = param.param_type.lower()
            name = param.name.lower()
            if param_type == 'string':
                if 'coin' in name: result[param.name] = "KMD"
                elif 'status' in name: result[param.name] = "Ok"
                elif 'hash' in name: result[param.name] = "0x" + "a" * 64
                else: result[param.name] = "example_string"
            elif param_type in ['integer', 'u64', 'i32']: result[param.name] = 123
            elif param_type in ['float', 'double', 'bigdecimal']: result[param.name] = 123.456
            elif param_type == 'boolean': result[param.name] = True
            elif param.is_array: result[param.name] = ["item1", "item2"]
            elif param_type == 'object': result[param.name] = {"key": "value"}
            else: result[param.name] = "unknown_type_value"
        
        response = {"mmrpc": "2.0", "result": result, "id": None}
        return json.dumps(response, indent=2)

    def generate_export_title(self, human_title: str) -> str:
        """Generate the export title following style guide rules."""
        return f'Komodo DeFi Framework Method: {human_title}'
    
    def generate_export_description(self, method_name: str, description: str) -> str:
        """Generate the export description."""
        clean_desc = description.replace(f"`{method_name}`", method_name)
        return f"{clean_desc.rstrip('.')} in the Komodo DeFi Framework API."
    
    def get_source_file_reference(self, source_files: List[str]) -> str:
        """Get the first relevant source file for the Note section."""
        if not source_files:
            return "mm2src/"
        
        impl_files = [f for f in source_files if 'test' not in f.lower() and f.endswith('.rs')]
        return impl_files[0] if impl_files else source_files[0]

    def generate(self, method_details: MethodDetails) -> str:
        """
        Generates and returns the complete MDX documentation content as a string.
        File I/O is handled by the calling module.
        """
        logger.info(f"Generating docs content for {method_details.name}")

        request_table = self.generate_parameter_table(method_details.request_params, is_request=True)
        response_table = self.generate_parameter_table(method_details.response_params, is_request=False)
        error_table = self.generate_error_table(method_details.error_types)
        error_responses = self.generate_error_responses(method_details.error_types)
        
        example_request = json.dumps(method_details.examples[0] if method_details.examples else {}, indent=2)
        example_response = self.generate_example_response(method_details.response_params)
        
        source_file = self.get_source_file_reference(method_details.source_files)
        
        # Replace template placeholders
        content = self.template_content.format(
            title=self.generate_export_title(method_details.human_title),
            description=self.generate_export_description(method_details.name, method_details.description),
            human_title=method_details.human_title,
            method_name=method_details.name,
            api_tag=method_details.api_tag,
            request_table=request_table,
            response_table=response_table,
            error_table=error_table,
            error_responses=error_responses,
            example_request=example_request,
            example_response=example_response,
            source_file=source_file
        )
        
        return self.clean_up_formatting(content)

    def clean_up_formatting(self, content: str) -> str:
        """Clean up formatting issues in the generated content."""
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'\n(#+)\s*([^\n]+)\n', r'\n\n\1 \2\n\n', content)
        content = re.sub(r'\|\s*\|\s*', '| ', content)
        content = re.sub(r'\s*\|\s*\n', ' |\n', content)
        content = re.sub(r'\n(<(CodeGroup|CollapsibleSection))', r'\n\n\1', content)
        content = re.sub(r'(</(CodeGroup|CollapsibleSection))>)\n', r'\1\n\n', content)
        
        return content.strip() + '\n' 