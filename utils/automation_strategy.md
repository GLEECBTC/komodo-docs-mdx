Process:

- Get KDF Repo Methods names list (`utils/py/scan_kdf_repository.py` outputs to `data/kdf_repo_rpc_methods.json`)
- Update method map json file (outputs to `data/method_map.json`)
- compare `data/kdf_repo_rpc_methods.json` and `data/method_map.json`
    - if there are methods in `kdf_repo_rpc_methods.json` that are not in `method_map.json`, log this to console and the json file `missing_methods.json`
    - if there are methods in `method_map.json` that are not in `kdf_repo_rpc_methods.json`, log this to console and the json file `extra_methods.json`


# Scan repository for latest methods
python kdf_tools.py scan --branch dev --force-refresh

# Compare repository with documentation
python kdf_tools.py compare --branch dev

# Generate unified mapping (extracts JSON and maps methods)
python kdf_tools.py map

# Generate Postman collections
python kdf_tools.py postman --versions all

# Convert to OpenAPI specifications
python kdf_tools.py convert --version all
