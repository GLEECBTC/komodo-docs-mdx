# Adding new methods

#### Add table data for requests, responses, or errors in `src/data/tables/v2` to populate tables in the documentation.

The filename should match the existing folder structure in `src/pages/komodo-defi-framework`

For example, for `src/pages/komodo-defi-framework/api/v20/utils` place table parameters descriptions in `src/data/tables/v2/utils.json`, as below:

```json
{
  "AddNodeToVersionStatErrors": {
    "data": [
      {
        "parameter": "DatabaseError",
        "type": "string",
        "required": false,
        "description": "Database constraint error occurred."
      },
      {
        "parameter": "PeerIdParseError",
        "type": "string",
        "required": false,
        "description": "The provided peer ID format is invalid."
      }
    ]
  },
  "AddNodeToVersionStatRequest": {
    "data": [
      {
        "parameter": "name",
        "type": "string",
        "required": true,
        "description": "The name assigned to the node"
      },
      {
        "parameter": "address",
        "type": "string",
        "required": true,
        "description": "The IP address of the node"
      },
      {
        "parameter": "peer_id",
        "type": "string",
        "required": true,
        "description": "The node's unique Peer ID"
      }
    ]
  },
  "AddNodeToVersionStatResponse": {
    "data": [
      {
        "parameter": "result",
        "type": "string",
        "required": true,
        "description": "The outcome of the request."
      }
    ]
  }
}
```


####  Add request bodies in `src/data/requests/kdf`

The filename should match the existing folder structure in `src/pages/komodo-defi-framework`

For example, for `src/pages/komodo-defi-framework/api/v20/utils` place sample request bodies in `src/data/requests/kdf/v2/utils.json`, as below:

```json
  {
    "AddNodeToVersionStat": {
      "method": "add_node_to_version_stat",
      "mmrpc": "2.0",
      "params": {
        "address": "168.119.236.241",
        "name": "seed1",
        "peer_id": "12D3KooWEsuiKcQaBaKEzuMtT6uFjs89P1E8MK3wGRZbeuCbCw6P"
      },
      "userpass": "RPC_UserP@SSW0RD"
    }
  }
```

Each object in the json file should have a unique name, with a common prefix for variations of the same method.


#### Add methods to the kdf_methods_v2.json or kdf_methods_legacy.json files

This file links the method name to the request examples and parameters table data. 
It also includes optional metadata fields to indicate environment and wallet type requirements, prerequisite methods, and response timeout.
The `tags` field is used to categorize the method for reference.

```json
{
  "enable_eth_with_tokens": {
    "examples": {
      "EnableEthWithTokensGasStation": "Enable Eth With Tokens Gas Station",
      "EnableEthWithTokensMaticBalancesFalse": "Enable Eth With Tokens Matic Balances False",
      "EnableEthWithTokensMaticNft": "Enable Eth With Tokens Matic Nft",
      "EnableEthWithTokensWalletConnect": "Enable Eth With Tokens Wallet Connect"
    },
    "prerequisites": [],
    "requirements": {
      "environments": [
        "native",
        "wasm"
      ],
      "wallet_types": [
        "iguana"
      ]
    },
    "table": "EnableEthWithTokensArguments",
    "tags": [
      "v2"
    ],
    "timeout": 300
  }
}
```


## Reporting

#### Missing methods

If a method is missing from the `kdf_methods_v2.json`/`kdf_methods_legacy.json` files, it will be reported as missing in split files:
`postman/generated/reports/missing_methods_v2.json` and `postman/generated/reports/missing_methods_legacy.json`.

#### Missing requests

Any request key detected in the param tables or responses json files, but not seen in the request json files, will be reported as missing in
`postman/generated/reports/missing_requests_v2.json` and `postman/generated/reports/missing_requests_legacy.json`.

```json
{
  "v2": [
    "LegacyElectrumBch",
    "LegacyElectrumKmd",
    "LegacyElectrumQtum",
    "LegacyEnableBnb",
    "LegacyEnableMatic",
    "TaskEnableZCoinStatusBasic"
  ]
}
```

#### Missing responses

Any response key detected in the param table or request json files, but not seen in the responses json files, will be reported as missing in
`postman/generated/reports/missing_responses_v2.json` and `postman/generated/reports/missing_responses_legacy.json` as a simple list for each method.

```json
{
  "add_node_to_version_stat": [
    "AddNodeToVersionStat"
  ],
  "enable_eth_with_tokens": [
    "EnableEthWithTokensMaticNft"
  ]
}
```

#### Missing tables

Any method detected in the `kdf_methods_v2.json`/`kdf_methods_legacy.json` files, but not seen in the param tables json files, will be reported as missing in
`postman/generated/reports/missing_tables_v2.json` and `postman/generated/reports/missing_tables_legacy.json` as a simple list.

```json
[
  "add_node_to_version_stat"
]
```

#### Untranslated keys

In `kdf_methods_v2.json`/`kdf_methods_legacy.json`, every request key is given a human-readable name in the `examples` field.
If a request key is missing from the `examples` field, it will be reported as untranslated in `postman/generated/reports/untranslated_keys.json` as a simple list.

```json
  "task::enable_z_coin::init": {
    "examples": {
      "TaskEnableZCoinInit": "Initialize Z-coin",
      "TaskEnableZCoinInitBasic": "Initialize Z-coin with basic params",
      "TaskEnableZCoinInitWithSyncParams": "Initialize Z-coin with sync params"
    }
    ...
  }
```

#### KDF response delays

In `postman/generated/reports/kdf_response_delays.json`, we track the response `delay` and `status code` for each method and request key across different environments. This is useful for identifying performance characteristics and optimization opportunities, or to compare performance between different environments.

```json
    "enable_tendermint_with_assets": {
      "EnableTendermintWithAssetsBalancesFalse": {
        "native-hd": {
          "delay": 0.753,
          "status_code": 200
        },
        "native-nonhd": {
          "delay": 0.752,
          "status_code": 200
        }
      },
      "EnableTendermintWithAssetsBalancesTrue": {
        "native-hd": {
          "delay": 2.25,
          "status_code": 200
        },
        "native-nonhd": {
          "delay": 2.262,
          "status_code": 200
        }
      }
    }
```


#### Inconsistent responses

In `postman/generated/reports/inconsistent_responses.json` the responses from each environment is compared to the native-hd response to detect structural differences or success/failure patterns. This helps identify where more than one response structure needs to be documented, or highlight methods which have compatibility limited to a subset of environments or wallet types.

```json
"enable_eth_with_tokens": {
    "EnableEthWithTokensGasStation": {
    "instances": {
        "native-hd": {
            "id": null,
            "mmrpc": "2.0",
            "result": {
                "current_block": 23367217,
                "nfts_infos": {},
                "ticker": "ETH",
                "wallet_balance": {
                "accounts": [
                    ...
                ],
                "wallet_type": "HD"
                }
            }
        },
        "native-nonhd": {
            "id": null,
            "mmrpc": "2.0",
            "result": {
                "current_block": 23367228,
                "erc20_addresses_infos": {
                ...
                }
                },
                "eth_addresses_infos": {
                ...
                },
                "nfts_infos": {}
            }
        }
    }
}
```