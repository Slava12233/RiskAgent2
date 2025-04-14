#!/usr/bin/env python
"""
Risk Engine API Demo Client

This script demonstrates the Risk Engine API with realistic
examples from various industries.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import argparse

# Configuration
API_BASE_URL = "http://localhost:8000/api"

def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80)

def print_json(data: Dict[str, Any]) -> None:
    """Print JSON data in a formatted way."""
    print(json.dumps(data, indent=2))
    print("-" * 80)

def check_health() -> bool:
    """Check if the API is healthy and running."""
    print_header("CHECKING API HEALTH")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        data = response.json()
        
        print_json(data)
        
        return data.get("status") == "healthy" and data.get("database") == "connected"
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def evaluate_company(company_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Send a risk evaluation request for a company.
    
    Args:
        company_data: Company data including financial metrics
        
    Returns:
        Response data from the API or None if an error occurred
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/evaluate",
            json=company_data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def get_evaluation(evaluation_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific evaluation by ID.
    
    Args:
        evaluation_id: The ID of the evaluation to retrieve
        
    Returns:
        Response data from the API or None if an error occurred
    """
    try:
        response = requests.get(f"{API_BASE_URL}/evaluations/{evaluation_id}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def get_company_evaluations(company_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve all evaluations for a company.
    
    Args:
        company_name: The name of the company
        
    Returns:
        List of evaluations or None if an error occurred
    """
    try:
        # URL encode the company name
        encoded_name = requests.utils.quote(company_name)
        response = requests.get(f"{API_BASE_URL}/evaluations/company/{encoded_name}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def run_demo_scenarios() -> None:
    """Run multiple realistic demo scenarios across different industries."""
    # First check if API is healthy
    if not check_health():
        print("API is not healthy. Please ensure the server is running.")
        return
    
    # Demo scenarios
    run_technology_startup_scenario()
    run_established_tech_company_scenario()
    run_manufacturing_company_scenario()
    run_retail_business_scenario()
    run_healthcare_company_scenario()
    run_financial_services_scenario()
    
    # Demonstrate retrieving company evaluations
    print_header("RETRIEVING EVALUATIONS FOR TECH INNOVATIONS INC")
    evals = get_company_evaluations("Tech Innovations Inc")
    if evals:
        print(f"Found {len(evals)} evaluations:")
        for i, evaluation in enumerate(evals, 1):
            print(f"\nEvaluation #{i}:")
            print_json(evaluation)

def run_technology_startup_scenario() -> None:
    """Technology Startup Scenario - High Risk."""
    print_header("TECHNOLOGY STARTUP SCENARIO")
    
    company_data = {
        "user_id": "analyst001",
        "companyName": "NextGen AI Startup",
        "debtToEquity": 3.8,
        "netProfit": -850000,
        "negativeNewsScore": 0.25,
        "latePaymentsRate": 0.22,
        "sector": "technology"
    }
    
    print("Technology Startup Company Profile:")
    print("- Recently founded AI company with innovative technology")
    print("- High debt from initial funding rounds")
    print("- Currently operating at a loss while developing products")
    print("- Some late payments to suppliers")
    print("- Relatively positive media coverage")
    print("\nSubmitting for evaluation...")
    
    result = evaluate_company(company_data)
    if result:
        print("\nRisk Evaluation Result:")
        print_json(result)

def run_established_tech_company_scenario() -> None:
    """Established Technology Company Scenario - Low Risk."""
    print_header("ESTABLISHED TECHNOLOGY COMPANY SCENARIO")
    
    company_data = {
        "user_id": "analyst002",
        "companyName": "Tech Innovations Inc",
        "debtToEquity": 0.9,
        "netProfit": 12500000,
        "negativeNewsScore": 0.15,
        "latePaymentsRate": 0.03,
        "sector": "technology"
    }
    
    print("Established Technology Company Profile:")
    print("- Market leader with 15+ years of operation")
    print("- Strong balance sheet with low debt")
    print("- Consistent profitability")
    print("- Excellent payment history")
    print("- Positive media presence")
    print("\nSubmitting for evaluation...")
    
    result = evaluate_company(company_data)
    if result:
        print("\nRisk Evaluation Result:")
        print_json(result)
        
        # Retrieve detailed evaluation
        if result.get("evaluation_id"):
            print("\nRetrieving detailed evaluation...")
            detailed = get_evaluation(result["evaluation_id"])
            if detailed:
                print("\nDetailed Evaluation Record:")
                print_json(detailed)

def run_manufacturing_company_scenario() -> None:
    """Manufacturing Company Scenario - Medium Risk."""
    print_header("MANUFACTURING COMPANY SCENARIO")
    
    company_data = {
        "user_id": "analyst003",
        "companyName": "Global Manufacturing Solutions",
        "debtToEquity": 2.2,
        "netProfit": 3200000,
        "negativeNewsScore": 0.45,
        "latePaymentsRate": 0.12,
        "sector": "manufacturing"
    }
    
    print("Manufacturing Company Profile:")
    print("- Established manufacturing firm with global operations")
    print("- Moderate debt from recent facility expansions")
    print("- Profitable but with fluctuating margins")
    print("- Some supply chain issues causing payment delays")
    print("- Negative press regarding environmental compliance")
    print("\nSubmitting for evaluation...")
    
    result = evaluate_company(company_data)
    if result:
        print("\nRisk Evaluation Result:")
        print_json(result)

def run_retail_business_scenario() -> None:
    """Retail Business Scenario - High Risk."""
    print_header("RETAIL BUSINESS SCENARIO")
    
    company_data = {
        "user_id": "analyst004",
        "companyName": "Urban Retail Outlets",
        "debtToEquity": 3.5,
        "netProfit": -1200000,
        "negativeNewsScore": 0.65,
        "latePaymentsRate": 0.28,
        "sector": "retail"
    }
    
    print("Retail Business Profile:")
    print("- Chain of urban retail stores")
    print("- High debt from recent acquisitions")
    print("- Operating at a loss due to market pressures")
    print("- Consistent late payments to suppliers")
    print("- Negative press about store closures and staff layoffs")
    print("\nSubmitting for evaluation...")
    
    result = evaluate_company(company_data)
    if result:
        print("\nRisk Evaluation Result:")
        print_json(result)

def run_healthcare_company_scenario() -> None:
    """Healthcare Company Scenario - Low Risk."""
    print_header("HEALTHCARE COMPANY SCENARIO")
    
    company_data = {
        "user_id": "analyst005",
        "companyName": "MediCore Health Services",
        "debtToEquity": 1.1,
        "netProfit": 7800000,
        "negativeNewsScore": 0.12,
        "latePaymentsRate": 0.04,
        "sector": "healthcare"
    }
    
    print("Healthcare Company Profile:")
    print("- Established healthcare services provider")
    print("- Low debt-to-equity ratio")
    print("- Strong and consistent profitability")
    print("- Excellent payment history")
    print("- Positive public reputation")
    print("\nSubmitting for evaluation...")
    
    result = evaluate_company(company_data)
    if result:
        print("\nRisk Evaluation Result:")
        print_json(result)

def run_financial_services_scenario() -> None:
    """Financial Services Scenario - Medium to High Risk."""
    print_header("FINANCIAL SERVICES SCENARIO")
    
    company_data = {
        "user_id": "analyst006",
        "companyName": "Nexus Financial Holdings",
        "debtToEquity": 2.7,
        "netProfit": 1500000,
        "negativeNewsScore": 0.55,
        "latePaymentsRate": 0.09,
        "sector": "finance"
    }
    
    print("Financial Services Company Profile:")
    print("- Mid-sized financial services firm")
    print("- Elevated debt levels")
    print("- Profitable but below industry average")
    print("- Some payment delays to service providers")
    print("- Negative press regarding regulatory compliance")
    print("\nSubmitting for evaluation...")
    
    result = evaluate_company(company_data)
    if result:
        print("\nRisk Evaluation Result:")
        print_json(result)

def main() -> None:
    """Main entry point for the demo client."""
    parser = argparse.ArgumentParser(description="Risk Engine API Demo Client")
    parser.add_argument("-s", "--scenario", type=str, help="Run a specific scenario: tech-startup, established-tech, manufacturing, retail, healthcare, finance, or all")
    
    args = parser.parse_args()
    
    if args.scenario:
        if args.scenario == "tech-startup":
            run_technology_startup_scenario()
        elif args.scenario == "established-tech":
            run_established_tech_company_scenario()
        elif args.scenario == "manufacturing":
            run_manufacturing_company_scenario()
        elif args.scenario == "retail":
            run_retail_business_scenario()
        elif args.scenario == "healthcare":
            run_healthcare_company_scenario()
        elif args.scenario == "finance":
            run_financial_services_scenario()
        elif args.scenario == "all":
            run_demo_scenarios()
        else:
            print(f"Unknown scenario: {args.scenario}")
            print("Available scenarios: tech-startup, established-tech, manufacturing, retail, healthcare, finance, all")
    else:
        # Run all scenarios
        run_demo_scenarios()

if __name__ == "__main__":
    print_header("RISK ENGINE API DEMO")
    print("This script demonstrates how to use the Risk Engine API with realistic examples.")
    print("Make sure the Risk Engine server is running at http://localhost:8000")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nDemo terminated by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    
    print("\nDemo completed.") 