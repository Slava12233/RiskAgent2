#!/usr/bin/env python3
"""
End-to-end test for the web crawler conversational agent.

This script simulates conversations with the agent on 3 different topics
and verifies that the responses contain relevant information.
"""

import os
import sys
import time
import json
import unittest
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("e2e_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("e2e_test")

# Add parent directory to path to import agent
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the agent with error handling
try:
    from agent import get_agent, WebCrawlerAgent
except ImportError as e:
    logger.error(f"Failed to import agent: {e}")
    sys.exit(1)

# Try importing the simple crawler if available
try:
    import simple_crawler
    SIMPLE_CRAWLER_AVAILABLE = True
    logger.info("Simple crawler is available for testing")
except ImportError:
    SIMPLE_CRAWLER_AVAILABLE = False
    logger.warning("Simple crawler is not available")

class WebCrawlerAgentE2ETest(unittest.TestCase):
    """Test the WebCrawlerAgent with real conversations and web crawling."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are used for all tests."""
        logger.info("Setting up E2E test suite")
        try:
            # Get the agent
            cls.agent = get_agent()
            logger.info("Agent initialized successfully")
            
            # Create a unique user ID for testing
            cls.test_user_id = f"test_user_{int(time.time())}"
            logger.info(f"Test user ID: {cls.test_user_id}")
        except Exception as e:
            logger.error(f"Error in test setup: {e}")
            raise
    
    def setUp(self):
        """Set up before each test."""
        logger.info(f"Starting new test: {self._testMethodName}")
    
    def test_news_topic(self):
        """Test conversation about news on Israel."""
        logger.info("Testing news topic about Israel")
        
        # Define test conversation
        messages = [
            "I need information about the latest developments in Israel",
            "What are the recent events in the Israel-Hamas conflict?",
            "Can you summarize the humanitarian situation in Gaza?"
        ]
        
        # Process each message and verify responses
        self._run_conversation_test(
            topic="Israel News",
            messages=messages,
            required_keywords=["Israel", "Gaza", "conflict", "humanitarian"]
        )
    
    def test_tech_comparison(self):
        """Test conversation about programming language comparison."""
        logger.info("Testing tech comparison topic")
        
        # Define test conversation
        messages = [
            "Compare Python, JavaScript, and Rust programming languages",
            "Which one is best for web development?",
            "What are the performance differences between them?"
        ]
        
        # Process each message and verify responses
        self._run_conversation_test(
            topic="Programming Language Comparison",
            messages=messages,
            required_keywords=["Python", "JavaScript", "Rust", "performance", "development"]
        )
    
    def test_product_reviews(self):
        """Test conversation about product reviews for laptops."""
        logger.info("Testing product reviews topic")
        
        # Define test conversation
        messages = [
            "What are the best laptops for programming in 2023?",
            "Compare Dell XPS and MacBook Pro",
            "Which one has better battery life?"
        ]
        
        # Process each message and verify responses
        self._run_conversation_test(
            topic="Laptop Reviews",
            messages=messages,
            required_keywords=["laptop", "battery", "programming", "Dell", "MacBook"]
        )
    
    def _run_conversation_test(self, topic: str, messages: List[str], required_keywords: List[str]):
        """
        Run a multi-message conversation test and verify responses.
        
        Args:
            topic: The conversation topic for logging
            messages: List of user messages to send
            required_keywords: Keywords that should appear in at least one response
        """
        logger.info(f"Running conversation test for topic: {topic}")
        
        responses = []
        keywords_found = {keyword: False for keyword in required_keywords}
        
        # Process each message in the conversation
        for i, message in enumerate(messages):
            logger.info(f"Processing message {i+1}/{len(messages)}: {message}")
            
            try:
                # Time the response
                start_time = time.time()
                response = self.agent.process_message(self.test_user_id, message)
                end_time = time.time()
                
                # Log the response time
                response_time = end_time - start_time
                logger.info(f"Response time: {response_time:.2f} seconds")
                
                # Verify we got a response
                self.assertIsNotNone(response, f"No response received for message: {message}")
                self.assertIsInstance(response, str, f"Response should be a string, got {type(response)}")
                self.assertTrue(len(response) > 0, f"Response should not be empty for message: {message}")
                
                # Check for keywords in the response
                for keyword in required_keywords:
                    if keyword.lower() in response.lower():
                        keywords_found[keyword] = True
                
                # Log a summary of the response (truncated)
                max_response_log_length = 500
                truncated_response = response
                if len(response) > max_response_log_length:
                    truncated_response = response[:max_response_log_length] + "... [truncated]"
                logger.info(f"Response: {truncated_response}")
                
                # Save the response for later analysis
                responses.append({
                    "message": message,
                    "response": response,
                    "response_time": response_time
                })
                
                # Add a small delay between messages to prevent rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                self.fail(f"Exception while processing message '{message}': {e}")
        
        # Verify that we found required keywords in at least one response
        missing_keywords = [k for k, found in keywords_found.items() if not found]
        self.assertEqual(
            len(missing_keywords), 0, 
            f"Missing required keywords in conversation responses: {missing_keywords}"
        )
        
        # Save the conversation to a file for later analysis
        self._save_conversation(topic, messages, responses)
    
    def _save_conversation(self, topic: str, messages: List[str], responses: List[Dict[str, Any]]):
        """Save the conversation to a JSON file for later analysis."""
        filename = f"test_conversation_{topic.lower().replace(' ', '_')}_{int(time.time())}.json"
        
        data = {
            "topic": topic,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "conversation": []
        }
        
        # Build the conversation structure
        for i, response_data in enumerate(responses):
            data["conversation"].append({
                "turn": i + 1,
                "user_message": response_data["message"],
                "agent_response": response_data["response"],
                "response_time_seconds": response_data["response_time"]
            })
        
        # Save to file
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved conversation to {filename}")
    
    def tearDown(self):
        """Clean up after each test."""
        logger.info(f"Finished test: {self._testMethodName}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        logger.info("Tearing down E2E test suite")

def main():
    """Run the E2E tests."""
    logger.info("Starting E2E test")
    
    # Run the tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    logger.info("Finished E2E test")

if __name__ == "__main__":
    main() 