"""
String Utilities

Consolidated string manipulation and method name conversion functions.
These utilities handle method name normalization, formatting, and path generation.
"""

import re
from typing import Tuple, Optional, List, Dict
from functools import lru_cache


# =============================================================================
# METHOD NAME CONVERSIONS
# =============================================================================

@lru_cache(maxsize=512)
def convert_dir_to_method_name(directory_name: str) -> str:
    """
    Convert directory/folder name to canonical method name format.
    
    Converts folder format (hyphen-separated) to canonical format (:: separated).
    Underscores within method name parts are preserved.
    
    Examples:
    - task-enable_utxo-init -> task::enable_utxo::init
    - lightning-channels-close_channel -> lightning::channels::close_channel
    
    Args:
        directory_name: Directory/folder name (e.g., "task-enable_utxo-init")
        
    Returns:
        Canonical method name (e.g., "task::enable_utxo::init")
    """
    if not directory_name:
        return ""
    
    # Simply replace hyphens with double colons.
    # This is the designated separator for file/folder names that corresponds to '::'.
    return directory_name.replace("-", "::")


@lru_cache(maxsize=512)
def convert_method_to_dir_name(method_name: str) -> str:
    """
    Convert canonical method name to directory/folder name format.
    
    Converts canonical format (:: separated) to folder format (hyphen-separated).
    Underscores within method name parts are preserved.
    
    Examples:
    - task::enable_utxo::init -> task-enable_utxo-init
    - lightning::channels::open_channel -> lightning-channels-open_channel
    
    Args:
        method_name: Canonical method name (e.g., "task::enable_utxo::init")
        
    Returns:
        Directory/folder name (e.g., "task-enable_utxo-init")
    """
    if not method_name:
        return ""
    
    # Simply replace '::' with '-'.
    # Hyphens are used in filesystem paths to represent the '::' separator from canonical names.
    return method_name.replace("::", "-")


@lru_cache(maxsize=512)
def convert_canonical_to_slug(method_name: str) -> str:
    """
    Convert canonical method name to URL slug format.
    
    Converts canonical format to slug format:
    - task::enable_utxo::init → task-enable-utxo-init
    - lightning::channels::close_channel → lightning-channels-close-channel
    - experimental::staking::delegate → experimental-staking-delegate
    
    Args:
        method_name: Canonical method name (e.g., "task::enable_utxo::init")
        
    Returns:
        URL slug (e.g., "task-enable-utxo-init")
    """
    if not method_name:
        return ""
    
    # Replace :: with - and _ with -
    return method_name.replace("::", "-").replace("_", "-")


@lru_cache(maxsize=512)
def convert_slug_to_canonical(slug: str) -> str:
    """
    Convert URL slug to canonical method name format.
    
    Note: This conversion is lossy because we can't reliably distinguish
    between hyphens that should become :: vs those that should become _.
    This function makes best-effort guesses based on common patterns.
    
    Args:
        slug: URL slug (e.g., "task-enable-utxo-init")
        
    Returns:
        Canonical method name (e.g., "task::enable_utxo::init")
    """
    if not slug:
        return ""
    
    # Known patterns where hyphens should become underscores
    underscore_patterns = [
        # Enable patterns - specifically handle enable-<coin> patterns
        r'enable-utxo',     # enable-utxo → enable_utxo
        r'enable-bch',      # enable-bch → enable_bch
        r'enable-eth',      # enable-eth → enable_eth
        r'enable-qtum',     # enable-qtum → enable_qtum
        r'enable-z-coin',   # enable-z-coin → enable_z_coin
        r'enable-coin',     # enable-coin → enable_coin
        # Other common method name patterns
        r'account-balance',   # account-balance → account_balance
        r'new-address',       # new-address → new_address
        r'z-coin',           # z-coin → z_coin
        r'nft-([a-z]+)',     # nft-list → nft_list
        r'close-channel',    # close-channel → close_channel
        r'send-payment',     # send-payment → send_payment
        r'trusted-node',     # trusted-node → trusted_node
        r'claimable-balances', # claimable-balances → claimable_balances
        r'channel-details',   # channel-details → channel_details
        r'payment-details',   # payment-details → payment_details
    ]
    
    result = slug
    
    # Apply underscore patterns
    for pattern in underscore_patterns:
        result = re.sub(pattern, lambda m: m.group(0).replace('-', '_'), result)
    
    # Convert remaining hyphens to double colons
    result = result.replace("-", "::")
    
    return result


@lru_cache(maxsize=512)
def convert_folder_to_slug(folder_name: str) -> str:
    """
    Convert folder format to URL slug format.
    
    Args:
        folder_name: Folder name (e.g., "task-enable_utxo-init")
        
    Returns:
        URL slug (e.g., "task-enable-utxo-init")
    """
    if not folder_name:
        return ""
    
    # Replace underscores with hyphens
    return folder_name.replace("_", "-")


@lru_cache(maxsize=512)
def convert_slug_to_folder(slug: str) -> str:
    """
    Convert URL slug to folder format.
    
    Note: This conversion is lossy and makes best-effort guesses.
    
    Args:
        slug: URL slug (e.g., "task-enable-utxo-init")
        
    Returns:
        Folder name (e.g., "task-enable_utxo-init")
    """
    if not slug:
        return ""
    
    # Known patterns where hyphens should become underscores in folder names
    underscore_patterns = [
        # Enable patterns - preserve underscores in method names
        r'enable-utxo',     # enable-utxo → enable_utxo
        r'enable-bch',      # enable-bch → enable_bch
        r'enable-eth',      # enable-eth → enable_eth
        r'enable-qtum',     # enable-qtum → enable_qtum
        r'enable-z-coin',   # enable-z-coin → enable_z_coin
        r'enable-coin',     # enable-coin → enable_coin
        # Other common method name patterns
        r'account-balance',   # account-balance → account_balance
        r'new-address',       # new-address → new_address
        r'z-coin',           # z-coin → z_coin
        r'nft-([a-z]+)',     # nft-list → nft_list
        r'close-channel',    # close-channel → close_channel
        r'send-payment',     # send-payment → send_payment
        r'trusted-node',     # trusted-node → trusted_node
        r'claimable-balances', # claimable-balances → claimable_balances
        r'channel-details',   # channel-details → channel_details
        r'payment-details',   # payment-details → payment_details
    ]
    
    result = slug
    
    # Apply underscore patterns
    for pattern in underscore_patterns:
        result = re.sub(pattern, lambda m: m.group(0).replace('-', '_'), result)
    
    return result


def format_method_name_for_display(method_name: str) -> str:
    """
    Format method name for human-readable display.
    
    Args:
        method_name: Raw method name
        
    Returns:
        Formatted method name for display
    """
    # Split on :: and capitalize each part
    parts = method_name.split("::")
    formatted_parts = []
    
    for part in parts:
        # Handle underscores
        if "_" in part:
            words = part.split("_")
            formatted_part = " ".join(word.capitalize() for word in words)
        else:
            formatted_part = part.capitalize()
        
        formatted_parts.append(formatted_part)
    
    return " → ".join(formatted_parts)


# =============================================================================
# NORMALIZATION FUNCTIONS (CONSOLIDATED)
# =============================================================================

@lru_cache(maxsize=256)
def normalize_method_name(method_name: str) -> str:
    """
    Normalize method name to consistent format for comparison.
    
    SIMPLIFIED: Now that the scanner returns proper full method names with correct prefixes,
    we can greatly simplify this normalization function.
    
    Args:
        method_name: Method name in any format
        
    Returns:
        Normalized method name with :: separators
    """
    if not method_name:
        return ""
    
    # Remove extra whitespace and convert to lowercase
    normalized = method_name.strip().lower()
    
    # Handle different separator conventions
    # Documentation uses: task-enable_bch-cancel (filesystem format)
    # Repository uses: task::enable_bch::cancel (canonical format)
    # Convert filesystem format to canonical format
    normalized = normalized.replace("-", "::")
    
    # Clean up any multiple colons that might result from the conversion
    while "::::" in normalized:
        normalized = normalized.replace("::::", "::")
    
    # Clean up any leading/trailing colons
    normalized = normalized.strip(":")
    
    # Handle specific KDF method naming patterns
    normalized = _handle_kdf_method_patterns(normalized)
    
    return normalized


def _handle_kdf_method_patterns(method_name: str) -> str:
    """
    Handle specific KDF method naming patterns.
    
    SIMPLIFIED: Now that we have proper method names from the scanner,
    we only need to handle a few specific edge cases.
    
    Args:
        method_name: Pre-normalized method name
        
    Returns:
        Method name with any necessary pattern adjustments
    """
    # Handle a few specific method name variations that may still exist
    method_mappings = {
    }
    
    # Apply mappings for specific edge cases only
    return method_mappings.get(method_name, method_name)


@lru_cache(maxsize=128)
def clean_method_name(method_name: str) -> str:
    """
    Clean and normalize method name by removing problematic characters.
    
    Args:
        method_name: Raw method name
        
    Returns:
        Cleaned method name
    """
    if not method_name:
        return ""
    
    # Remove leading/trailing whitespace
    cleaned = method_name.strip()
    
    # Remove common problematic prefixes
    prefixes_to_remove = [
        "komodo defi framework method: ",
        "kdf method: ",
        "method: ",
        "api method: "
    ]
    
    cleaned_lower = cleaned.lower()
    for prefix in prefixes_to_remove:
        if cleaned_lower.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    
    # Remove extra whitespace and normalize separators
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Convert common separators to double colon
    cleaned = cleaned.replace(' → ', '::')
    cleaned = cleaned.replace(' -> ', '::')
    cleaned = cleaned.replace(' | ', '::')
    
    # Handle special characters
    cleaned = cleaned.replace('"', '').replace("'", "")
    cleaned = cleaned.replace('(', '').replace(')', '')
    cleaned = cleaned.replace('[', '').replace(']', '')
    
    return cleaned.strip()


@lru_cache(maxsize=128)
def normalize_method_name_variations(method_name: str) -> tuple:
    """
    Generate normalized variations of a method name for matching.
    
    SIMPLIFIED: Now that we have proper method names from the scanner,
    we only need basic format variations.
    
    Args:
        method_name: The method name to normalize
        
    Returns:
        Tuple of normalized variations
    """
    if not method_name:
        return tuple()
    
    variations = {method_name}  # Always include original
    
    # Clean the method name
    cleaned = clean_method_name(method_name)
    if cleaned and cleaned != method_name:
        variations.add(cleaned)
    
    # Generate basic format variations (:: vs -)
    variations.update(_generate_format_variations(cleaned))
    
    return tuple(variations)


def _generate_format_variations(method_name: str) -> set:
    """Generate format variations (:: vs -)."""
    variations = set()
    
    # Convert :: to -
    if '::' in method_name:
        dash_version = method_name.replace('::', '-')
        variations.add(dash_version)
    
    # Convert - to ::
    elif '-' in method_name and not method_name.startswith(('http-', 'https-')):
        colon_version = method_name.replace('-', '::')
        variations.add(colon_version)
    
    return variations


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_method_parts(method_name: str) -> List[str]:
    """
    Extract method name parts split by double colon.
    
    Args:
        method_name: Method name with :: separators
        
    Returns:
        List of method parts
    """
    if not method_name:
        return []
    
    return [part.strip() for part in method_name.split('::') if part.strip()]


def join_method_parts(parts: List[str]) -> str:
    """
    Join method parts with double colon separator.
    
    Args:
        parts: List of method parts
        
    Returns:
        Joined method name
    """
    return '::'.join(part.strip() for part in parts if part.strip())


def extract_base_method(method_name: str) -> str:
    """Extract the base method name (without operation suffix)."""
    if not method_name:
        return ""
    
    # Try structured patterns first
    patterns = [
        re.compile(r'^task[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
        re.compile(r'^stream[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
        re.compile(r'^lightning[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE)
    ]
    
    pattern_names = ['task', 'stream', 'lightning']
    
    for i, pattern in enumerate(patterns):
        match = pattern.match(method_name)
        if match and match.group(1):
            return f"{pattern_names[i]}::{match.group(1)}"
    
    # Fallback to simple splitting
    parts = re.split(r'[::-]', method_name)
    if len(parts) > 2:
        return '::'.join(parts[:-1])
    
    return method_name


def extract_operation(method_name: str) -> Optional[str]:
    """Extract the operation suffix from a method name."""
    if not method_name:
        return None
    
    # Try structured patterns first
    patterns = [
        re.compile(r'^task[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
        re.compile(r'^stream[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
        re.compile(r'^lightning[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE)
    ]
    
    for pattern in patterns:
        match = pattern.match(method_name)
        if match and len(match.groups()) > 1 and match.group(2):
            return match.group(2)
    
    # Fallback to simple splitting
    parts = re.split(r'[::-]', method_name)
    if len(parts) > 2:
        return parts[-1]
    
    return None


# =============================================================================
# PATH AND CATEGORY FUNCTIONS
# =============================================================================

def generate_api_path(method_name: str, version: str = "v2") -> str:
    """
    Generate API path from method name.
    
    Args:
        method_name: Method name
        version: API version
        
    Returns:
        API path
    """
    return f"/{version}/{method_name.replace('::', '/')}"


@lru_cache(maxsize=256)
def extract_category_from_method(method_name: str) -> Tuple[str, Optional[str]]:
    """
    Extract category and optional subcategory from method name.
    
    Args:
        method_name: The method name to analyze
        
    Returns:
        Tuple of (category, subcategory)
    """
    # Handle task methods
    if method_name.startswith("task::"):
        parts = method_name.split("::")
        if len(parts) >= 3:
            operation = parts[-1]  # init, status, cancel, user_action
            base_task = "::".join(parts[1:-1])  # enable_eth, create_new_account, etc.
            
            if base_task.startswith("enable_"):
                return ("coin_activation", "task_managed")
            elif base_task.find('account') != -1:
                return ("wallet", "task_managed")
            elif base_task.find('wallet') != -1:
                return ("wallet", "task_managed")
            else:
                return ("task_managed", base_task.replace("_", "-"))
        elif len(parts) == 2:
            base_task = parts[1]
            if base_task.startswith("enable_"):
                return ("coin_activation", "task_managed")
            elif base_task.find('account') != -1:
                return ("wallet", "task_managed")
            elif base_task.find('wallet') != -1:
                return ("wallet", "task_managed")
            else:
                return ("task_managed", base_task.replace("_", "-"))
    
    # Handle lightning methods
    elif method_name.find("lightning") != -1:
        parts = method_name.split("::")
        if len(parts) >= 3:
            subcategory = parts[1]  # channels, nodes, payments
            return ("lightning", subcategory)
        return ("lightning", None)
    
    # Handle streaming methods
    elif method_name.startswith(("stream::", "streaming::")):
        return ("streaming", None)
    
    # Handle wallet methods
    elif method_name.find("wallet") != -1:
        parts = method_name.split("::")
        if len(parts) >= 3:
            subcategory = parts[1]
            return ("wallet", subcategory)
        return ("wallet", None)
    
    # Handle other common patterns
    elif any(keyword in method_name for keyword in ["swap", "order", "trade", "buy", "sell", "setprice"]):
        return ("trading", None)
    elif any(keyword in method_name for keyword in ["nft", "non_fungible"]):
        return ("nft", None)
    elif "1inch" in method_name:
        return ("1inch", None)
    elif "experimental" in method_name:
        return ("experimental", None)
    else:
        return ("misc", None)


# =============================================================================
# MDX AND YAML EXTRACTION FUNCTIONS (CONSOLIDATED)
# =============================================================================

def extract_method_name_from_mdx_content(content: str) -> Optional[str]:
    """
    Extract method name from MDX content using standardized pattern.
    
    This consolidates the duplicate implementations across the codebase.
    
    Args:
        content: MDX file content
        
    Returns:
        Method name if found, None otherwise
    """
    # Look for method heading pattern (##\s+method_name\s*{{)
    # Updated to handle escaped underscores (\_) in MDX headings
    method_pattern = r'##\s+([a-zA-Z0-9_\\:.-]+)\s*\{\{'
    match = re.search(method_pattern, content)
    
    if match:
        method_name = match.group(1).strip()
        # Convert escaped underscores back to regular underscores
        method_name = method_name.replace('\\_', '_')
        return method_name
    
    return None


def is_overview_page(content: str) -> bool:
    """
    Check if the MDX content suggests it's an overview page by looking for a 'tag: overview'.
    """
    # Pattern to find ## headings with a 'tag: overview'
    overview_pattern = r'##\s+.*\{\{.*tag\s*:\s*["\']overview["\'].*\}\}'
    
    # Search for the pattern in the content
    if re.search(overview_pattern, content, re.IGNORECASE):
        return True
    
    return False


def extract_method_name_from_yaml_filename(filename: str, version: str) -> Optional[str]:
    """
    Extract method name from YAML filename using standardized conversion.
    
    This consolidates the duplicate implementations across the codebase.
    
    Args:
        filename: YAML filename
        version: API version (v1 or v2)
        
    Returns:
        Method name if valid, None otherwise
    """
    # Remove extension
    return filename.replace('.yaml', '').replace('-', '::')


def extract_methods_from_mdx_codeblocks(content: str, is_legacy: bool = False) -> Tuple[List[str], List[str]]:
    """
    Extract method names from MDX CodeGroup blocks.
    
    This consolidates the duplicate implementations across the codebase.
    
    Args:
        content: MDX file content
        is_legacy: Whether this is a legacy API file
        
    Returns:
        Tuple of (v1_methods, v2_methods)
    """
    v1_methods = []
    v2_methods = []
    
    # Find all CodeGroup blocks
    codegroups = re.findall(r'<CodeGroup[\s\S]*?>([\s\S]*?)</CodeGroup>', content, re.MULTILINE)
    
    for block in codegroups:
        # Extract code blocks from within CodeGroup
        code_blocks = re.findall(r'```[a-zA-Z]*\n([\s\S]*?)```', block)
        
        for code in code_blocks:
            # Look for method field in JSON
            method_match = re.search(r'"method"\s*:\s*"([a-zA-Z0-9_:.-]+)"', code)
            if method_match:
                method = method_match.group(1)
                
                if is_legacy:
                    v1_methods.append(method)
                elif '"mmrpc": "2.0"' in code:
                    v2_methods.append(method)
                else:
                    v1_methods.append(method)
    
    return sorted(list(set(v1_methods))), sorted(list(set(v2_methods)))


def extract_methods_from_mdx_headings(content: str) -> List[str]:
    """
    Extract method names from MDX ## headings, excluding overview and structures pages.
    
    This function looks for ## headings with method names and filters out pages
    tagged as 'overview' or 'structures' since these are not individual API methods.
    
    Args:
        content: MDX file content
        
    Returns:
        List of method names found in headings
    """
    methods = []
    
    # Skip overview and structures pages entirely
    if is_overview_page(content):
        return []
    
    # Pattern to find ## headings with labels and tags
    heading_pattern = r'##\s+([a-zA-Z0-9_:.-]+)\s*\{\{[^}]*label\s*:\s*["\']([a-zA-Z0-9_:.-]+)["\'][^}]*tag\s*:\s*["\']([a-zA-Z0-9_-]+)["\'][^}]*\}\}'
    
    matches = re.findall(heading_pattern, content)
    
    for heading_text, label_method, tag in matches:
        # Skip overview and structures tags
        if tag.lower() in ['overview', 'structures']:
            continue
            
        # Use the label method name as it's more canonical
        method_name = label_method.strip()
        
        # Validate method name format
        if method_name and not method_name.isspace():
            methods.append(method_name)
    
    return sorted(list(set(methods)))


# =============================================================================
# TEXT FORMATTING FUNCTIONS
# =============================================================================

def camel_case_to_snake_case(text: str) -> str:
    """
    Convert camelCase text to snake_case.
    
    Args:
        text: CamelCase text
        
    Returns:
        snake_case text
    """
    # Insert underscore before uppercase letters
    snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', text)
    return snake_case.lower()


def snake_case_to_camel_case(text: str, capitalize_first: bool = False) -> str:
    """
    Convert snake_case text to camelCase.
    
    Args:
        text: snake_case text
        capitalize_first: Whether to capitalize the first letter
        
    Returns:
        camelCase text
    """
    components = text.split('_')
    if capitalize_first:
        return ''.join(word.capitalize() for word in components)
    else:
        return components[0] + ''.join(word.capitalize() for word in components[1:])


def title_case_with_exceptions(text: str, exceptions: List[str] = None) -> str:
    """
    Convert text to title case with exceptions for specific words.
    
    Args:
        text: Text to convert
        exceptions: List of words to keep lowercase
        
    Returns:
        Title-cased text
    """
    if exceptions is None:
        exceptions = ['and', 'or', 'but', 'for', 'nor', 'on', 'at', 'to', 'from', 'by', 'of', 'in']
    
    words = text.split()
    title_words = []
    
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in exceptions:
            title_words.append(word.capitalize())
        else:
            title_words.append(word.lower())
    
    return ' '.join(title_words)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


# =============================================================================
# MATCHING FUNCTIONS
# =============================================================================

def find_best_match(method_name: str, mapping_dict: Dict[str, str]) -> Optional[str]:
    """
    Find the best matching key in a mapping dictionary for a given method name.
    Uses fuzzy matching with Levenshtein distance.
    
    Note: Removed @lru_cache decorator because mapping_dict is unhashable.
    
    Args:
        method_name: Method name to find match for
        mapping_dict: Dictionary to search in
        
    Returns:
        Best matching key or None if no good match found
    """
    if not method_name or not mapping_dict:
        return None
    
    # First try exact match
    if method_name in mapping_dict:
        return method_name
    
    # Try normalized variations
    variations = normalize_method_name_variations(method_name)
    for variation in variations:
        if variation in mapping_dict:
            return variation
    
    # Try fuzzy matching
    return _fuzzy_match(method_name, mapping_dict)


def _fuzzy_match(method_name: str, mapping_dict: Dict[str, str]) -> Optional[str]:
    """Perform fuzzy matching using edit distance."""
    if not method_name:
        return None
    
    best_match = None
    best_score = float('inf')
    threshold = len(method_name) // 3  # Allow up to 1/3 character differences
    
    for key in mapping_dict.keys():
        if abs(len(key) - len(method_name)) > threshold:
            continue
        
        score = _levenshtein_distance(method_name.lower(), key.lower())
        if score < best_score and score <= threshold:
            best_score = score
            best_match = key
    
    return best_match


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def get_file_content_with_frontmatter(file_path: str) -> str:
    """
    Reads the entire content of a file, including frontmatter.
    
    Args:
        file_path (str): The path to the file.
        
    Returns:
        str: The content of the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        # Assuming a logger is available or just print
        print(f"Error reading file {file_path}: {e}")
        return "" 