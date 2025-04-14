# Enhanced Company Risk Analysis

This document explains how to use the enhanced company risk analysis features implemented in the Risk Agent system.

## Overview

The enhanced risk analysis feature allows the agent to:

1. Detect when users ask about company risk analysis
2. Extract financial metrics from company websites and financial data sources
3. Calculate risk scores based on the extracted metrics
4. Present a comprehensive risk assessment with detailed financial information

## Usage Examples

You can interact with the risk analysis feature through natural language queries:

```
analyze the risk for Apple
what is the financial risk of Tesla?
perform a risk assessment for Microsoft
evaluate Amazon's company risk
analyze Google's financial health
```

## How It Works

The system follows these steps when analyzing company risk:

1. **Company Detection**: The agent identifies company names in your query.

2. **Data Collection**: For well-known companies, the system:
   - Looks up the company's stock symbol (e.g., AAPL for Apple)
   - Collects data from financial websites like Yahoo Finance
   - Extracts content from the company's own website
   - Combines data from multiple sources for a more complete picture

3. **Metric Extraction**: The system extracts key financial metrics:
   - Revenue figures
   - Net profit/earnings
   - Market capitalization
   - Debt-to-equity ratio
   - Negative news sentiment
   - Industry sector

4. **Risk Calculation**: The risk engine analyzes the extracted metrics to:
   - Calculate a risk score (0-100, where higher scores mean higher risk)
   - Determine risk level (Low, Medium, High)
   - Generate explanations of risk factors
   - Provide customized recommendations

5. **Result Presentation**: The results are presented in a structured format with:
   - Summary of risk score and level
   - Detailed financial metrics with appropriate units (billions, millions)
   - List of risk factors
   - Actionable recommendations
   - Data sources and disclaimers

## Testing

To test the risk analysis feature:

1. Run the unit tests:
   ```
   python -m unittest tests/test_risk_analysis.py
   ```

2. Try the demonstration script:
   ```
   python demo_risk_analysis.py
   ```

3. Use the interactive agent and ask about company risk.

## Technical Details

The risk analysis feature uses several components:

- **agent.py**: Contains the `detect_company_risk_query` method for identifying risk analysis queries.
- **risk_analyzer.py**: Extracts financial data from crawled content and interfaces with the risk engine.
- **risk-engine/**: Calculates risk scores based on financial metrics.

If you're enhancing the feature, focus on these areas:

1. Improve regex patterns in `extract_financial_data` to extract more metrics
2. Add more companies and stock symbols to `get_stock_symbol`
3. Add more financial data sources in `analyze_company_from_url`

## Limitations

The current implementation has some limitations:

- Works best with well-known companies (Apple, Microsoft, Tesla, etc.)
- Depends on the quality of data available on websites
- May miss some financial metrics if they're not mentioned in standard formats
- Performance depends on website availability and response times

## Future Enhancements

Planned enhancements include:

- Support for more companies and sectors
- Integration with professional financial data APIs
- Historical trend analysis
- Competitor comparison
- Machine learning for more accurate risk prediction 