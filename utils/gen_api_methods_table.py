#!/usr/bin/env python3
import os
import glob
import re
import sys
import json

script_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.dirname(script_path)


def slugify_for_api_table(text):
    text = text.split("{{")[0].strip()
    text = text.replace("_", "-")
    text = re.sub(r'[^a-zA-Z0-9\-]', '', text)
    return text.lower()

def get_method_name(line):
    if 'CodeGroup' in line and "label" in line:
        return line.split('label="')[1].split('"')[0]
    elif line.startswith("## ") and "label" in line:
        return line.split('label')[1].split(':')[1].split(',')[0].replace("'", "").replace('"', "").strip()
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

def gen_api_methods_table():
    slugs = json.loads(open(f'{root_path}/filepathSlugs.json', 'r').read())
    komodefi_files = glob.glob(f'{root_path}/src/pages/komodo-defi-framework/**/index.mdx', recursive = True)
    methods_dict = {
        "legacy": [],
        "v20": [],
        "v20-dev": []
    }
    methods_list = []
    for file in komodefi_files:
            
        if ignore_file(file):
            continue
        file_methods_list = []
        relative_path = file.replace(f'{root_path}/', '')
        file_slugs = slugs[file.replace(f'{root_path}/', '')]
        with open(file, 'r') as f:

            for line in f.readlines():
                doc_path = file.replace(f'{root_path}/src/pages', '').replace('/index.mdx', '')
                doc_split = doc_path.split('/')
                if len(doc_split) > 3:
                    section = doc_split[3]
                    if section in methods_dict:
                        method = get_method_name(line)
                        method_slug = slugify_for_api_table(method)
                        if method_slug not in file_slugs:
                            method_slug = file_slugs[0]
                        methods_dict[section].append({
                            "link": f"[{method}]({doc_path}/#{method_slug})",
                            "method": method,
                            "doc_url": doc_path
                        })
                        file_methods_list.append(method)
                        

        # print(f"###### Methods in {file}: {file_methods_list}")
        if len(file_methods_list) > 0:
            methods_list.extend(file_methods_list)
        else:
            sys.exit(f"###### No methods found in {file}!")
    methods_list = sorted(list(set(methods_list)))

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
