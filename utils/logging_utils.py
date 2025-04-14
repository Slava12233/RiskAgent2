"""
Logging utilities for the web crawler agent.

This module provides functions for logging detailed information about
the web crawler's operations to help diagnose issues.
"""

import os
import logging
import datetime
import platform
import sys
import time
from typing import Dict, Any, Optional

# Configure logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Create a logger
logger = logging.getLogger("web_crawler")
logger.setLevel(logging.DEBUG)

# Create a file handler
log_filename = f"crawler_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_filename))
file_handler.setLevel(logging.DEBUG)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger(name: str = "web_crawler", level: int = logging.INFO) -> logging.Logger:
    """
    Get a logger with the specified name and level.
    
    Args:
        name: The name of the logger
        level: The logging level
        
    Returns:
        logging.Logger: The configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Check if the logger already has handlers
    if not logger.handlers:
        # Create a timestamp for the log file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join("logs", f"{name}_{timestamp}.log")
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Set formatter for handlers
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

def log_system_info(logger: Optional[logging.Logger] = None) -> None:
    """
    Log system information.
    
    Args:
        logger: The logger to use (or create a new one if None)
    """
    if logger is None:
        logger = get_logger()
    
    # Log Python version
    logger.info(f"Python version: {sys.version}")
    
    # Log platform information
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"System: {platform.system()}")
    logger.info(f"Machine: {platform.machine()}")
    logger.info(f"Processor: {platform.processor()}")
    
    # Log Playwright availability
    try:
        import playwright
        logger.info(f"Playwright version: {getattr(playwright, '__version__', 'unknown')}")
    except ImportError:
        logger.info("Playwright not available")
    
    # Log other relevant packages
    try:
        import aiohttp
        logger.info(f"aiohttp version: {aiohttp.__version__}")
    except ImportError:
        logger.info("aiohttp not available")
    
    try:
        import requests
        logger.info(f"requests version: {requests.__version__}")
    except ImportError:
        logger.info("requests not available")
    
    try:
        import bs4
        logger.info(f"BeautifulSoup version: {bs4.__version__}")
    except ImportError:
        logger.info("BeautifulSoup not available")

def log_request(logger: logging.Logger, url: str, method: str = "GET") -> None:
    """
    Log a request being made.
    
    Args:
        logger: The logger to use
        url: The URL being requested
        method: The HTTP method
    """
    logger.info(f"{method} request to {url}")

def log_response(logger: logging.Logger, url: str, status: int, size: int) -> None:
    """
    Log a response received.
    
    Args:
        logger: The logger to use
        url: The URL that was requested
        status: The HTTP status code
        size: The size of the response in bytes
    """
    logger.info(f"Response from {url}: status={status}, size={size} bytes")

def log_error(logger: logging.Logger, url: str, error: Exception) -> None:
    """
    Log an error that occurred during a request.
    
    Args:
        logger: The logger to use
        url: The URL that was requested
        error: The error that occurred
    """
    logger.error(f"Error requesting {url}: {str(error)}")
    logger.debug(f"Error type: {type(error).__name__}")
    logger.debug(f"Error details: {repr(error)}")

def log_playwright_status(logger: logging.Logger, url: str, status: str, details: str = "") -> None:
    """
    Log Playwright status information.
    
    Args:
        logger: The logger to use
        url: The URL being processed
        status: The status of the Playwright operation
        details: Additional details
    """
    message = f"Playwright {status} for {url}"
    if details:
        message += f": {details}"
    logger.info(message)

def log_fallback(logger: logging.Logger, url: str, reason: str) -> None:
    """
    Log a fallback to a simpler approach.
    
    Args:
        logger: The logger to use
        url: The URL being processed
        reason: The reason for the fallback
    """
    logger.info(f"Falling back to simpler HTTP approach for {url}: {reason}")

def log_playwright_attempt(logger: logging.Logger, url: str, attempt: int, 
                          timeout: float, wait_until: str) -> None:
    """
    Log a Playwright navigation attempt.
    
    Args:
        logger: The logger to use
        url: The URL being navigated to
        attempt: The attempt number
        timeout: The timeout in milliseconds
        wait_until: The wait_until strategy
    """
    logger.info(f"Playwright attempt {attempt} for {url} with timeout={timeout}ms, wait_until={wait_until}")

def log_crawl_success(logger: logging.Logger, url: str, method: str, 
                     duration: float, content_size: int) -> None:
    """
    Log a successful crawl.
    
    Args:
        logger: The logger to use
        url: The URL that was crawled
        method: The method used (e.g., "Playwright", "HTTP")
        duration: The duration of the crawl in seconds
        content_size: The size of the extracted content in bytes
    """
    logger.info(f"Successfully crawled {url} with {method} in {duration:.2f}s, content size: {content_size} bytes")

def log_retry(logger: logging.Logger, url: str, attempt: int, max_attempts: int, 
             wait_time: float, error: str) -> None:
    """
    Log a retry attempt.
    
    Args:
        logger: The logger to use
        url: The URL being retried
        attempt: The current attempt number
        max_attempts: The maximum number of attempts
        wait_time: The wait time before the next attempt
        error: The error that caused the retry
    """
    logger.info(f"Retry {attempt}/{max_attempts} for {url} in {wait_time:.2f}s due to: {error}")
