from typing import Dict

def sort_version_method_counts(version_counts: Dict[str, int]) -> Dict[str, int]:
    """
    Sorts a dictionary of version method counts alphabetically by version 
    and ensures the 'all' key is present and calculated.

    Args:
        version_counts: A dictionary where keys are version strings and 
                        values are method counts.

    Returns:
        A new dictionary with sorted version counts and a calculated 'all' key.
    """
    if 'all' not in version_counts:
        version_counts['all'] = sum(v for k, v in version_counts.items() if k != 'all')
    
    return dict(sorted(version_counts.items())) 

CONFIRMED_EMPTY_PARAMS_METHODS = {
    "v1": [
        "stop_simple_market_maker_bot",
        "get_enabled_coins",
        "get_public_key",
        "get_public_key_hash",
        "stop_version_stat_collection"
    ],
    "v2": [
    ]
}

def is_confirmed_empty_params_method(method_name: str, version: str) -> bool:
    """
    Checks if a method is in the list of confirmed empty params methods.
    """
    if version == "v1":
        return method_name in CONFIRMED_EMPTY_PARAMS_METHODS["v1"]
    elif version == "v2":
        return method_name in CONFIRMED_EMPTY_PARAMS_METHODS["v2"]
    return False