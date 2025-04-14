"""
End-to-end tests for company risk analysis functionality.

This module tests the entire risk analysis pipeline from company detection
to data extraction to risk calculation and result formatting.
"""

import unittest
import os
import sys
import re
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent import WebCrawlerAgent
import risk_analyzer

class TestRiskAnalysis(unittest.TestCase):
    """Test the end-to-end risk analysis functionality."""
    
    def setUp(self):
        """Set up the test environment."""
        self.agent = WebCrawlerAgent()
        # Create a user ID for testing
        self.user_id = "test_user_123"
    
    @patch('risk_analyzer.check_risk_engine_health')
    @patch('simple_crawler.crawl_webpage')
    @patch('risk_analyzer.evaluate_company_risk')
    def test_analyze_apple_risk(self, mock_evaluate, mock_crawl, mock_health_check):
        """Test analyzing risk for Apple."""
        # Configure mocks
        mock_health_check.return_value = True  # Risk engine is healthy
        
        # Mock the crawler to return sample Apple financial data
        apple_data = """
        Apple Inc. (AAPL)
        Market Cap: $2.87 trillion
        Revenue: $383.29 billion
        Debt to Equity Ratio: 1.23
        Sector: Technology
        Net Profit: $96.99 billion
        """
        mock_crawl.return_value = apple_data
        
        # Mock the risk engine evaluation
        mock_evaluate.return_value = {
            "risk_score": 35.8,
            "risk_level": "Low Risk",
            "explanations": [
                "Debt-to-equity ratio is within healthy range",
                "Strong positive net profit indicates excellent financial health",
                "Low negative news coverage",
                "Technology sector has moderate baseline risk"
            ],
            "recommendations": [
                "Maintain current financial practices",
                "Annual risk reassessment recommended"
            ],
            "financial_data_extracted": {
                "debtToEquity": 1.23,
                "netProfit": 96990000000,
                "negativeNewsScore": 0.15,
                "latePaymentsRate": 0.03,
                "sector": "technology",
                "revenue": 383290000000,
                "marketCap": 2870000000000
            }
        }
        
        # 1. Test company detection in agent
        company_info = self.agent.detect_company_risk_query("analyze the risk for Apple")
        self.assertIsNotNone(company_info, "Should detect Apple as a company for risk analysis")
        self.assertEqual(company_info["company_name"], "Apple", "Should extract 'Apple' as the company name")
        
        # 2. Test analysis from URL
        result = risk_analyzer.analyze_company_from_url(
            "https://finance.yahoo.com/quote/AAPL", 
            "Apple",
            self.user_id
        )
        
        # Verify the crawler was called with the correct URL
        mock_crawl.assert_called_with("https://finance.yahoo.com/quote/AAPL")
        
        # Verify risk evaluation was called with extracted data
        self.assertIn("risk_analysis", result, "Result should contain risk analysis")
        
        # 3. Test formatting
        formatted_output = risk_analyzer.format_risk_analysis_for_display(result)
        
        # Check for key sections in the formatted output
        self.assertIn("## Risk Analysis for Apple", formatted_output)
        self.assertIn("### Financial Metrics", formatted_output)
        self.assertIn("**Revenue**:", formatted_output)
        self.assertIn("**Market Cap**:", formatted_output)
        self.assertIn("### Risk Factors", formatted_output)
        self.assertIn("### Recommendations", formatted_output)
        self.assertIn("### Data Sources", formatted_output)
        
        # Check if revenue is formatted properly (should be in billions)
        self.assertRegex(formatted_output, r"\*\*Revenue\*\*: \$\d+\.\d+ billion")
        
        # Check if market cap is formatted properly (should be in trillions)
        self.assertRegex(formatted_output, r"\*\*Market Cap\*\*: \$\d+\.\d+ trillion")
    
    @patch('agent.risk_analyzer')
    def test_process_risk_analysis_message(self, mock_risk_analyzer):
        """Test the entire message processing pipeline for risk analysis."""
        # Mock analyze_company_risk method to return a dummy result
        mock_result = {
            "formatted_analysis": "## Risk Analysis for Apple\n**Risk Score**: 35.8 / 100\n**Risk Level**: Low Risk",
            "raw_analysis": {}
        }
        mock_risk_analyzer.analyze_company_from_url.return_value = {"company": "Apple", "website": "https://www.apple.com"}
        mock_risk_analyzer.format_risk_analysis_for_display.return_value = mock_result["formatted_analysis"]
        mock_risk_analyzer.get_stock_symbol.return_value = "AAPL"
        
        # Process a message requesting Apple risk analysis
        response_tuple = self.agent.process_message(self.user_id, "What is the financial risk of Apple?")
        
        # Check type of response
        self.assertIsInstance(response_tuple, tuple, "Response should be a tuple")
        self.assertEqual(len(response_tuple), 2, "Response tuple should have 2 elements")
        
        # The first element should be the text response
        response_text = response_tuple[0]
        # The second element should be a list of crawled URLs
        crawled_urls = response_tuple[1]
        
        # Verify the risk analyzer was called
        self.assertTrue(mock_risk_analyzer.analyze_company_from_url.called, 
                       "Risk analyzer should be called for company risk query")
        
        # Verify that the response contains risk analysis information
        self.assertIn("Risk Analysis for Apple", response_text)
        
        # Verify that the URL appears in the crawled URLs list
        self.assertTrue(len(crawled_urls) > 0, "Should have at least one crawled URL")


# Run the tests if the file is executed directly
if __name__ == "__main__":
    unittest.main() 