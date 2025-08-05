import json
import os

def generate_mdx_content(errors_map):
    content = []
    content.append('export const title = "Komodo DeFi Framework RPC Errors";')
    content.append('export const description = "A comprehensive list of possible RPC errors in Komodo DeFi Framework.";')
    content.append('')
    content.append('# KDF RPC Errors')
    content.append('')
    content.append('This document lists all possible error types that can be returned by the Komodo DeFi Framework API.')
    content.append('')

    for error_enum, variants in sorted(errors_map.items()):
        content.append(f'## {error_enum}')
        content.append('')
        content.append('| ErrorType              | Description                                                                  |')
        content.append('| ---------------------- | ---------------------------------------------------------------------------- |')
        for variant, description in sorted(variants.items()):
            content.append(f'| {variant} | {description} |')
        content.append('')

    return '\n'.join(content)

def main():
    errors_map_path = 'kdf_errors_map.json'
    if not os.path.exists(errors_map_path):
        print(f"Error: {errors_map_path} not found.")
        return

    with open(errors_map_path, 'r') as f:
        errors_map = json.load(f)

    mdx_content = generate_mdx_content(errors_map)

    output_dir = 'src/pages/komodo-defi-framework/common-structures/error-types'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_path = os.path.join(output_dir, 'index.mdx')

    with open(output_path, 'w') as f:
        f.write(mdx_content)

    print(f"Error documentation generated at {output_path}")

if __name__ == "__main__":
    main() 