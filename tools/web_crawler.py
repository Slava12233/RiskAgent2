"""
Web crawler module for fetching content from webpages.

This module provides functions for crawling webpages and extracting content
using Playwright directly for better control over the browser lifecycle.
"""

import asyncio
import os
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urlparse
import time
import tempfile
import shutil
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import logging
import subprocess
import sys
import aiohttp

# Import custom logging utilities
from utils.logging_utils import (
    get_logger,
    log_request,
    log_response,
    log_error,
    log_playwright_status,
    log_fallback,
    log_system_info
)

# Try importing Crawl4AI as an alternative
try:
    import crawl4ai
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False

# Get logger
logger = get_logger()

# Log system information at module import time
log_system_info()

# Constants
DEFAULT_TIMEOUT = 60000  # 60 seconds
DEFAULT_WORD_THRESHOLD = 100
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Website type definitions for specialized extraction
WEBSITE_TYPES = {
    "news": {
        "domains": ["cnn.com", "bbc.com", "reuters.com", "nytimes.com", "theguardian.com", 
                   "jpost.com", "timesofisrael.com", "haaretz.com"],
        "selectors": ["article", "main", ".article-body", ".story-body", ".article__content"]
    },
    "documentation": {
        "domains": ["docs.python.org", "developer.mozilla.org", "reactjs.org", "react.dev"],
        "selectors": ["article", "main", ".documentation", ".content", ".main-content"]
    },
    "blog": {
        "domains": ["medium.com", "dev.to", "hashnode.com", "wordpress.com", "blogger.com"],
        "selectors": ["article", ".post-content", ".article-content", ".blog-post"]
    },
    "ecommerce": {
        "domains": ["amazon.com", "ebay.com", "walmart.com", "aliexpress.com", "etsy.com"],
        "selectors": [".product-description", ".product-details", ".item-description"]
    },
    "social": {
        "domains": ["twitter.com", "facebook.com", "instagram.com", "linkedin.com", "reddit.com"],
        "selectors": [".tweet", ".post", ".content", ".feed-item"]
    },
    "product_review": {
        "domains": ["rtings.com", "tomsguide.com", "techradar.com", "cnet.com", "pcmag.com", 
                   "wirecutter.com", "ign.com", "gamespot.com"],
        "selectors": [
            "article", 
            ".review-body", 
            ".article-content", 
            ".product-review", 
            ".buying-guide",
            ".product-roundup",
            ".best-list",
            "#product-review-container",
            ".review-wrapper",
            ".product-content"
        ]
    },
    "tech_review": {
        "domains": ["rtings.com", "tomsguide.com", "techradar.com"],
        "selectors": [
            ".review-section", 
            ".product-breakdown", 
            ".specs-table", 
            ".pros-cons", 
            ".verdict",
            ".ratings-wrapper",
            ".product-hero",
            ".product-summary",
            ".product-specs"
        ]
    }
}

class WebCrawlerError(Exception):
    """Custom exception for web crawler errors."""
    pass

class PlaywrightManager:
    """Manager for Playwright browser instances."""
    
    def __init__(self):
        """Initialize the PlaywrightManager."""
        self.browser = None
        self.context = None
        self.page = None
        self.logger = logging.getLogger("web_crawler")

        try:
            # Use subprocess.run instead of asyncio for better Python 3.12 compatibility
            import subprocess
            import sys
            
            # Check if playwright is installed
            try:
                import playwright
                # Get version safely without accessing __version__ directly
                try:
                    self.playwright_version = getattr(playwright, '__version__', 'unknown')
                except AttributeError:
                    self.playwright_version = 'unknown'
                self.logger.info(f"Playwright version: {self.playwright_version}")
            except ImportError:
                self.playwright_version = "unknown"
                self.logger.info(f"Playwright version: {self.playwright_version}")
                
            self.logger.info("Attempting to launch Playwright browser")
            
            # Install browsers if needed using subprocess.run
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    capture_output=True, 
                    text=True,
                    timeout=120  # Add timeout to prevent hanging
                )
                if result.returncode != 0:
                    self.logger.warning(f"Playwright browser installation issue: {result.stderr}")
                else:
                    self.logger.debug("Playwright browsers installed successfully")
            except Exception as e:
                self.logger.warning(f"Error during Playwright browser installation: {str(e)}")
            
            # Initialize browser synchronously
            self._init_browser_sync()
                
        except Exception as e:
            self.logger.error(f"Error initializing PlaywrightManager: {str(e)}")
            self.browser = None
    
    def _init_browser_sync(self):
        """Initialize the browser synchronously."""
        try:
            from playwright.sync_api import sync_playwright
            
            pw = sync_playwright().start()
            self.logger.info("Launching Chromium browser")
            
            # Use sync_playwright instead of async version
            self.browser = pw.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--disable-extensions',
                    '--disable-notifications',
                ]
            )
            
            self.logger.info("Browser launched successfully")
        except Exception as e:
            self.logger.error(f"Error initializing browser: {str(e)}")
            self.browser = None

    def close(self):
        """Close the browser."""
        try:
            if self.browser:
                self.browser.close()
                self.logger.info("Browser closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}")

def detect_website_type(url: str) -> Optional[str]:
    """
    Detect the type of website based on the URL.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Optional[str]: The detected website type or None if not detected
    """
    try:
        domain = urlparse(url).netloc.lower()
        
        for website_type, config in WEBSITE_TYPES.items():
            if any(d in domain for d in config["domains"]):
                return website_type
        
        return None
    except Exception as e:
        logger.warning(f"Error detecting website type: {str(e)}")
        return None

def get_target_selectors(url: str) -> List[str]:
    """
    Get target CSS selectors for a specific URL based on website type.
    
    Args:
        url: The URL to get selectors for
        
    Returns:
        List[str]: List of CSS selectors to target for content extraction
    """
    website_type = detect_website_type(url)
    
    if website_type and website_type in WEBSITE_TYPES:
        return WEBSITE_TYPES[website_type]["selectors"]
    
    # Default selectors for general websites
    return ["article", "main", ".content", "#content", ".main-content"]

async def check_playwright_installed() -> bool:
    """
    Check if Playwright browsers are installed.
    
    Returns:
        bool: True if Playwright browsers are installed, False otherwise
    """
    try:
        # Try to import playwright
        import playwright
        from playwright.async_api import async_playwright
        
        logger.info(f"Playwright version: {getattr(playwright, '__version__', 'unknown')}")
        
        # Try to launch a browser
        try:
            logger.info("Attempting to launch Playwright browser")
            async with async_playwright() as p:
                try:
                    logger.info("Launching Chromium browser")
                    browser = await p.chromium.launch(headless=True)
                    logger.info("Browser launched successfully")
                    await browser.close()
                    logger.info("Browser closed successfully")
                    return True
                except Exception as e:
                    if "Executable doesn't exist" in str(e):
                        logger.error(f"Playwright browser executable not found: {str(e)}")
                        return False
                    logger.error(f"Error launching browser: {str(e)}")
                    logger.debug(f"Error type: {type(e).__name__}")
                    logger.debug(f"Error details: {repr(e)}")
                    return False
        except NotImplementedError as e:
            # This error occurs on some Python versions with asyncio
            logger.error(f"NotImplementedError in asyncio subprocess: {str(e)}")
            logger.debug(f"Error type: {type(e).__name__}")
            logger.debug(f"Error details: {repr(e)}")
            logger.info("Using synchronous fallback")
            
            # Use a synchronous fallback
            import subprocess
            try:
                # Check if playwright is installed using a synchronous command
                logger.info("Checking Playwright installation with subprocess")
                result = subprocess.run(
                    ["playwright", "--version"], 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                logger.info(f"Subprocess result: {result.returncode}")
                if result.stdout:
                    logger.info(f"Subprocess stdout: {result.stdout.strip()}")
                if result.stderr:
                    logger.info(f"Subprocess stderr: {result.stderr.strip()}")
                return result.returncode == 0
            except Exception as e:
                logger.error(f"Error checking Playwright installation with subprocess: {str(e)}")
                logger.debug(f"Error type: {type(e).__name__}")
                logger.debug(f"Error details: {repr(e)}")
                return False
    except ImportError as e:
        logger.error(f"Playwright import error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error checking Playwright installation: {str(e)}")
        logger.debug(f"Error type: {type(e).__name__}")
        logger.debug(f"Error details: {repr(e)}")
        return False

def check_playwright_installed_sync() -> bool:
    """
    Check if Playwright is installed and working.
    
    Returns:
        bool: True if Playwright is installed and working, False otherwise
    """
    try:
        # Try to import playwright
        import playwright
        logger.info(f"Playwright version: {getattr(playwright, '__version__', 'unknown')}")
        
        # Check if we're on Python 3.12, which has known asyncio subprocess issues
        if sys.version_info.major == 3 and sys.version_info.minor >= 12:
            logger.warning("Python 3.12+ detected, which may have compatibility issues with Playwright")
            
            # Use a subprocess check as a fallback
            import subprocess
            try:
                result = subprocess.run(
                    ["playwright", "--version"], 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                return result.returncode == 0
            except Exception as e:
                logger.error(f"Error checking Playwright with subprocess: {str(e)}")
                return False
        
        # Use synchronous API to check Playwright for older Python versions
        try:
            playwright_manager = PlaywrightManager()
            result = playwright_manager.browser is not None
            playwright_manager.close()
            return result
        except NotImplementedError:
            logger.error("NotImplementedError: asyncio subprocess transport not implemented")
            return False
        except Exception as e:
            logger.error(f"Error checking Playwright: {str(e)}")
            return False
    except Exception:
        return False

async def extract_content_from_page(page: Page, url: str, context: str = "", summary: bool = False) -> str:
    """
    Extract content from a page that has already been navigated to.
    
    Args:
        page: The Playwright page object
        url: The URL of the page
        context: Additional context about what information to look for
        summary: Whether to return a summary of the page
        
    Returns:
        str: The extracted content from the page
    """
    try:
        start_time = time.time()
        logger.info(f"Extracting content from {url}")
        
        # Get the page content and title
        html_content = await page.content()
        title = await page.title()
        
        logger.info(f"Page title: {title}")
        
        # Use BeautifulSoup to extract content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find and remove unwanted elements that might contain noise
        unwanted_selectors = [
            'nav', 'header', 'footer', 'aside', 
            '.ads', '.advertisement', '.cookie-notice',
            '.popup', '#popup', '.modal', '#modal',
            '.newsletter', '.subscription', '.sidebar',
            'script', 'style', 'noscript', 'iframe',
            '.social-media', '.share-buttons',
            'svg', '.comment-section', '#comments'
        ]
        
        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Get the website type
        website_type = detect_website_type(url)
        logger.info(f"Detected website type: {website_type or 'general'}")
        
        # Try to find main content using target selectors
        target_selectors = get_target_selectors(url)
        main_content = None
        
        # Try each selector in order, looking for one with sufficient content
        for selector in target_selectors:
            elements = soup.select(selector)
            if elements:
                # Filter out elements with very little text
                content_elements = [el for el in elements if len(el.get_text(strip=True)) > 200]
                
                if content_elements:
                    # Choose the element with the most text content
                    main_content = max(content_elements, key=lambda el: len(el.get_text(strip=True)))
                    logger.info(f"Found main content using selector: {selector}")
                    break
        
        # If no main content found, use the body
        if not main_content:
            logger.info("No main content found with specific selectors, using body")
            main_content = soup.body
            
            # If the body is too large, try to find a main content section
            if len(main_content.get_text(strip=True)) > 50000:
                logger.info("Body is very large, trying to find a more focused content section")
                
                # Additional common content containers
                for selector in ['main', 'article', '.content', '#content', '.main-content', '.post', '.entry']:
                    elements = soup.select(selector)
                    if elements and len(elements[0].get_text(strip=True)) > 500:
                        main_content = elements[0]
                        logger.info(f"Found focused content section using selector: {selector}")
                        break
        
        # Extract text content
        if main_content:
            # Get all paragraphs and headings for better structured content
            paragraphs = []
            
            # Look for headings and paragraphs
            for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote']):
                text = element.get_text(strip=True)
                if text and len(text) > 20:  # Only include non-empty, substantial paragraphs
                    if element.name.startswith('h'):
                        # Add extra newlines around headings for better formatting
                        paragraphs.append(f"\n## {text}\n")
                    else:
                        paragraphs.append(text)
            
            # Join all paragraphs with double newline for better readability
            text_content = "\n\n".join(paragraphs)
            
            # If we couldn't extract structured content, fall back to regular text extraction
            if not text_content or len(text_content) < 200:
                logger.info("Structured extraction produced limited content, falling back to simple extraction")
                text_content = main_content.get_text(separator='\n\n', strip=True)
        else:
            text_content = soup.get_text(separator='\n\n', strip=True)
        
        # Create markdown content
        content = f"# {title}\n\n{text_content}"
        
        # Limit content size if summary is requested
        if summary and len(content) > 2000:
            logger.info(f"Truncating content for summary (original length: {len(content)} chars)")
            content = content[:2000] + "...\n\n(Content truncated for summary)"
        
        # Add metadata if available
        metadata = {
            "title": title,
            "url": url,
            "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "website_type": website_type or "general"
        }
        
        # Try to extract description and author
        description_meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if description_meta and description_meta.get("content"):
            metadata["description"] = description_meta["content"]
        
        author_meta = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", attrs={"property": "article:author"})
        if author_meta and author_meta.get("content"):
            metadata["author"] = author_meta["author"]
        
        # Try to extract publication date
        date_meta = (
            soup.find("meta", attrs={"name": "date"}) or 
            soup.find("meta", attrs={"property": "article:published_time"}) or
            soup.find("meta", attrs={"name": "publication_date"})
        )
        if date_meta and date_meta.get("content"):
            metadata["publication_date"] = date_meta["content"]
        
        # Add metadata to content
        metadata_str = "\n\n## Page Metadata\n\n"
        for key, value in metadata.items():
            metadata_str += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        
        content = content + "\n\n" + metadata_str
        
        # Add context-specific information if provided
        if context:
            # Try to find relevant sections based on context keywords
            context_keywords = [kw.strip().lower() for kw in context.split() if len(kw.strip()) > 3]
            if context_keywords:
                logger.info(f"Looking for content relevant to context keywords: {context_keywords}")
                relevant_sections = []
                
                # Find paragraphs containing context keywords
                paragraphs = content.split("\n\n")
                for paragraph in paragraphs:
                    if any(kw in paragraph.lower() for kw in context_keywords):
                        relevant_sections.append(paragraph)
                
                # If we found relevant sections, highlight them
                if relevant_sections:
                    logger.info(f"Found {len(relevant_sections)} relevant sections based on context")
                    content += "\n\n## Relevant Information\n\n"
                    content += "\n\n".join(relevant_sections)
        
        # Log performance
        duration = time.time() - start_time
        content_size = len(content)
        logger.info(f"Content extraction completed in {duration:.2f}s, size: {content_size} bytes")
        
        return content
    
    except Exception as e:
        logger.error(f"Error extracting content from page: {str(e)}")
        return f"Error extracting content: {str(e)}"

async def crawl_webpage(url, timeout=DEFAULT_TIMEOUT, user_agent=None, summary=False):
    """
    Crawl a webpage and extract its content.
    This is the async version of the function.
    
    Args:
        url: The URL to crawl
        timeout: Timeout in seconds
        user_agent: User agent to use
        summary: Whether to return a summary of the page
        
    Returns:
        str: Extracted content
    """
    logger = logging.getLogger("web_crawler")
    logger.info(f"Crawling {url}")
    
    # Try with Playwright first
    try:
        # Modified to use the synchronous version for better compatibility
        content = await asyncio.to_thread(
            crawl_webpage_sync, url, timeout, user_agent, summary
        )
        return content
    except Exception as e:
        logger.info(f"Falling back to HTTP approach after Playwright failed: {str(e)}")
        
    # Fallback to HTTP approach
    try:
        # First try with aiohttp
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                logger.debug(f"Fetching {url} with aiohttp")
                headers = {'User-Agent': user_agent or DEFAULT_USER_AGENT}
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP error {response.status} for {url}")
                        raise WebCrawlerError(f"HTTP error {response.status}")
                    
                    html = await response.text()
                    logger.debug(f"Successfully fetched {url} with aiohttp")
                    return extract_content(url, html, summary)
        except Exception as e:
            logger.warning(f"aiohttp error: {str(e)}, falling back to requests")
            
        # Fallback to synchronous requests
        logger.info(f"Using synchronous requests for {url}")
        return await asyncio.to_thread(crawl_with_requests, url, timeout, user_agent, summary)
    except Exception as e:
        logger.error(f"Error crawling {url} with HTTP fallback: {str(e)}")
        return f"Error crawling {url}: {str(e)}"

def crawl_webpage_sync(url, context="", timeout=DEFAULT_TIMEOUT, user_agent=None, summary=False):
    """
    Synchronous version of crawl_webpage.
    
    Args:
        url: The URL to crawl
        context: Additional context about what information to look for
        timeout: Timeout in seconds
        user_agent: User agent to use
        summary: Whether to return a summary of the page
        
    Returns:
        str: Extracted content
    """
    logger = logging.getLogger("web_crawler")
    logger.info(f"Crawling {url}")
    
    # Try with Crawl4AI first if available (more reliable on Python 3.12)
    if CRAWL4AI_AVAILABLE and sys.version_info.major == 3 and sys.version_info.minor >= 12:
        try:
            logger.info("Using Crawl4AI for web crawling (better Python 3.12 compatibility)")
            return crawl_with_crawl4ai(url, context, timeout, user_agent, summary)
        except Exception as e:
            logger.warning(f"Crawl4AI crawling failed: {str(e)}")
    
    # Otherwise try with Playwright
    try:
        # Check Python version - we know 3.12+ has issues with Playwright
        if sys.version_info.major == 3 and sys.version_info.minor >= 12:
            logger.info("Python 3.12+ detected, trying Playwright carefully")
            
        # Use the PlaywrightManager to manage browser sessions
        manager = PlaywrightManager()
        
        if manager.browser:
            # Use a context and page for this specific crawl
            browser_context = manager.browser.new_context(
                user_agent=user_agent or DEFAULT_USER_AGENT
            )
            
            page = browser_context.new_page()
            
            try:
                # Navigate to the URL
                html = _navigate_with_retry_sync(page, url, timeout)
                
                # Extract content from page
                soup = BeautifulSoup(html, 'html.parser')
                content = extract_content(url, html, summary)
                
                # Clean up
                page.close()
                browser_context.close()
                
                return content
            finally:
                # Ensure resources are cleaned up
                try:
                    page.close()
                    browser_context.close()
                except:
                    pass
        else:
            logger.warning("No Playwright browser available, falling back to HTTP")
            raise WebCrawlerError("Playwright browser initialization failed")
    except Exception as e:
        logger.warning(f"Playwright crawling failed: {str(e)}")
    
    # Fallback to HTTP approach
    try:
        # Use requests for a synchronous HTTP request
        return crawl_with_requests(url, timeout, user_agent, summary)
    except Exception as e:
        # Last resort - try Crawl4AI if available but not already tried
        if CRAWL4AI_AVAILABLE and not (sys.version_info.major == 3 and sys.version_info.minor >= 12):
            try:
                logger.info("Last resort: Using Crawl4AI for web crawling")
                return crawl_with_crawl4ai(url, context, timeout, user_agent, summary)
            except Exception as crawl4ai_error:
                logger.error(f"Crawl4AI error: {str(crawl4ai_error)}")
                
        # Return a meaningful error message
        error_message = f"Failed to crawl {url}: {str(e)}"
        logger.error(error_message)
        return error_message

def _navigate_with_retry_sync(page, url, timeout=DEFAULT_TIMEOUT, max_retries=3):
    """
    Navigate to a URL with retry logic using sync Playwright API.
    
    Args:
        page: Playwright page
        url: URL to navigate to
        timeout: Timeout in seconds
        max_retries: Maximum number of retries
        It's really critical to get the URL.
        
    Returns:
        str: HTML content
    """
    logger = logging.getLogger("web_crawler")
    
    # Different wait_until strategies to try
    strategies = ["networkidle", "domcontentloaded", "load"]
    
    for attempt in range(1, max_retries + 1):
        current_timeout = timeout * (1 + 0.5 * (attempt - 1))  # Increase timeout with each retry
        wait_until = strategies[min(attempt - 1, len(strategies) - 1)]  # Use different strategy for each retry
        
        try:
            logger.info(f"Attempt {attempt} for {url} with timeout {current_timeout}s")
            logger.info(f"Using wait_until={wait_until} for this attempt")
            
            # Use sync navigate
            page.goto(url, wait_until=wait_until, timeout=current_timeout * 1000)
            
            # Get the content
            html = page.content()
            return html
            
        except Exception as e:
            logger.warning(f"Error navigating to {url} with Playwright: {str(e)}")
            
            if attempt < max_retries:
                # Wait before retry with exponential backoff
                wait_time = 2.5 * attempt * 3
                logger.info(f"Waiting {wait_time}s before retry {attempt}")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed after {max_retries} attempts with Playwright for {url}")
                raise WebCrawlerError(f"Failed to navigate to {url} after {max_retries} attempts: {str(e)}")

def crawl_with_requests(url, timeout=DEFAULT_TIMEOUT, user_agent=None, summary=False):
    """
    Crawl a webpage using requests (synchronous HTTP).
    
    Args:
        url: The URL to crawl
        timeout: Timeout in seconds
        user_agent: User agent to use
        summary: Whether to return a summary of the page
        
    Returns:
        str: Extracted content
    """
    logger = logging.getLogger("web_crawler")
    logger.info(f"Using synchronous requests for {url}")
    
    try:
        import requests
        
        # Ensure user_agent is a string, not a boolean
        if user_agent is None or user_agent is True:
            user_agent = DEFAULT_USER_AGENT
        elif not isinstance(user_agent, str):
            user_agent = DEFAULT_USER_AGENT
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        
        if response.status_code != 200:
            logger.warning(f"HTTP error {response.status_code} for {url}")
            return f"Error: HTTP status {response.status_code} for {url}"
        
        # Extract the content
        html = response.text
        return extract_content(url, html, summary)
        
    except Exception as e:
        logger.error(f"Error with requests for {url}: {str(e)}")
        return f"Error crawling {url}: {str(e)}"

async def crawl_multiple_webpages(urls: List[str], context: str = "", summary: bool = True) -> str:
    """
    Crawl multiple webpages and combine their content.
    Uses the crawl_webpage function which will automatically fall back to HTTP if Playwright is not available.
    
    Args:
        urls: List of URLs to crawl
        context: Additional context about what information to look for
        summary: Whether to return summaries of the pages
        
    Returns:
        str: The combined content from the webpages
    """
    # Add a sources section at the beginning
    sources_section = "## Sources Being Crawled\n"
    for i, url in enumerate(urls):
        sources_section += f"{i+1}. [{url}]({url})\n"
    
    # Limit the number of URLs to crawl to avoid excessive resource usage
    max_urls = 5
    if len(urls) > max_urls:
        logger.warning(f"Limiting crawl to {max_urls} URLs out of {len(urls)} requested")
        urls = urls[:max_urls]
    
    # Create a map of URL to its results
    results = {}
    
    # Create a semaphore to limit concurrent crawls
    # This prevents overloading the system with too many browser instances
    semaphore = asyncio.Semaphore(2)  # Max 2 concurrent crawls
    
    async def crawl_with_semaphore(url):
        """Helper function to crawl with a semaphore for concurrency control."""
        async with semaphore:
            try:
                logger.info(f"Crawling {url}")
                content = await crawl_webpage(url, context, summary)
                return url, content
            except Exception as e:
                error_message = f"Error crawling {url}: {str(e)}"
                logger.error(error_message)
                return url, f"## Error crawling {url}\n\n{error_message}"
    
    # Create tasks for all URLs
    tasks = [crawl_with_semaphore(url) for url in urls]
    
    # Wait for all tasks to complete
    for task in asyncio.as_completed(tasks):
        try:
            url, content = await task
            results[url] = content
        except Exception as e:
            logger.error(f"Task error: {str(e)}")
    
    # Build the combined content in the original URL order to maintain consistency
    combined_content = [sources_section]
    
    for url in urls:
        if url in results:
            combined_content.append(f"## Information from {url}\n")
            combined_content.append(results[url])
            combined_content.append("\n---\n")
        else:
            combined_content.append(f"## Error crawling {url}\n\nFailed to obtain content.")
    
    # Return the combined content
    return "\n".join(combined_content)

def crawl_multiple_webpages_sync(urls: List[str], context: str = "", summary: bool = True) -> str:
    """
    Synchronous version of crawl_multiple_webpages.
    
    Args:
        urls: List of URLs to crawl
        context: Additional context about what information to look for
        summary: Whether to return summaries of the pages
        
    Returns:
        str: The combined content from the webpages
    """
    # Get or create an event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If there's no event loop in this thread, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        # Run the async function with a longer timeout for multiple pages
        timeout = DEFAULT_TIMEOUT * (len(urls) + 1) / 1000  # Convert ms to seconds and scale with URL count
        if loop.is_running():
            # If the loop is already running, use run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(crawl_multiple_webpages(urls, context, summary), loop)
            result = future.result(timeout=timeout)
        else:
            # Otherwise, use run_until_complete
            result = loop.run_until_complete(crawl_multiple_webpages(urls, context, summary))
        
        return result
    except Exception as e:
        error_message = f"Error crawling multiple webpages: {str(e)}"
        logger.error(error_message)
        
        # Fallback to individual sequential crawling if parallel crawling fails
        logger.info("Falling back to sequential crawling")
        combined_content = []
        
        # Add a sources section at the beginning
        sources_section = "## Sources Being Crawled\n"
        for i, url in enumerate(urls):
            sources_section += f"{i+1}. [{url}]({url})\n"
        combined_content.append(sources_section)
        
        # Try to crawl each URL individually
        for url in urls:
            try:
                content = crawl_webpage_sync(url, context, summary)
                combined_content.append(f"## Information from {url}\n")
                combined_content.append(content)
                combined_content.append("\n---\n")
            except Exception as url_error:
                logger.error(f"Error crawling {url}: {str(url_error)}")
                combined_content.append(f"## Error crawling {url}\n\n{str(url_error)}")
        
        # Return the combined content
        return "\n".join(combined_content)

def extract_content(url, html, summary=False):
    """
    Extract content from HTML.
    
    Args:
        url: The URL of the page
        html: The HTML content
        summary: Whether to return a summary
        
    Returns:
        str: Extracted content
    """
    try:
        start_time = time.time()
        logger = logging.getLogger("web_crawler")
        
        # Use BeautifulSoup to extract content
        soup = BeautifulSoup(html, 'html.parser')
        
        # Get the title
        title = soup.title.string if soup.title else "No title"
        logger.info(f"Page title: {title}")
        
        # Remove unwanted elements
        unwanted_selectors = [
            'nav', 'header', 'footer', 'aside', 
            '.ads', '.advertisement', '.cookie-notice',
            '.popup', '#popup', '.modal', '#modal',
            '.newsletter', '.subscription', '.sidebar',
            'script', 'style', 'noscript', 'iframe',
            '.social-media', '.share-buttons',
            'svg', '.comment-section', '#comments'
        ]
        
        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Get the website type
        website_type = detect_website_type(url)
        logger.info(f"Detected website type: {website_type or 'general'}")
        
        # Try to find main content using target selectors
        target_selectors = get_target_selectors(url)
        main_content = None
        
        for selector in target_selectors:
            elements = soup.select(selector)
            if elements:
                # Use the first substantial element
                main_content = elements[0]
                logger.info(f"Found main content using selector: {selector}")
                break
        
        # If no main content found, use the body
        if not main_content:
            logger.info("No main content found with specific selectors, using body")
            main_content = soup.body
        
        # Extract text content
        if main_content:
            # Get all paragraphs and headings
            paragraphs = []
            
            for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote']):
                text = element.get_text(strip=True)
                if text and len(text) > 20:
                    if element.name.startswith('h'):
                        paragraphs.append(f"\n## {text}\n")
                    else:
                        paragraphs.append(text)
            
            text_content = "\n\n".join(paragraphs)
            
            # If structured extraction failed, fall back to simple
            if not text_content or len(text_content) < 200:
                logger.info("Structured extraction produced limited content, falling back to simple extraction")
                text_content = main_content.get_text(separator='\n\n', strip=True)
        else:
            text_content = soup.get_text(separator='\n\n', strip=True)
        
        # Create markdown content
        content = f"# {title}\n\n{text_content}"
        
        # Limit content size if summary is requested
        if summary and len(content) > 2000:
            logger.info(f"Truncating content for summary (original length: {len(content)} chars)")
            content = content[:2000] + "...\n\n(Content truncated for summary)"
        
        # Log performance
        duration = time.time() - start_time
        logger.info(f"Content extraction completed in {duration:.2f}s, size: {len(content)} bytes")
        
        return content
    
    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return f"Error extracting content from {url}: {str(e)}"

def crawl_with_crawl4ai(url, context="", timeout=DEFAULT_TIMEOUT, user_agent=None, summary=False):
    """
    Use Crawl4AI as an alternative crawler implementation.
    
    Args:
        url: The URL to crawl
        context: Additional context about what information to look for
        timeout: Timeout in seconds (NOTE: not used directly in BrowserConfig)
        user_agent: User agent to use
        summary: Whether to return a summary of the page
        
    Returns:
        str: Extracted content
    """
    try:
        print(f"Using Crawl4AI to crawl {url}")
        
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
        import asyncio
        
        # Create a browser config without passing timeout (it's not supported)
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        
        # Use timeout in the crawler run config instead
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            # If CrawlerRunConfig supports timeout, use it here
            # timeout=timeout  # This might not be supported either
        )
        
        async def run_crawl():
            crawler = AsyncWebCrawler(config=browser_config)
            await crawler.start()
            
            try:
                result = await crawler.arun(
                    url=url,
                    config=crawl_config,
                    session_id="session1"
                )
                
                if result.success:
                    content = result.markdown_v2.raw_markdown if hasattr(result, 'markdown_v2') else result.markdown
                    await crawler.close()
                    return content
                else:
                    error_message = f"Failed to crawl {url}: {result.error_message}"
                    await crawler.close()
                    return error_message
            except Exception as e:
                await crawler.close()
                raise e
        
        # Run the async function
        return asyncio.run(run_crawl())
    except Exception as e:
        print(f"Error with Crawl4AI for {url}: {str(e)}")
        return f"Error crawling {url}: {str(e)}"
