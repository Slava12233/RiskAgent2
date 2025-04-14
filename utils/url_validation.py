"""
URL validation and processing utilities.

This module provides functions for validating and processing URLs
to ensure they are well-formed and safe to crawl.
"""

import re
from typing import Optional, Tuple, List
from urllib.parse import urlparse, urljoin, urlunparse


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.
    
    Args:
        url: The URL to validate
        
    Returns:
        bool: True if the URL is valid, False otherwise
    """
    if not url:
        return False
    
    # Check if URL has a scheme
    if not url.startswith(('http://', 'https://')):
        return False
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except:
        return False


def normalize_url(url: str) -> str:
    """
    Normalize a URL by ensuring it has a scheme and handling special cases.
    
    Args:
        url: The URL to normalize
        
    Returns:
        str: The normalized URL
    """
    if not url:
        return url
    
    # Add https:// if no scheme is provided
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Reconstruct the URL with normalized components
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path if parsed.path else '/',
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))
    
    return normalized


def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: The URL to extract the domain from
        
    Returns:
        str: The domain name
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        # Return the original URL if it can't be parsed
        return url


def is_same_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs belong to the same domain.
    
    Args:
        url1: The first URL
        url2: The second URL
        
    Returns:
        bool: True if both URLs belong to the same domain
    """
    domain1 = extract_domain(url1)
    domain2 = extract_domain(url2)
    
    return domain1 == domain2


def is_safe_url(url: str) -> bool:
    """
    Check if a URL is safe to crawl.
    
    Args:
        url: The URL to check
        
    Returns:
        bool: True if the URL is safe, False otherwise
    """
    # Must be a valid URL
    if not is_valid_url(url):
        return False
    
    # Check for IP addresses (might indicate potential internal URLs)
    ip_pattern = re.compile(r'\d+\.\d+\.\d+\.\d+')
    if ip_pattern.search(url):
        return False
    
    # Check for localhost and internal domains
    parsed = urlparse(url)
    if parsed.netloc == 'localhost' or parsed.netloc.startswith('127.') or '.local' in parsed.netloc:
        return False
    
    # List of allowed schemes
    allowed_schemes = {'http', 'https'}
    if parsed.scheme.lower() not in allowed_schemes:
        return False
    
    return True


def extract_urls_from_text(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text: Text to extract URLs from
        
    Returns:
        List[str]: List of extracted URLs
    """
    if not text:
        return []
    
    # Pattern to match URLs
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    
    # Find all matches
    matches = re.findall(url_pattern, text)
    
    return matches


def resolve_relative_url(base_url: str, relative_url: str) -> str:
    """
    Resolve a relative URL against a base URL.
    
    Args:
        base_url: The base URL
        relative_url: The relative URL
        
    Returns:
        str: The resolved absolute URL
    """
    if not base_url or not relative_url:
        return ""
    
    try:
        return urljoin(base_url, relative_url)
    except Exception:
        return ""


def clean_url_for_display(url: str, max_length: int = 50) -> str:
    """
    Clean a URL for display purposes, truncating if necessary.
    
    Args:
        url: The URL to clean
        max_length: Maximum length for display
        
    Returns:
        str: The cleaned URL
    """
    if not url:
        return ""
    
    # Extract domain and path
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Truncate path if URL is too long
        if len(domain) + len(path) > max_length and len(path) > 10:
            displayed_path = path[:10] + "..." + path[-10:]
            return f"{domain}{displayed_path}"
        
        return f"{domain}{path}"
    except Exception:
        # If parsing fails, truncate the raw URL
        if len(url) > max_length:
            return url[:max_length-3] + "..."
        return url 