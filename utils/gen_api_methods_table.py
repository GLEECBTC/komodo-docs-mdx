#!/usr/bin/env python3
import os
import glob
import re
import sys
import json
import logging
import unicodedata

script_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.dirname(script_path)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def slugify_for_api_table(text):
    text = text.split("{{")[0].strip()
    text = text.lower()
    # Normalize common separators to hyphens
    text = text.replace("_", "-")
    text = re.sub(r"[:]+", "-", text)         # convert :: to -
    text = re.sub(r"\s+", "-", text)          # spaces to -
    # Remove anything that's not alphanumeric or hyphen
    text = re.sub(r"[^a-z0-9\-]", "", text)
    # Collapse multiple hyphens
    text = re.sub(r"\-+", "-", text).strip("-")
    return text

def slugify_heading(text):
    """
    Best-effort replication of heading slug generation used by docs:
    - Drop MDX annotations (e.g., `{{ ... }}`)
    - Normalize unicode, lowercase
    - Replace spaces/underscores with hyphens
    - Remove non-alphanumeric/hyphen chars
    """
    text = text.split("{{")[0].strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = text.replace("_", "-")
    text = re.sub(r"[:]+", "-", text)         # convert :: to -
    text = re.sub(r"\s+", "-", text)  # spaces to hyphens
    text = re.sub(r"[^a-z0-9\-]", "", text)
    text = re.sub(r"\-+", "-", text).strip("-")
    return text

def compute_file_slugs(path_to_file):
    """
    Fallback slug collector when filepathSlugs.json is stale or missing entries.
    Collects markdown headings and generates unique slugs.
    """
    slugs = []
    slug_counts = {}
    try:
        with open(path_to_file, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.rstrip("\n")
                if line.startswith("#"):
                    # Remove leading hashes and whitespace
                    heading_text = line.lstrip("#").strip()
                    if not heading_text:
                        continue
                    base = slugify_heading(heading_text)
                    if not base:
                        continue
                    # Ensure uniqueness similar to slugifyWithCounter
                    count = slug_counts.get(base, 0)
                    slug_counts[base] = count + 1
                    if count == 0:
                        slugs.append(base)
                    else:
                        slugs.append(f"{base}-{count+1}")
    except Exception as e:
        logger.error(f"Failed to compute fallback slugs for {path_to_file}: {e}")
        return []
    return slugs

def get_method_name(line):
    # Try to capture CodeGroup label="..."
    if 'CodeGroup' in line and "label" in line:
        # Support both single and double quotes
        m = re.search(r'label\s*=\s*["\']([^"\']+)["\']', line)
        if m:
            return m.group(1)
    # Fallback: capture heading labels like:
    # # title {{label : 'method_name', ...}}
    # or with any heading level (##, ###, etc.)
    if "label" in line:
        m = re.search(r'label\s*:\s*["\']([^"\']+)["\']', line)
        if m:
            return m.group(1).strip()
    return ""

def ignore_file(file):
    for i in ["common_structures",
              "batch_requests",
              "v20-dev/index.mdx",
              "v20/index.mdx",
              "legacy/index.mdx",
              "legacy/help/index.mdx",
              "v20/utils/index.mdx",
              "rational_number_note",
              "komodo-defi-framework/index.mdx",
              "komodo-defi-framework/tutorials",
              "komodo-defi-framework/changelog",
              "komodo-defi-framework/setup",
              "komodo-defi-framework/api/index.mdx",
              "komodo-defi-framework/api/v20/coin_activation/index.mdx",
              "komodo-defi-framework/api/v20/coin_activation/task_managed/enable_sia/index.mdx",
              "task_managed/index.mdx",
              "non_fungible_tokens/index.mdx",
              "query_nft_database_tables/index.mdx",
              "v20/streaming/index.mdx",
              "v20/lightning/index.mdx",
              "v20/wallet/index.mdx",
              "v20/wallet/staking/index.mdx",
              "v20/wallet/tx/index.mdx",
              "v20/wallet/fee_management/index.mdx",
              "swaps_and_orders/index.mdx"
            ]:
        if i in file:
            return True
    return False

def get_method_slug(method):
    if method == "":
        return ""
    return slugify_for_api_table(method)

def get_method_link(method_file, doc_path, file_slugs) -> dict:
    with open(method_file, 'r') as f:
        for line in f.readlines():
            method = get_method_name(line)
            if method and method.strip():
                method_slug = slugify_for_api_table(method)
                if method_slug not in file_slugs:
                    method_slug = file_slugs[0]
                return {
                    "link": f"[{method}]({doc_path}/#{method_slug})",
                    "method": method,
                    "doc_url": doc_path
                }
    return {}


def gen_api_methods_table():
    slugs = json.loads(open(f'{root_path}/filepathSlugs.json', 'r').read())
    komodefi_files = glob.glob(f'{root_path}/src/pages/komodo-defi-framework/**/index.mdx', recursive = True)
    methods_dict = {
        "legacy": [],
        "v20": [],
        "v20-dev": []
    }
    methods_list = []
    updated_slugs = False
    for file in komodefi_files:
            
        if ignore_file(file):
            continue
        file_methods_list = []
        relative_path = file.replace(f'{root_path}/', '')
        key = relative_path
        if key not in slugs:
            logger.warning(
                "Missing slug entry in filepathSlugs.json for '%s'. "
                "Attempting to compute fallback slugs from file headings. "
                "If you keep seeing this, regenerate slugs via: "
                "node utils/js/validate_update_internal_links_userpass.js", key
            )
            computed = compute_file_slugs(file)
            if not computed:
                sys.exit(
                    f"Missing slug entry for '{key}' and failed to compute fallback slugs.\n"
                    f"Please run: node utils/js/validate_update_internal_links_userpass.js\n"
                    f"Then re-run this script."
                )
            slugs[key] = computed
            updated_slugs = True
        file_slugs = slugs[key]
        with open(file, 'r') as f:

            doc_path = file.replace(f'{root_path}/src/pages', '').replace('/index.mdx', '')
            doc_split = doc_path.split('/')
            if len(doc_split) > 3:
                section = doc_split[3]
            else:
                logger.error(f"###### No section found in {file}!")
                continue
            if section not in methods_dict:
                logger.error(f"###### {section} section not found in methods_dict!")
                continue
            method_link = get_method_link(file, doc_path, file_slugs)
            if "link" not in method_link:
                logger.error(f"###### No method link found in {file}!")
                continue
            methods_dict[section].append(method_link)
            file_methods_list.append(method_link["method"])
                        

        # print(f"###### Methods in {file}: {file_methods_list}")
        if len(file_methods_list) > 0:
            methods_list.extend(file_methods_list)
        else:
            sys.exit(f"###### No methods found in {file}!")
    methods_list = sorted(list(set(methods_list)))

    # Persist any newly computed slugs back to filepathSlugs.json to plug the gap for future runs
    if updated_slugs:
        try:
            with open(f'{root_path}/filepathSlugs.json', 'w', encoding='utf-8') as f_slugs:
                json.dump(slugs, f_slugs, indent=2, ensure_ascii=False)
            logger.info("Updated filepathSlugs.json with missing entries.")
        except Exception as e:
            logger.warning("Failed to persist updated slugs to filepathSlugs.json: %s", e)

    with open(f'{script_path}/methods_table.template', 'r') as f:
        template = f.read()
        with open(f'{root_path}/src/pages/komodo-defi-framework/api/index.mdx', 'w') as f2:
            f2.write(template)
            for method in methods_list:
                legacy = ""
                v20 = ""
                v20_dev = ""
                for i in methods_dict.keys():
                    for j in methods_dict[i]:
                        if j["method"] == method:
                            if i == "legacy":
                                legacy = j["link"]
                            if i == "v20":
                                v20 = j["link"]
                            if i == "v20-dev":
                                v20_dev = j["link"]

                legacy = escape_underscores(legacy)
                v20 = escape_underscores(v20)
                v20_dev = escape_underscores(v20_dev)
                line = "| {:^108} | {:^108} | {:^108} |".format(legacy, v20, v20_dev)
                f2.write(f"{line}\n")

def escape_underscores(s):
    output = ""
    for letter in s:
        if letter == "_":
            output += "\\_"
        else:
            output += letter
    return output

if __name__ == '__main__':
    gen_api_methods_table()
