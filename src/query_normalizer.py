import unicodedata
import re

def normalize_query(query: str) -> str:
    """
    Normalizes the user search query to ensure consistent hit rates.
    
    Normalization steps:
    1. Unicode Normalization (NFKC): Unifies half-width/full-width characters.
    2. Lowercasing: Ensures case-insensitive search.
    3. Whitespace Normalization: Trims and replaces multiple spaces with single space.
    
    Args:
        query (str): The raw user input.
        
    Returns:
        str: The normalized query string.
    """
    if not query:
        return ""
        
    # 1. Unicode Normalization (NFKC)
    # Converts full-width chars (e.g., 'Ａ') to half-width ('A') and handles composed chars.
    normalized = unicodedata.normalize('NFKC', query)
    
    # 2. Case folding
    normalized = normalized.lower()
    
    # 3. Whitespace cleanup
    # Replace any sequence of whitespace with a single space and trim ends.
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized
