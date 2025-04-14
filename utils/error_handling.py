"""
Error handling utilities for the web crawler agent.

This module provides error handling utilities for the web crawler agent,
including custom exceptions and user-friendly error messages.
"""

from typing import Dict, Any, Callable, TypeVar, Optional

# Type variables for generic functions
T = TypeVar('T')
R = TypeVar('R')


class WebCrawlerError(Exception):
    """
    Custom exception for web crawler errors.
    
    Attributes:
        message: A user-friendly error message
        details: A dictionary with additional error details
    """
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


def safe_execute(func: Callable[..., R], *args, **kwargs) -> R:
    """
    Execute a function safely, catching and wrapping exceptions.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
        
    Raises:
        WebCrawlerError: If an exception occurs during execution
    """
    try:
        return func(*args, **kwargs)
    except WebCrawlerError:
        # Re-raise existing WebCrawlerError instances
        raise
    except Exception as e:
        # Wrap other exceptions in WebCrawlerError
        raise WebCrawlerError(
            message=f"Error during execution: {str(e)}",
            details={"error_type": "execution_error"}
        )


def get_user_friendly_error_message(error_type: str) -> str:
    """
    Get a user-friendly error message for a specific error type.
    
    Args:
        error_type: The type of error that occurred
        
    Returns:
        str: A user-friendly error message
    """
    error_messages = {
        "invalid_url": "I couldn't process this URL. Please provide a valid URL starting with http:// or https://.",
        
        "connection_error": "I couldn't connect to this website. The server might be down or the URL might be incorrect.",
        
        "crawler_timeout": "The website took too long to respond. It might be temporarily overloaded or the content might be too large.",
        
        "site_blocked": "This website seems to be blocking web crawlers. I'm not able to access its content.",
        
        "rate_limited": "I've been temporarily blocked from accessing this website because I've made too many requests. Please try again later.",
        
        "content_extraction_error": "I couldn't extract useful content from this webpage. It might have a non-standard structure or very little textual content.",
        
        "content_too_large": "This webpage has too much content for me to process. Consider specifying a more specific page or section.",
        
        "general_error": "I encountered an unexpected error while trying to access this website. Please try again or try a different URL."
    }
    
    return error_messages.get(error_type, error_messages["general_error"]) 