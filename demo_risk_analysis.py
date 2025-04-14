#!/usr/bin/env python
"""
Risk Analysis Demonstration Script

This script demonstrates the enhanced company risk analysis feature by analyzing
Apple's risk profile and displaying the formatted results.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import agent and risk_analyzer
try:
    from agent import get_agent
    from risk_analyzer import analyze_company_from_url, format_risk_analysis_for_display
except ImportError as e:
    print(f"Error importing modules: {str(e)}")
    print("Please run this script from the project root directory.")
    sys.exit(1)

def demo_risk_analysis():
    """Demonstrate the enhanced risk analysis feature."""
    print("=" * 80)
    print("RISK ANALYSIS DEMONSTRATION".center(80))
    print("=" * 80)
    
    # Create a user ID for the demo
    user_id = "demo_user_001"
    
    # Get the agent instance
    agent = get_agent()
    
    # 1. Test company detection in agent
    print("\nTEST 1: Company Detection")
    print("-" * 80)
    
    test_messages = [
        "analyze the risk for Apple",
        "what is the financial risk of Microsoft?",
        "perform a risk assessment for Tesla",
        "evaluate Amazon's company risk",
        "analyze google's financial health"
    ]
    
    for message in test_messages:
        print(f"Message: '{message}'")
        company_info = agent.detect_company_risk_query(message)
        if company_info:
            print(f"✅ Detected company: {company_info['company_name']}")
            print(f"URL: {company_info['url']}")
        else:
            print("❌ No company detected")
        print()
    
    # 2. Demonstrate full risk analysis for Apple
    print("\nTEST 2: Complete Risk Analysis for Apple")
    print("-" * 80)
    
    print("Processing message: 'analyze the risk for Apple'")
    response, urls = agent.process_message(user_id, "analyze the risk for Apple")
    
    print("\nCRAWLED URLS:")
    for url in urls:
        print(f"- {url}")
    
    print("\nANALYSIS RESULT:")
    print(response)
    
    # 3. Demonstrate manual analysis with the risk_analyzer module
    print("\nTEST 3: Manual Analysis with Risk Analyzer")
    print("-" * 80)
    
    # Use Yahoo Finance for better financial data
    url = "https://finance.yahoo.com/quote/AAPL"
    company_name = "Apple"
    
    print(f"Analyzing {company_name} from {url}...")
    try:
        result = analyze_company_from_url(url, company_name, user_id)
        if "error" in result:
            print(f"Error: {result['error']}")
            print(f"Message: {result.get('message', 'No details available')}")
        else:
            # Format and display the result
            formatted_result = format_risk_analysis_for_display(result)
            print(formatted_result)
    except Exception as e:
        print(f"Analysis failed: {str(e)}")
    
    print("\nDemonstration complete!")
    
if __name__ == "__main__":
    demo_risk_analysis() 