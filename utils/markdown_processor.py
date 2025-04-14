"""
Markdown processing utilities.

This module provides functions for processing and cleaning markdown content
extracted from web pages, to make it more suitable for use by the agent.
"""

import re
from typing import List, Optional


def clean_markdown(markdown_text: str) -> str:
    """
    Clean markdown text by removing excessive whitespace and formatting.
    
    Args:
        markdown_text: The markdown text to clean
        
    Returns:
        str: The cleaned markdown text
    """
    if not markdown_text:
        return ""
    
    # Remove multiple newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', markdown_text)
    
    # Remove multiple spaces
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    
    # Remove empty bullet points
    cleaned = re.sub(r'\n\s*[-*+]\s*\n', '\n', cleaned)
    
    # Normalize headings with space after #
    cleaned = re.sub(r'(#{1,6})([^#\s])', r'\1 \2', cleaned)
    
    return cleaned.strip()


def extract_main_content(markdown_text: str) -> str:
    """
    Extract the main content from markdown text, focusing on headings and text.
    
    Args:
        markdown_text: The markdown text to process
        
    Returns:
        str: The extracted main content
    """
    if not markdown_text:
        return ""
    
    # Clean the markdown first
    cleaned = clean_markdown(markdown_text)
    
    # Split by headings
    sections = re.split(r'(#{1,6} .*)', cleaned)
    
    # Filter out empty sections
    filtered_sections = [section for section in sections if section.strip()]
    
    # Reassemble the content
    main_content = "\n".join(filtered_sections)
    
    return main_content


def truncate_markdown(markdown_text: str, max_length: int = 8000) -> str:
    """
    Truncate markdown text to a maximum length, preserving structure.
    
    Args:
        markdown_text: The markdown text to truncate
        max_length: Maximum length of the result
        
    Returns:
        str: The truncated markdown text
    """
    if not markdown_text:
        return ""
    
    if len(markdown_text) <= max_length:
        return markdown_text
    
    # Try to truncate at paragraph boundaries
    paragraphs = markdown_text.split('\n\n')
    result = ""
    
    for paragraph in paragraphs:
        if len(result + paragraph + '\n\n') > max_length:
            # Add an ellipsis to indicate truncation
            result += "\n\n... (content truncated)"
            break
        result += paragraph + '\n\n'
    
    return result.strip()


def summarize_markdown(markdown_text: str, max_length: int = 2000) -> str:
    """
    Create a simplified summary of the markdown content.
    
    Args:
        markdown_text: The markdown text to summarize
        max_length: Maximum length of the summary
        
    Returns:
        str: A summary of the markdown text
    """
    if not markdown_text:
        return ""
    
    # Extract headings as a simple form of summarization
    headings = re.findall(r'(#{1,6} .*)', markdown_text)
    
    # Get first few paragraphs
    paragraphs = markdown_text.split('\n\n')
    important_paragraphs = paragraphs[:5]  # First 5 paragraphs
    
    # Combine headings and important paragraphs
    summary_parts = []
    
    # Add a summary header
    summary_parts.append("# Page Summary\n")
    
    # Add heading outline if available
    if headings:
        summary_parts.append("## Content Structure\n")
        for heading in headings[:10]:  # Limit to first 10 headings
            # Indent subheadings
            indentation = heading.count('#') - 1
            summary_parts.append(f"{'  ' * indentation}- {heading.strip('# ')}")
        summary_parts.append("\n")
    
    # Add content preview
    summary_parts.append("## Content Preview\n")
    for paragraph in important_paragraphs:
        # Skip headings and very short paragraphs in the preview
        if not paragraph.startswith('#') and len(paragraph) > 20:
            # Truncate long paragraphs
            if len(paragraph) > 200:
                paragraph = paragraph[:200] + "..."
            summary_parts.append(paragraph)
    
    # Join everything and truncate to max_length
    summary = "\n\n".join(summary_parts)
    return truncate_markdown(summary, max_length)


def format_for_agent(markdown_text: str, url: str, title: Optional[str] = None, max_length: int = 8000) -> str:
    """
    Format markdown content for the agent's response.
    
    Args:
        markdown_text: The markdown text to format
        url: The source URL
        title: The page title (optional)
        max_length: Maximum length of the formatted content
        
    Returns:
        str: The formatted content ready for the agent
    """
    if not markdown_text:
        return f"No content could be extracted from {url}"
    
    # Create a header with metadata
    header = f"# Content from {title or 'webpage'}\n"
    header += f"Source: {url}\n"
    
    # Truncate the content to fit within max_length including header
    truncated_content = truncate_markdown(markdown_text, max_length - len(header) - 100)
    
    # Combine header and content
    formatted = f"{header}\n{truncated_content}"
    
    return formatted 