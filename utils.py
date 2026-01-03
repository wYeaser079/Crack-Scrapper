"""Utility functions for the pothole image scraper."""

import hashlib
import re
from urllib.parse import urlparse


def compute_hash(content: bytes) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content).hexdigest()


def sanitize_filename(url: str, max_length: int = 100) -> str:
    """
    Sanitize a URL to create a safe filename component.

    Args:
        url: The source URL to sanitize
        max_length: Maximum length of the sanitized string

    Returns:
        A filesystem-safe string derived from the URL
    """
    # Remove protocol
    sanitized = re.sub(r'^https?://', '', url)

    # Replace unsafe characters with hyphens
    sanitized = re.sub(r'[/:?&=%#\\\s]+', '-', sanitized)

    # Remove any remaining non-alphanumeric characters except hyphen and dot
    sanitized = re.sub(r'[^a-zA-Z0-9\-.]', '', sanitized)

    # Collapse multiple hyphens
    sanitized = re.sub(r'-+', '-', sanitized)

    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('-')

    return sanitized


def get_file_extension(url: str, content_type: str = None) -> str:
    """
    Determine file extension from URL or content type.

    Args:
        url: The image URL
        content_type: The Content-Type header value (optional)

    Returns:
        File extension including the dot (e.g., '.jpg')
    """
    # Try to get extension from content type first
    if content_type:
        content_type_map = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/svg+xml': '.svg',
        }
        # Extract base content type (remove parameters like charset)
        base_type = content_type.split(';')[0].strip().lower()
        if base_type in content_type_map:
            return content_type_map[base_type]

    # Fall back to URL parsing
    parsed = urlparse(url)
    path = parsed.path.lower()

    # Common image extensions
    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg']:
        if path.endswith(ext):
            return '.jpg' if ext == '.jpeg' else ext

    # Default to .jpg if unknown
    return '.jpg'


def read_queries_from_file(filepath: str) -> list[str]:
    """
    Read search queries from a text file.

    Args:
        filepath: Path to the queries file

    Returns:
        List of query strings
    """
    queries = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                queries.append(line)

    return queries
