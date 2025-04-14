"""
Test script for basic crawling commands.

This script tests the agent's ability to understand and process basic scraping
commands like "scrape Tesla website", "crawl Apple", etc.
"""

import sys
import os
import time
from termcolor import colored

# Add parent directory to path to import agent
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the WebCrawlerAgent class
from agent import WebCrawlerAgent, get_agent

def test_command(agent, command, expected_behavior="detect URL"):
    """
    Test if the agent correctly processes a basic command.
    
    Args:
        agent: The WebCrawlerAgent instance
        command: The command to test
        expected_behavior: What we expect the agent to do
    
    Returns:
        bool: True if test passed, False otherwise
    """
    print(colored(f"\nTesting command: '{command}'", "cyan"))
    print(f"Expected behavior: {expected_behavior}")
    
    # First, test URL detection directly
    url = agent.detect_url_in_message(command)
    
    if expected_behavior == "detect URL":
        if url:
            print(colored(f"✓ URL detected: {url}", "green"))
            return True
        else:
            print(colored("✗ Failed to detect URL", "red"))
            return False
    elif expected_behavior == "no URL":
        if not url:
            print(colored("✓ Correctly did not detect URL", "green"))
            return True
        else:
            print(colored(f"✗ Incorrectly detected URL: {url}", "red"))
            return False
    
    return False

def test_basic_commands():
    """Run tests for basic web crawling commands."""
    print(colored("\n=== TESTING BASIC WEB CRAWLING COMMANDS ===", "yellow"))
    
    # Create agent
    try:
        agent = get_agent()
        print(colored("Agent created successfully", "green"))
    except Exception as e:
        print(colored(f"Failed to create agent: {str(e)}", "red"))
        return
    
    # Test cases
    commands = [
        # Direct commands
        ("scrape Tesla website", "detect URL"),
        ("crawl Apple", "detect URL"),
        ("go to Microsoft website", "detect URL"),
        ("visit Amazon", "detect URL"),
        ("browse Twitter", "detect URL"),
        
        # Variations with 'the'
        ("scrape the Tesla website", "detect URL"),
        ("check the Apple site", "detect URL"),
        
        # Variations with prepositions
        ("get information from Facebook", "detect URL"),
        ("read content about Google", "detect URL"),
        
        # Multi-word companies
        ("crawl New York Times", "detect URL"),
        ("visit Wall Street Journal", "detect URL"),
        ("analyze Coca Cola website", "detect URL"),
        
        # Non-standard names
        ("scrape CNN", "detect URL"),
        ("check BBC news", "detect URL"),
        ("visit NYT website", "detect URL"),
        
        # Less common companies (should auto-construct URLs)
        ("scrape Spotify website", "detect URL"),
        ("crawl Uber", "detect URL"),
        ("go to Airbnb website", "detect URL"),
        
        # Domain suffix tests
        ("visit python.org", "detect URL"),
        ("check github.com", "detect URL"),
        
        # Edge cases
        ("what is the weather today", "no URL"),
        ("tell me a joke", "no URL"),
        ("help me with my homework", "no URL"),
        ("can you talk about Tesla cars?", "no URL"),  # Just talking about Tesla, not asking to crawl
        ("the blog post on Microsoft AI", "no URL"),   # Not a direct scrape command
        
        # Commands with other information
        ("scrape Apple website for information about new iPhones", "detect URL"),
        ("visit Tesla and tell me about their electric vehicles", "detect URL")
    ]
    
    # Run tests
    results = []
    for command, expected in commands:
        result = test_command(agent, command, expected)
        results.append(result)
    
    # Print summary
    print(colored("\n=== TEST SUMMARY ===", "yellow"))
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} tests ({passed/total*100:.1f}%)")
    
    if passed == total:
        print(colored("All tests passed!", "green"))
    else:
        print(colored(f"Failed {total-passed} tests", "red"))

if __name__ == "__main__":
    test_basic_commands() 