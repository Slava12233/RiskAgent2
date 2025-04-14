"""
Simple and reliable web crawler module.

This module provides basic web crawling functionality using requests and BeautifulSoup,
which is more reliable than browser automation for simple text extraction.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional, Union
from urllib.parse import urlparse, quote_plus
import time
import concurrent.futures
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_crawler")

# Default user agent to mimic a browser
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Constants for retries and timeouts
MAX_RETRIES = 3
BASE_TIMEOUT = 15
MAX_WORKERS = 3  # Reduced from 5 to 3 to prevent resource exhaustion

def crawl_webpage(url: str, context: str = "", summary: bool = False) -> str:
    """
    Crawl a webpage and extract its content with retry logic.
    
    Args:
        url: The URL to crawl
        context: Optional context/query to focus the extraction
        summary: Whether to return a summary or full content
        
    Returns:
        str: Extracted content in markdown format
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Increase timeout with each retry
            timeout = BASE_TIMEOUT * (1 + 0.5 * attempt)
            logger.info(f"Crawling {url} with simple crawler (attempt {attempt+1}/{MAX_RETRIES}, timeout={timeout}s)")
            
            # Make the request with a reasonable timeout
            headers = {
                'User-Agent': DEFAULT_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()  # Raise an error for bad status codes
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get the page title
            title = soup.title.text.strip() if soup.title else "No title found"
            
            # Remove unwanted elements
            for element in soup.select('script, style, nav, footer, header, aside, .ads, .comments, .navigation'):
                element.decompose()
            
            # Extract main content
            main_content = extract_main_content(soup, url)
            
            # Format as markdown
            markdown = f"# {title}\n\n"
            
            # Add metadata
            markdown += f"**Source**: {url}\n"
            markdown += f"**Crawled at**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Add content
            if summary:
                # For summary, use just a portion of the content
                content_text = main_content[:1500] + "..." if len(main_content) > 1500 else main_content
                markdown += f"{content_text}\n\n*(Summary mode - showing truncated content)*"
            else:
                markdown += main_content
            
            logger.info(f"Successfully crawled {url} on attempt {attempt+1}")
            return markdown
            
        except Exception as e:
            logger.warning(f"Error crawling {url} on attempt {attempt+1}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                # Wait before retry with exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time}s before retry")
                time.sleep(wait_time)
            else:
                # All retries failed
                logger.error(f"Failed to crawl {url} after {MAX_RETRIES} attempts")
                return f"Error: Failed to crawl {url} after {MAX_RETRIES} attempts. {str(e)}"

def extract_main_content(soup: BeautifulSoup, url: str) -> str:
    """
    Extract the main content from a webpage.
    
    Args:
        soup: BeautifulSoup object of the page
        url: Original URL for context
        
    Returns:
        str: Extracted main content as markdown
    """
    # Try different content selectors based on common website layouts
    content_selectors = [
        'main', 'article', '.post-content', '.article-content', '.entry-content',
        '#content', '.content', '.main-content', '.page-content'
    ]
    
    # Find the main content container
    main_element = None
    for selector in content_selectors:
        elements = soup.select(selector)
        if elements:
            # Choose the element with the most content
            main_element = max(elements, key=lambda el: len(el.get_text(strip=True)))
            break
    
    # If no main content found, use the body
    if not main_element:
        main_element = soup.body
    
    # Extract paragraphs and headings
    content_parts = []
    for element in main_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
        text = element.get_text(strip=True)
        if text:
            # Format headings as markdown
            if element.name.startswith('h'):
                heading_level = int(element.name[1])
                heading_marks = '#' * heading_level
                content_parts.append(f"{heading_marks} {text}\n")
            else:
                content_parts.append(text + "\n\n")
    
    # Join all parts
    content = "".join(content_parts)
    
    # If no structured content found, fall back to all text
    if not content or len(content) < 100:
        content = soup.get_text(separator='\n\n', strip=True)
    
    return content

def crawl_multiple_webpages(urls: List[str], context: str = "", summary: bool = True) -> str:
    """
    Crawl multiple webpages and combine their content.
    
    Args:
        urls: List of URLs to crawl
        context: Optional context/query to focus the extraction
        summary: Whether to return summaries or full content
        
    Returns:
        str: Combined content from all webpages
    """
    results = []
    
    # Add a sources section at the beginning
    sources_section = "## Sources Being Crawled\n"
    for i, url in enumerate(urls):
        sources_section += f"{i+1}. [{url}]({url})\n"
    results.append(sources_section)
    
    # Limit the number of concurrent requests to prevent resource exhaustion
    max_workers = min(MAX_WORKERS, len(urls))
    logger.info(f"Crawling {len(urls)} URLs with {max_workers} workers")
    
    # Use ThreadPoolExecutor for parallel crawling with limited concurrency
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a future for each URL
        future_to_url = {
            executor.submit(crawl_webpage, url, context, summary): url 
            for url in urls
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                content = future.result()
                results.append(f"## Information from {url}\n\n{content}")
            except Exception as e:
                logger.error(f"Error in thread for {url}: {str(e)}")
                results.append(f"## Error accessing {url}\n\n{str(e)}")
    
    # Combine all results
    return "\n\n".join(results)

def crawl_multiple_webpages_sync(urls: List[str], context: str = "", summary: bool = True) -> str:
    """
    Compatibility function that matches the signature expected by the agent.
    This is a wrapper around crawl_multiple_webpages for API compatibility.
    
    Args:
        urls: List of URLs to crawl
        context: Optional context/query to focus the extraction
        summary: Whether to return summaries or full content
        
    Returns:
        str: Combined content from all webpages
    """
    logger.info(f"Using simple_crawler.crawl_multiple_webpages_sync for URLs: {urls}")
    return crawl_multiple_webpages(urls, context, summary)

def get_relevant_urls(query: str, num_results: int = 3, category: str = "general") -> List[str]:
    """
    Get relevant URLs for a search query using DuckDuckGo with retries.
    
    Args:
        query: Search query
        num_results: Number of results to return
        category: Category of the search (general, news, etc.)
        
    Returns:
        List[str]: List of relevant URLs
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Increase timeout with each retry
            timeout = BASE_TIMEOUT * (1 + 0.5 * attempt)
            logger.info(f"Searching for '{query}' (attempt {attempt+1}/{MAX_RETRIES}, timeout={timeout}s)")
            
            # Format the query for the URL
            formatted_query = quote_plus(query)
            
            # Use different base URLs depending on category
            if category == "news":
                search_url = f"https://html.duckduckgo.com/html/?q={formatted_query}+news"
            else:
                search_url = f"https://html.duckduckgo.com/html/?q={formatted_query}"
            
            # Make the request with a longer timeout
            headers = {'User-Agent': DEFAULT_USER_AGENT}
            response = requests.get(search_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different selectors - DuckDuckGo might change their HTML structure
            possible_selectors = [
                '.result__url',           # Old selector
                '.result-link',           # Possible alternative 
                '.result a.result__a',    # Another possibility
                'a.result__url',          # Another possibility
                '.links_main a',          # Another possibility
                'a[href^="//duckduckgo.com/l/?uddg="]'  # Generic approach for redirect links
            ]
            
            results = []
            for selector in possible_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        # Extract URL - look for href attribute or if it's a text element
                        if element.has_attr('href'):
                            href = element['href']
                            # Handle DuckDuckGo redirect URLs
                            if 'uddg=' in href:
                                url = href.split('uddg=')[-1].split('&rut=')[0]
                                # URL decode if needed
                                import urllib.parse
                                url = urllib.parse.unquote(url)
                            else:
                                url = href
                                
                            if url not in results and not url.endswith(('.pdf', '.doc', '.docx', '.ppt', '.pptx')):
                                results.append(url)
                                if len(results) >= num_results:
                                    return results
                        elif hasattr(element, 'text'):
                            # Some result URLs might be in the text
                            text = element.text.strip()
                            if text.startswith(('http://', 'https://')):
                                if text not in results:
                                    results.append(text)
                                    if len(results) >= num_results:
                                        return results
            
            # If we found any results, return them
            if results:
                logger.info(f"Found {len(results)} URLs for '{query}'")
                return results
                
            # Fallback to generic news sites for news queries
            if category == "news":
                logger.info(f"No results found, using news fallback URLs for '{query}'")
                return [
                    "https://www.bbc.com/news/world-middle-east",
                    "https://www.aljazeera.com/middle-east/",
                    "https://www.reuters.com/world/middle-east/"
                ][:num_results]
            else:
                # Fallback to Wikipedia for general queries
                logger.info(f"No results found, using Wikipedia fallback URL for '{query}'")
                return [f"https://en.wikipedia.org/wiki/{formatted_query.replace('+', '_')}"]
                
        except Exception as e:
            logger.warning(f"Error getting relevant URLs on attempt {attempt+1}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                # Wait before retry with exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time}s before retry")
                time.sleep(wait_time)
            else:
                # All retries failed, return fallback URLs
                logger.error(f"Failed to get relevant URLs after {MAX_RETRIES} attempts")
                
                # Return some default URLs based on category
                if category == "news":
                    return [
                        "https://www.bbc.com/news",
                        "https://www.reuters.com",
                        "https://apnews.com"
                    ][:num_results]
                else:
                    return ["https://en.wikipedia.org/wiki/Main_Page"]

if __name__ == "__main__":
    # Simple test
    test_url = "https://en.wikipedia.org/wiki/Web_crawler"
    content = crawl_webpage(test_url, summary=True)
    print(content[:500] + "...") 