"""
Search API integration for the web crawler agent.

This module provides functions for integrating with external search APIs
to find relevant URLs for user queries.
"""

import os
import json
import time
import re
from typing import List, Dict, Any, Optional
import requests
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API keys from environment variables
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX")  # Custom Search Engine ID
BING_SEARCH_API_KEY = os.getenv("BING_SEARCH_API_KEY")

# Cache for search results to avoid redundant API calls
# Structure: {query: {results: [...], timestamp: time.time()}}
search_cache = {}
CACHE_EXPIRY_TIME = 3600  # 1 hour in seconds


def search_with_google(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search using Google Custom Search API.
    
    Args:
        query: The search query
        num_results: Number of results to return
        
    Returns:
        List[Dict[str, str]]: List of search results
    
    Raises:
        ValueError: If API key or CX is not set
        requests.RequestException: If there's an API error
    """
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_CX:
        raise ValueError("Google Search API key or CX not set")
    
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        "q": query,
        "key": GOOGLE_SEARCH_API_KEY,
        "cx": GOOGLE_SEARCH_CX,
        "num": min(num_results, 10)  # Max 10 results per request
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        raise requests.RequestException(f"Google Search API Error: {response.status_code} - {response.text}")
    
    data = response.json()
    
    results = []
    if "items" in data:
        for item in data["items"]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "Google Custom Search"
            })
    
    return results


def search_with_bing(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search using Bing Web Search API.
    
    Args:
        query: The search query
        num_results: Number of results to return
        
    Returns:
        List[Dict[str, str]]: List of search results
    
    Raises:
        ValueError: If API key is not set
        requests.RequestException: If there's an API error
    """
    if not BING_SEARCH_API_KEY:
        raise ValueError("Bing Search API key not set")
    
    url = "https://api.bing.microsoft.com/v7.0/search"
    
    headers = {
        "Ocp-Apim-Subscription-Key": BING_SEARCH_API_KEY
    }
    
    params = {
        "q": query,
        "count": min(num_results, 50)  # Max 50 results per request
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        raise requests.RequestException(f"Bing Search API Error: {response.status_code} - {response.text}")
    
    data = response.json()
    
    results = []
    if "webPages" in data and "value" in data["webPages"]:
        for item in data["webPages"]["value"]:
            results.append({
                "title": item.get("name", ""),
                "link": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "source": "Bing Web Search"
            })
    
    return results


def search_web(query: str, num_results: int = 5, use_cache: bool = True) -> List[Dict[str, str]]:
    """
    Search the web using available search APIs.
    Falls back to alternatives if primary API fails.
    
    Args:
        query: The search query
        num_results: Number of results to return
        use_cache: Whether to use cached results
        
    Returns:
        List[Dict[str, str]]: List of search results
    """
    # Check cache first
    cache_key = f"{query}_{num_results}"
    if use_cache and cache_key in search_cache:
        cache_entry = search_cache[cache_key]
        # Check if cache is still valid
        if time.time() - cache_entry["timestamp"] < CACHE_EXPIRY_TIME:
            print(f"Using cached search results for: {query}")
            return cache_entry["results"]
    
    results = []
    
    # Try Google first if API key is available
    if GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX:
        try:
            results = search_with_google(query, num_results)
        except Exception as e:
            print(f"Google Search API error: {str(e)}")
            results = []
    
    # Try Bing if Google failed or API key is not available
    if not results and BING_SEARCH_API_KEY:
        try:
            results = search_with_bing(query, num_results)
        except Exception as e:
            print(f"Bing Search API error: {str(e)}")
            results = []
    
    # If both APIs failed or no API keys are available, use a fallback approach
    if not results:
        results = fallback_search(query, num_results)
    
    # Update cache
    if use_cache:
        search_cache[cache_key] = {
            "results": results,
            "timestamp": time.time()
        }
    
    return results


def extract_urls_from_results(search_results: List[Dict[str, str]]) -> List[str]:
    """
    Extract URLs from search results.
    
    Args:
        search_results: List of search result dictionaries
        
    Returns:
        List[str]: List of extracted URLs
    """
    return [result["link"] for result in search_results if "link" in result]


def filter_urls_by_domain(urls: List[str], preferred_domains: List[str]) -> List[str]:
    """
    Filter and prioritize URLs based on preferred domains.
    
    Args:
        urls: List of URLs to filter
        preferred_domains: List of preferred domains
        
    Returns:
        List[str]: Filtered and prioritized list of URLs
    """
    # Extract domain from URL
    def get_domain(url):
        match = re.search(r"^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/\n]+)", url)
        return match.group(1) if match else ""
    
    # Split URLs into preferred and others
    preferred_urls = []
    other_urls = []
    
    for url in urls:
        domain = get_domain(url)
        if any(preferred_domain in domain for preferred_domain in preferred_domains):
            preferred_urls.append(url)
        else:
            other_urls.append(url)
    
    # Return preferred URLs first, then others
    return preferred_urls + other_urls


def fallback_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Fallback search when APIs are not available.
    Uses local logic to generate potential URLs.
    
    Args:
        query: The search query
        num_results: Number of results to return
        
    Returns:
        List[Dict[str, str]]: List of search results
    """
    # This is a very simplified approach without actually searching the web
    results = []
    
    # Generate Wikipedia URL for the query
    wikipedia_query = quote_plus(query)
    results.append({
        "title": f"{query} - Wikipedia",
        "link": f"https://en.wikipedia.org/wiki/{wikipedia_query.replace('+', '_')}",
        "snippet": f"Wikipedia article about {query}",
        "source": "Fallback Search"
    })
    
    # Add other common knowledge sites
    results.append({
        "title": f"{query} - Encyclopedia Britannica",
        "link": f"https://www.britannica.com/search?query={wikipedia_query}",
        "snippet": f"Britannica information about {query}",
        "source": "Fallback Search"
    })
    
    # For programming queries, add programming sites
    programming_terms = ["python", "javascript", "programming", "code", "html", "css", "api", "framework"]
    if any(term in query.lower() for term in programming_terms):
        results.append({
            "title": f"{query} - MDN Web Docs",
            "link": f"https://developer.mozilla.org/en-US/search?q={wikipedia_query}",
            "snippet": f"MDN documentation related to {query}",
            "source": "Fallback Search"
        })
        results.append({
            "title": f"{query} - Stack Overflow",
            "link": f"https://stackoverflow.com/search?q={wikipedia_query}",
            "snippet": f"Stack Overflow questions related to {query}",
            "source": "Fallback Search"
        })
    
    # For product-related queries, add review sites
    product_terms = ["review", "best", "top", "compare", "vs", "versus", "which", "laptop", "phone", "camera"]
    if any(term in query.lower() for term in product_terms):
        results.append({
            "title": f"{query} - PCMag",
            "link": f"https://www.pcmag.com/search?query={wikipedia_query}",
            "snippet": f"PCMag reviews related to {query}",
            "source": "Fallback Search"
        })
        results.append({
            "title": f"{query} - CNET",
            "link": f"https://www.cnet.com/search/?query={wikipedia_query}",
            "snippet": f"CNET reviews related to {query}",
            "source": "Fallback Search"
        })
    
    # For news-related queries, add news sites
    news_terms = ["news", "latest", "update", "current events", "breaking", "today"]
    if any(term in query.lower() for term in news_terms):
        results.append({
            "title": f"{query} - Reuters",
            "link": f"https://www.reuters.com/search/news?blob={wikipedia_query}",
            "snippet": f"Reuters news related to {query}",
            "source": "Fallback Search"
        })
        results.append({
            "title": f"{query} - BBC News",
            "link": f"https://www.bbc.co.uk/search?q={wikipedia_query}&filter=news",
            "snippet": f"BBC News related to {query}",
            "source": "Fallback Search"
        })
    
    return results[:num_results]


def get_relevant_urls(query: str, num_results: int = 5, category: str = None) -> List[str]:
    """
    Get relevant URLs for a query, using search APIs if available.
    
    Args:
        query: The search query
        num_results: Number of results to return
        category: Optional category to help filter results
        
    Returns:
        List[str]: List of relevant URLs
    """
    # Get search results
    search_results = search_web(query, num_results=num_results * 2)  # Get extra results for filtering
    
    # Extract URLs
    urls = extract_urls_from_results(search_results)
    
    # Get preferred domains based on category
    preferred_domains = []
    
    if category == "tech":
        preferred_domains = [
            "developer.mozilla.org", "stackoverflow.com", "github.com", 
            "docs.python.org", "w3schools.com", "reactjs.org", "angular.io"
        ]
    elif category == "product":
        preferred_domains = [
            "pcmag.com", "techradar.com", "cnet.com", "tomsguide.com", 
            "rtings.com", "wirecutter.com", "theverge.com"
        ]
    elif category == "news":
        preferred_domains = [
            "reuters.com", "apnews.com", "bbc.com", "aljazeera.com", 
            "nytimes.com", "theguardian.com", "bloomberg.com"
        ]
    elif category == "travel":
        preferred_domains = [
            "lonelyplanet.com", "tripadvisor.com", "booking.com", 
            "expedia.com", "cntraveler.com"
        ]
    elif category == "health":
        preferred_domains = [
            "mayoclinic.org", "webmd.com", "nih.gov", "who.int", 
            "healthline.com", "cdc.gov"
        ]
    else:
        # General knowledge domains for any category
        preferred_domains = [
            "wikipedia.org", "britannica.com", "nationalgeographic.com", 
            "howstuffworks.com", "khanacademy.org"
        ]
    
    # Filter and prioritize URLs
    filtered_urls = filter_urls_by_domain(urls, preferred_domains)
    
    # Return the requested number of results, or all if fewer are available
    return filtered_urls[:num_results] 