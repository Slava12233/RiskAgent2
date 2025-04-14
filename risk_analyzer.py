"""
Risk Analyzer Tool.

This module connects the web crawler with the risk engine API to perform
company risk analysis based on data extracted from their websites.
"""

import requests
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("risk_analyzer")

# Configuration for Risk Engine API
RISK_ENGINE_API_URL = "http://localhost:8000/api"

def check_risk_engine_health() -> bool:
    """
    Check if the Risk Engine API is available and healthy.
    
    Returns:
        bool: True if API is healthy, False otherwise
    """
    try:
        response = requests.get(f"{RISK_ENGINE_API_URL}/health")
        data = response.json()
        
        return data.get("status") == "healthy" and data.get("database") == "connected"
    except Exception as e:
        logger.error(f"Error checking Risk Engine health: {str(e)}")
        return False

def extract_financial_data(content: str) -> Dict[str, Any]:
    """
    Extract financial data from website content.
    
    Args:
        content: The HTML or text content from a company website
        
    Returns:
        Dict with extracted financial parameters
    """
    # Initialize with default values
    financial_data = {
        "debtToEquity": 2.0,  # Moderate risk by default
        "netProfit": 0,       # Break-even by default
        "negativeNewsScore": 0.3,  # Moderate news score by default
        "latePaymentsRate": 0.1,  # Moderate late payments by default
        "sector": "general",   # Default sector
        "revenue": 0,         # Default revenue
        "marketCap": 0        # Default market cap
    }
    
    # Extract Debt to Equity Ratio
    debt_equity_patterns = [
        r'debt[\s-]to[\s-]equity.*?(\d+\.\d+)',
        r'debt ratio.*?(\d+\.\d+)',
        r'leverage ratio.*?(\d+\.\d+)'
    ]
    for pattern in debt_equity_patterns:
        matches = re.search(pattern, content.lower())
        if matches:
            try:
                financial_data["debtToEquity"] = float(matches.group(1))
                break
            except ValueError:
                pass
    
    # Extract Net Profit
    profit_patterns = [
        r'net profit.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*million|\s*M)?',
        r'profit.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*million|\s*M)?',
        r'earnings.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*million|\s*M)?'
    ]
    for pattern in profit_patterns:
        matches = re.search(pattern, content.lower())
        if matches:
            try:
                profit_str = matches.group(1).replace(',', '')
                profit = float(profit_str)
                # If the number is likely in millions (context suggests)
                if 'million' in content[matches.start():matches.start() + 100] or 'M' in content[matches.start():matches.start() + 100]:
                    profit *= 1000000
                financial_data["netProfit"] = profit
                break
            except ValueError:
                pass
    
    # Extract Revenue figures
    revenue_patterns = [
        r'revenue.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*billion|\s*B|\s*million|\s*M)?',
        r'sales.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*billion|\s*B|\s*million|\s*M)?',
        r'turnover.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*billion|\s*B|\s*million|\s*M)?'
    ]
    for pattern in revenue_patterns:
        matches = re.search(pattern, content.lower())
        if matches:
            try:
                revenue_str = matches.group(1).replace(',', '')
                revenue = float(revenue_str)
                # Check for scale indicators
                context = content[matches.start():matches.start() + 100].lower()
                if 'billion' in context or 'B' in context:
                    revenue *= 1000000000
                elif 'million' in context or 'M' in context:
                    revenue *= 1000000
                financial_data["revenue"] = revenue
                break
            except ValueError:
                pass
                
    # Extract market cap information
    market_cap_patterns = [
        r'market cap.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*trillion|\s*T|\s*billion|\s*B|\s*million|\s*M)?',
        r'market capitalization.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*trillion|\s*T|\s*billion|\s*B|\s*million|\s*M)?',
        r'valuation.*?\$?(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*trillion|\s*T|\s*billion|\s*B|\s*million|\s*M)?'
    ]
    for pattern in market_cap_patterns:
        matches = re.search(pattern, content.lower())
        if matches:
            try:
                cap_str = matches.group(1).replace(',', '')
                cap = float(cap_str)
                # Check for scale indicators
                context = content[matches.start():matches.start() + 100].lower()
                if 'trillion' in context or 'T' in context:
                    cap *= 1000000000000
                elif 'billion' in context or 'B' in context:
                    cap *= 1000000000
                elif 'million' in context or 'M' in context:
                    cap *= 1000000
                financial_data["marketCap"] = cap
                break
            except ValueError:
                pass
    
    # Determine sector based on keywords
    sector_keywords = {
        "technology": ["tech", "software", "hardware", "it ", "digital", "computer", "ai ", "artificial intelligence", "cloud", "saas"],
        "finance": ["finance", "banking", "investment", "insurance", "fintech", "bank", "capital", "financial services"],
        "healthcare": ["health", "medical", "pharma", "biotech", "medicine", "healthcare", "hospital", "clinic"],
        "retail": ["retail", "shop", "store", "e-commerce", "consumer goods", "mall", "supermarket"],
        "manufacturing": ["manufacturing", "factory", "production", "industrial", "assembly", "machinery"],
        "energy": ["energy", "power", "utility", "electricity", "gas", "oil", "renewable", "solar", "wind"],
        "telecommunications": ["telecom", "communication", "network", "wireless", "broadband", "5g", "internet service"]
    }
    
    # Count occurrences of sector-related terms
    sector_counts = {sector: 0 for sector in sector_keywords}
    content_lower = content.lower()
    
    for sector, keywords in sector_keywords.items():
        for keyword in keywords:
            sector_counts[sector] += content_lower.count(keyword)
    
    # Determine most likely sector
    if max(sector_counts.values()) > 0:
        financial_data["sector"] = max(sector_counts.items(), key=lambda x: x[1])[0]
    
    # Estimate negative news score
    negative_terms = ["issue", "problem", "concern", "risk", "threat", "negative", "decline", 
                     "loss", "debt", "lawsuit", "litigation", "fine", "penalty", "investigation",
                     "scandal", "breach", "attack", "hack", "layoff", "downsize", "cut", "close"]
    
    negative_count = sum(content_lower.count(term) for term in negative_terms)
    total_words = len(content_lower.split())
    
    # Calculate negative news score (capped at 1.0)
    if total_words > 0:
        neg_score = min(1.0, (negative_count / total_words) * 20)  # Multiply by 20 to scale up
        financial_data["negativeNewsScore"] = round(neg_score, 2)
    
    logger.info(f"Extracted financial data: {json.dumps(financial_data)}")
    return financial_data

def evaluate_company_risk(company_name: str, website_content: str, user_id: str = "web_crawler_agent") -> Optional[Dict[str, Any]]:
    """
    Evaluate the risk level of a company based on its website content.
    
    Args:
        company_name: Name of the company
        website_content: Content scraped from the company website
        user_id: Identifier for the user making the request
        
    Returns:
        Dict with risk evaluation results or None if evaluation failed
    """
    if not check_risk_engine_health():
        logger.error("Risk Engine API is not available or healthy")
        return {
            "error": "Risk Engine API is not available",
            "message": "The risk engine service is currently unavailable. Please try again later."
        }
    
    # Extract financial data from website content
    financial_data = extract_financial_data(website_content)
    
    # Prepare request data
    request_data = {
        "user_id": user_id,
        "companyName": company_name,
        **financial_data
    }
    
    # Send request to Risk Engine API
    try:
        logger.info(f"Sending risk evaluation request for company: {company_name}")
        response = requests.post(
            f"{RISK_ENGINE_API_URL}/evaluate",
            json=request_data
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Received risk evaluation for {company_name}: Risk level: {result.get('recommendation')}, Score: {result.get('score')}")
            return {
                "company_name": company_name,
                "risk_score": result.get("score"),
                "risk_level": result.get("recommendation"),
                "explanations": result.get("explanations"),
                "recommendations": result.get("recommendations"),
                "evaluation_id": result.get("evaluation_id"),
                "financial_data_extracted": financial_data
            }
        else:
            logger.error(f"Error: API returned status code {response.status_code}")
            logger.error(response.text)
            return {
                "error": f"API Error (Status {response.status_code})",
                "message": f"The risk engine returned an error: {response.text}"
            }
    except Exception as e:
        logger.error(f"Error evaluating company risk: {str(e)}")
        return {
            "error": "Evaluation Error",
            "message": f"An error occurred while evaluating company risk: {str(e)}"
        }

def analyze_company_from_url(url: str, company_name: Optional[str] = None, user_id: str = "web_crawler_agent") -> Dict[str, Any]:
    """
    Analyze a company's risk based on its website URL.
    
    This function uses the web crawler to extract content from the company website,
    then passes that content to the risk engine for analysis.
    
    Args:
        url: The URL of the company website
        company_name: Optional company name (extracted from URL if not provided)
        user_id: Identifier for the user making the request
        
    Returns:
        Dict with risk evaluation results or error information
    """
    # Check if Risk Engine is available
    if not check_risk_engine_health():
        return {
            "error": "Risk Engine Unavailable",
            "message": "The risk engine service is not available. Please try again later."
        }
    
    # Extract company name from URL if not provided
    if not company_name:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        # Remove www. and .com/.net/etc.
        company_name = domain.replace('www.', '').split('.')[0].capitalize()
    
    try:
        # Import the crawler for website content extraction
        try:
            from simple_crawler import crawl_webpage
            logger.info(f"Using simple_crawler to analyze {url}")
            web_content = crawl_webpage(url)
            
            # For well-known companies, try to get additional data from financial sites
            well_known_companies = ["apple", "microsoft", "amazon", "google", "alphabet", "tesla", "meta", "facebook", "netflix"]
            if company_name.lower() in well_known_companies:
                logger.info(f"Getting additional financial data for {company_name}")
                
                # Get stock symbol
                stock_symbol = get_stock_symbol(company_name.lower())
                
                if stock_symbol:
                    # Construct URLs for financial data sources
                    finance_urls = [
                        f"https://finance.yahoo.com/quote/{stock_symbol}",
                        f"https://www.marketwatch.com/investing/stock/{stock_symbol}"
                    ]
                    
                    # Crawl financial sites for additional data
                    finance_content = ""
                    for finance_url in finance_urls[:1]:  # Limit to first one to avoid excessive crawling
                        try:
                            logger.info(f"Crawling financial data from {finance_url}")
                            finance_content += crawl_webpage(finance_url)
                        except Exception as e:
                            logger.warning(f"Failed to crawl {finance_url}: {str(e)}")
                    
                    # Combine company website content with financial data
                    if finance_content:
                        logger.info("Successfully acquired additional financial data")
                        web_content += "\n\n" + finance_content
                
        except ImportError:
            # Fallback to original crawler
            from tools.web_crawler import crawl_webpage_sync
            logger.info(f"Using original crawler to analyze {url}")
            web_content = crawl_webpage_sync(url)
        
        # Extract just the text content by removing markdown formatting
        content_text = re.sub(r'#.*?\n', '', web_content)  # Remove headers
        content_text = re.sub(r'\*\*|\*', '', content_text)  # Remove bold/italic
        content_text = re.sub(r'\[.*?\]\(.*?\)', '', content_text)  # Remove links
        
        # Evaluate the company risk
        evaluation_result = evaluate_company_risk(company_name, content_text, user_id)
        
        if not evaluation_result or "error" in evaluation_result:
            return evaluation_result or {
                "error": "Evaluation Failed",
                "message": "The risk evaluation failed for an unknown reason."
            }
        
        return {
            "company": company_name,
            "website": url,
            "risk_analysis": evaluation_result
        }
    
    except Exception as e:
        logger.error(f"Error analyzing company from URL: {str(e)}")
        return {
            "error": "Analysis Error",
            "message": f"An error occurred during analysis: {str(e)}"
        }

def get_stock_symbol(company_name: str) -> Optional[str]:
    """Get stock symbol for well-known companies."""
    company_symbols = {
        "apple": "AAPL",
        "microsoft": "MSFT",
        "amazon": "AMZN",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "tesla": "TSLA",
        "meta": "META",
        "facebook": "META",
        "nvidia": "NVDA",
        "netflix": "NFLX",
        "ibm": "IBM",
        "intel": "INTC",
        "amd": "AMD",
        "oracle": "ORCL",
        "salesforce": "CRM",
        "walmart": "WMT",
        "target": "TGT",
        "boeing": "BA",
        "disney": "DIS"
    }
    return company_symbols.get(company_name.lower())

def format_risk_analysis_for_display(analysis_result: Dict[str, Any]) -> str:
    """
    Format the risk analysis result for display to users.
    
    Args:
        analysis_result: The risk analysis result dictionary
        
    Returns:
        Formatted string with analysis results
    """
    if "error" in analysis_result:
        return f"**Error: {analysis_result['error']}**\n\n{analysis_result.get('message', '')}"
    
    risk_analysis = analysis_result.get("risk_analysis", {})
    financial_data = risk_analysis.get("financial_data_extracted", {})
    
    formatted_output = f"""## Risk Analysis for {analysis_result.get('company')}

**Website**: {analysis_result.get('website')}

### Risk Assessment
**Risk Score**: {risk_analysis.get('risk_score')} / 100
**Risk Level**: {risk_analysis.get('risk_level')}

### Financial Metrics
"""
    
    # Add financial metrics if available
    if financial_data.get("revenue", 0) > 0:
        revenue = financial_data.get("revenue")
        if revenue >= 1_000_000_000:
            formatted_output += f"**Revenue**: ${revenue/1_000_000_000:.2f} billion\n"
        elif revenue >= 1_000_000:
            formatted_output += f"**Revenue**: ${revenue/1_000_000:.2f} million\n"
        else:
            formatted_output += f"**Revenue**: ${revenue:,.0f}\n"
    
    if financial_data.get("marketCap", 0) > 0:
        market_cap = financial_data.get("marketCap")
        if market_cap >= 1_000_000_000_000:
            formatted_output += f"**Market Cap**: ${market_cap/1_000_000_000_000:.2f} trillion\n"
        elif market_cap >= 1_000_000_000:
            formatted_output += f"**Market Cap**: ${market_cap/1_000_000_000:.2f} billion\n"
        else:
            formatted_output += f"**Market Cap**: ${market_cap/1_000_000:.2f} million\n"
    
    formatted_output += f"**Debt-to-Equity Ratio**: {financial_data.get('debtToEquity', 'N/A')}\n"
    
    net_profit = financial_data.get("netProfit", 0)
    if net_profit != 0:
        if net_profit >= 1_000_000_000:
            formatted_output += f"**Net Profit**: ${net_profit/1_000_000_000:.2f} billion\n"
        elif net_profit >= 1_000_000:
            formatted_output += f"**Net Profit**: ${net_profit/1_000_000:.2f} million\n"
        elif net_profit < 0:
            # For losses, show in red
            if abs(net_profit) >= 1_000_000_000:
                formatted_output += f"**Net Loss**: ${abs(net_profit)/1_000_000_000:.2f} billion\n"
            elif abs(net_profit) >= 1_000_000:
                formatted_output += f"**Net Loss**: ${abs(net_profit)/1_000_000:.2f} million\n"
            else:
                formatted_output += f"**Net Loss**: ${abs(net_profit):,.0f}\n"
        else:
            formatted_output += f"**Net Profit**: ${net_profit:,.0f}\n"
    
    formatted_output += f"**Sector**: {financial_data.get('sector', 'Unknown').capitalize()}\n\n"
    
    formatted_output += "### Risk Factors\n"
    
    for explanation in risk_analysis.get("explanations", []):
        formatted_output += f"- {explanation}\n"
    
    formatted_output += "\n### Recommendations\n"
    
    for recommendation in risk_analysis.get("recommendations", []):
        formatted_output += f"- {recommendation}\n"
    
    # Add sources of information
    formatted_output += "\n### Data Sources\n"
    formatted_output += f"- Company website: {analysis_result.get('website')}\n"
    
    # Check if we have financial data from Yahoo Finance
    if "yahoo.com" in analysis_result.get('website', '') or financial_data.get("marketCap", 0) > 0:
        formatted_output += "- Financial data sources\n"
    
    # Add disclaimer
    formatted_output += """
### Note
This risk analysis is based on information extracted automatically from the company website and financial sources. 
The accuracy of the assessment depends on the quality and completeness of the information available.
For a comprehensive risk assessment, consult with financial experts.
"""
    
    return formatted_output

if __name__ == "__main__":
    # Simple test
    test_url = "https://www.example.com"
    print(f"Testing risk analysis for {test_url}")
    result = analyze_company_from_url(test_url, "Example Company")
    print(format_risk_analysis_for_display(result)) 