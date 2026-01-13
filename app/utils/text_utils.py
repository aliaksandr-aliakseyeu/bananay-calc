"""Text utilities for normalization and processing."""
import re


def normalize_name(name: str) -> str:
    """
    Normalize name for search.

    Rules:
    - Convert to lowercase
    - Replace ё with е
    - Remove all special characters (keep only letters, numbers, spaces)
    - Collapse multiple spaces into one
    - Trim spaces

    Args:
        name: Name string to normalize

    Returns:
        Normalized name string
    """
    normalized = name.lower()
    normalized = normalized.replace('ё', 'е')
    normalized = re.sub(r'[^а-яa-z0-9\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()
