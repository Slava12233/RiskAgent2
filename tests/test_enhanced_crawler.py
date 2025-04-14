"""
Comprehensive tests for the enhanced web crawler.

This module contains tests for the enhanced web crawler functionality,
including dynamic URL selection, parallel crawling, error handling,
and resource management.
"""

import os
import sys
import unittest
import asyncio
from typing import List
import time

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent import WebCrawlerAgent
from tools.web_crawler import (
    crawl_webpage_sync,
    crawl_multiple_webpages_sync,
    check_playwright_installed_sync
)


class TestDynamicUrlSelection(unittest.TestCase):
    """Test the dynamic URL selection functionality."""
    
    def setUp(self):
        """Set up the test environment."""
        self.agent = WebCrawlerAgent()
    
    def test_category_detection(self):
        """Test the category detection functionality."""
        # Test tech category
        query = "What are the benefits of using Python for web development?"
        category = self.agent._determine_query_category(query)
        self.assertEqual(category, "tech", "Failed to detect tech category")
        
        # Test product category
        query = "What are the best laptops for programming in 2023?"
        category = self.agent._determine_query_category(query)
        self.assertEqual(category, "product", "Failed to detect product category")
        
        # Test news category
        query = "What are the latest developments in the Middle East conflict?"
        category = self.agent._determine_query_category(query)
        self.assertEqual(category, "news", "Failed to detect news category")
        
        # Test travel category
        query = "What are the best tourist attractions in Rome?"
        category = self.agent._determine_query_category(query)
        self.assertEqual(category, "travel", "Failed to detect travel category")
        
        # Test health category
        query = "What are the symptoms of COVID-19?"
        category = self.agent._determine_query_category(query)
        self.assertEqual(category, "health", "Failed to detect health category")
    
    def test_topic_extraction(self):
        """Test the topic extraction functionality."""
        # Test normal query
        query = "What are the best programming languages to learn in 2023?"
        topics = self.agent._extract_topics_from_query(query)
        expected_topics = ["programming", "languages", "learn"]
        for topic in expected_topics:
            self.assertIn(topic, topics, f"Failed to extract topic: {topic}")
        
        # Test query with comparison
        query = "Compare Python and JavaScript for web development"
        topics = self.agent._extract_topics_from_query(query)
        expected_topics = ["python", "javascript", "web", "development"]
        for topic in expected_topics:
            self.assertIn(topic, topics, f"Failed to extract topic: {topic}")
        
        # Test query with named entities
        query = "What are the tourist attractions in New York City?"
        topics = self.agent._extract_topics_from_query(query)
        self.assertTrue(
            "new" in topics or "york" in topics or "city" in topics or "new york city" in topics,
            "Failed to extract named entity"
        )
    
    def test_website_selection(self):
        """Test the website selection based on category and topics."""
        # Test tech category
        websites = self.agent._get_websites_by_category("tech", "python programming", ["python", "programming"])
        
        # Should include Python-related sites
        python_sites = [site for site in websites if "python" in site.lower()]
        self.assertTrue(len(python_sites) > 0, "Failed to find Python-related websites")
        
        # Test product category
        websites = self.agent._get_websites_by_category("product", "best laptops", ["laptops", "best"])
        
        # Should include laptop-related sites
        laptop_sites = [site for site in websites if "laptop" in site.lower()]
        self.assertTrue(len(laptop_sites) > 0, "Failed to find laptop-related websites")
        
        # Test news category for Middle East
        websites = self.agent._get_websites_by_category("news", "middle east conflict", ["middle", "east", "conflict"])
        
        # Should include Middle East news sites
        me_sites = [site for site in websites if "middle" in site.lower() or "east" in site.lower()]
        self.assertTrue(len(me_sites) > 0, "Failed to find Middle East news websites")
        
        # Test travel category
        websites = self.agent._get_websites_by_category("travel", "rome italy", ["rome", "italy"])
        
        # Should include Rome or Italy sites
        rome_sites = [site for site in websites if "rome" in site.lower() or "italy" in site.lower()]
        self.assertTrue(len(rome_sites) > 0, "Failed to find Rome-related websites")
    
    def test_find_relevant_websites(self):
        """Test the find_relevant_websites method."""
        # Test for tech query
        websites = self.agent.find_relevant_websites("How to use Python for web development")
        self.assertTrue(len(websites) > 0, "Failed to find websites for tech query")
        
        # Test for product query
        websites = self.agent.find_relevant_websites("Best laptops for programming")
        self.assertTrue(len(websites) > 0, "Failed to find websites for product query")
        
        # Test for news query
        websites = self.agent.find_relevant_websites("Latest news on Middle East")
        self.assertTrue(len(websites) > 0, "Failed to find websites for news query")


class TestParallelCrawling(unittest.TestCase):
    """Test the parallel crawling functionality."""
    
    @unittest.skipIf(not check_playwright_installed_sync(), "Playwright not installed")
    def test_multiple_urls_crawling(self):
        """Test crawling multiple URLs in parallel."""
        # Simple, reliable URLs for testing
        urls = [
            "https://example.com",
            "https://www.python.org",
            "https://playwright.dev"
        ]
        
        # Time the parallel crawling
        start_time = time.time()
        result = crawl_multiple_webpages_sync(urls, summary=True)
        parallel_time = time.time() - start_time
        
        # Verify the result contains content from each URL
        for url in urls:
            self.assertIn(url, result, f"Result does not contain content from {url}")
        
        # Now crawl them sequentially and compare time
        start_time = time.time()
        sequential_results = []
        for url in urls:
            sequential_results.append(crawl_webpage_sync(url, summary=True))
        sequential_time = time.time() - start_time
        
        # The parallel crawling should generally be faster for multiple URLs
        # But we can't guarantee it, so just check that it worked
        print(f"Parallel crawling time: {parallel_time:.2f}s, Sequential crawling time: {sequential_time:.2f}s")
        
        # Check that we got content from each URL
        self.assertIn("Example Domain", result, "Failed to get content from example.com")
        self.assertIn("Python", result, "Failed to get content from python.org")
        self.assertIn("Playwright", result, "Failed to get content from playwright.dev")
    
    @unittest.skipIf(not check_playwright_installed_sync(), "Playwright not installed")
    def test_resource_management(self):
        """Test resource management with many concurrent requests."""
        # Create a larger number of URLs
        urls = ["https://example.com"] * 10
        
        # This should not cause resource issues due to semaphore limiting concurrency
        try:
            result = crawl_multiple_webpages_sync(urls, summary=True)
            # If we get here without errors, the test passes
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Resource management failed with error: {str(e)}")


class TestErrorHandling(unittest.TestCase):
    """Test the error handling functionality."""
    
    @unittest.skipIf(not check_playwright_installed_sync(), "Playwright not installed")
    def test_invalid_url(self):
        """Test handling of invalid URLs."""
        # Test with an invalid URL
        invalid_url = "https://thisisanonexistentwebsitethatdoesnotexist123456.com"
        
        # This should not raise an exception
        try:
            result = crawl_webpage_sync(invalid_url)
            # Check that the result contains an error message
            self.assertIn("Error", result, "Invalid URL error not handled properly")
        except Exception as e:
            self.fail(f"Invalid URL test failed with error: {str(e)}")
    
    @unittest.skipIf(not check_playwright_installed_sync(), "Playwright not installed")
    def test_timeout_handling(self):
        """Test handling of timeout errors."""
        # Use a URL known to be slow or timeout-prone
        slow_url = "https://httpbin.org/delay/10"  # This will delay for 10 seconds
        
        # Should handle the timeout gracefully
        try:
            result = crawl_webpage_sync(slow_url)
            # Either it succeeded (on a fast connection) or handled the timeout
            if "Error" in result:
                self.assertIn("timeout", result.lower(), "Timeout error not handled properly")
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Timeout handling test failed with error: {str(e)}")
    
    @unittest.skipIf(not check_playwright_installed_sync(), "Playwright not installed")
    def test_mixed_valid_invalid_urls(self):
        """Test crawling a mix of valid and invalid URLs."""
        # Mix of valid and invalid URLs
        urls = [
            "https://example.com",
            "https://thisisanonexistentwebsitethatdoesnotexist123456.com",
            "https://www.python.org"
        ]
        
        # This should not raise an exception
        try:
            result = crawl_multiple_webpages_sync(urls, summary=True)
            
            # Check that valid URLs were crawled
            self.assertIn("Example Domain", result, "Failed to get content from example.com")
            self.assertIn("Python", result, "Failed to get content from python.org")
            
            # Check that invalid URL error was handled
            self.assertIn("Error", result, "Invalid URL error not handled properly")
            
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Mixed URL test failed with error: {str(e)}")


class TestContentExtraction(unittest.TestCase):
    """Test the content extraction functionality."""
    
    @unittest.skipIf(not check_playwright_installed_sync(), "Playwright not installed")
    def test_extract_content_from_different_sites(self):
        """Test extracting content from different types of websites."""
        # Test a simple static site
        result = crawl_webpage_sync("https://example.com", summary=True)
        self.assertIn("Example Domain", result, "Failed to extract content from example.com")
        
        # Test a more complex site with dynamic content
        result = crawl_webpage_sync("https://www.python.org", summary=True)
        self.assertIn("Python", result, "Failed to extract content from python.org")
        
        # Test the documentation site
        result = crawl_webpage_sync("https://playwright.dev", summary=True)
        self.assertIn("Playwright", result, "Failed to extract content from playwright.dev")


def run_tests():
    """Run the tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDynamicUrlSelection))
    suite.addTests(loader.loadTestsFromTestCase(TestParallelCrawling))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestContentExtraction))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_tests() 