#!/usr/bin/env python3
"""
This module contains centralized regular expression constants for the project.
"""

import re

# Regex to find ## method_name {{...}}
METHOD_HEADING_REGEX = re.compile(r"^##\s+([a-zA-Z0-9_:]+)\s*\{\{.*\}\}\s*$", re.MULTILINE)

# Regex to find all code blocks for specific languages
CODE_BLOCK_REGEX = re.compile(r"```(json|jsonc|bash|sh|ps1|powershell)\s*\n(.*?)\n```", re.DOTALL)

# Regex to find "userpass" in a JSON string
USERPASS_REGEX = re.compile(r'"userpass"\s*:\s*"[^"]+"')

# Regex to find content between a method heading and the next heading or EOF
MDX_SECTION_REGEX = re.compile(
    r"(^##\s+[a-zA-Z0-9_:]+\s*\{\{.*?\}\}.*?)(?=^## |^# |$)",
    re.MULTILINE | re.DOTALL
) 