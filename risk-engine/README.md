# Business Risk Engine

A powerful API for evaluating business and financial risk based on company metrics. This service calculates risk scores, provides detailed explanations, and offers actionable recommendations tailored to different business sectors.

## Overview

The Risk Engine analyzes key financial and operational metrics to assess a company's risk profile:

- Debt-to-equity ratio
- Net profit
- Negative news exposure
- Late payments rate
- Sector-specific adjustments

The system provides:
- Risk scores (0-100, where higher means riskier)
- Risk level categorization (Low, Medium, High)
- Detailed explanations of risk factors
- Tailored recommendations based on risk profile and business sector

## System Architecture

The Risk Engine is built with:

- **FastAPI**: High-performance REST API framework
- **SQLAlchemy**: ORM for database interactions
- **Pydantic**: Data validation and settings management
- **SQLite**: Local database for storing risk evaluations

```
risk-engine/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI application entry point
│   ├── database.py        # Database connection handling
│   ├── models.py          # SQLAlchemy database models
│   ├── routes.py          # API endpoints
│   └── logic/
│       ├── __init__.py
│       ├── risk_calculator.py  # Core risk calculation logic
│       └── risk_scoring.py     # Risk scoring algorithms
├── tests/                 # Test suite
├── demo_client.py         # Demo client for testing
├── risk_engine.db         # SQLite database
└── README.md              # This file
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/evaluate` | POST | Calculate risk score for a company |
| `/api/evaluations/{evaluation_id}` | GET | Retrieve a specific evaluation |
| `/api/evaluations/company/{company_name}` | GET | Retrieve all evaluations for a company |
| `/api/health` | GET | Health check endpoint |

### Risk Evaluation Request Format

```json
{
  "user_id": "user123",
  "companyName": "Example Corp",
  "debtToEquity": 2.5,
  "netProfit": 1500000,
  "negativeNewsScore": 0.3,
  "latePaymentsRate": 0.1,
  "sector": "technology",
  "additionalFactors": {
    "yearsInBusiness": 5,
    "countryRisk": 0.2
  }
}
```

### Risk Evaluation Response Format

```json
{
  "score": 57.8,
  "explanations": [
    "High debt-to-equity ratio increases financial risk",
    "Strong positive net profit indicates excellent financial health",
    "Moderate negative news coverage",
    "Moderate rate of late payments",
    "Technology sector has moderate baseline risk"
  ],
  "recommendation": "Medium Risk",
  "recommendations": [
    "Quarterly financial health monitoring recommended",
    "Develop action plan for identified risk areas",
    "Evaluate competitive positioning in volatile market"
  ],
  "evaluation_id": 42
}
```

## Risk Calculation Methodology

The risk calculation incorporates:

1. **Financial Metrics Analysis**:
   - Debt-to-equity ratio: Higher ratios increase risk score
   - Net profit: Negative values significantly increase risk
   - Late payments rate: Higher rates indicate potential cash flow issues

2. **Sector-Based Adjustments**:
   - Different sectors have different baseline risk multipliers
   - Higher-risk sectors (finance, energy, oil & gas) have higher multipliers
   - Lower-risk sectors (utilities, healthcare) have lower multipliers

3. **External Factors Assessment**:
   - Negative news coverage evaluation
   - Additional contextual factors when provided

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/RiskAgent2.git
cd RiskAgent2/risk-engine
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the Risk Engine:
```bash
python -m app.main
```

The server will start on http://localhost:8000. Visit http://localhost:8000/docs for the interactive API documentation.

## Usage Examples

### Using the Demo Client

The repository includes a demo client that showcases various business scenarios:

```bash
python demo_client.py
```

To run a specific scenario:

```bash
python demo_client.py --scenario tech-startup
```

Available scenarios:
- tech-startup
- established-tech
- manufacturing
- retail
- healthcare
- finance

### Direct API Requests

```python
import requests

# Evaluate company risk
response = requests.post(
    "http://localhost:8000/api/evaluate",
    json={
        "user_id": "analyst001",
        "companyName": "Acme Corp",
        "debtToEquity": 1.8,
        "netProfit": 3200000,
        "negativeNewsScore": 0.25,
        "latePaymentsRate": 0.05,
        "sector": "technology"
    }
)

# Print the risk evaluation
print(response.json())
```

## Integration with Web Crawler Agent

The Risk Engine integrates with the Web Crawler Agent to automate company analysis:

1. The Web Crawler Agent extracts financial data from company websites
2. The Risk Analyzer module processes extracted information
3. The Risk Engine calculates risk scores and recommendations
4. Results are formatted and presented to users

### Analyzer Component

The `risk_analyzer.py` module handles:
- Extracting financial data from crawled content
- Detecting financial metrics using pattern matching
- Determining business sectors based on keyword frequency
- Estimating negative news exposure from content analysis
- Formatting results for user-friendly display

## Troubleshooting

### Database Connection Issues

If the database connection fails:
- Check that the database file exists and has proper permissions
- Verify the database path in `app/database.py`
- Restart the server after fixing connections

### API Errors

Common error codes:
- 404: Resource not found (evaluation ID doesn't exist)
- 500: Internal server error (typically a calculation error)

For API issues, check the server logs for detailed error messages.

### Integration Problems

If the web crawler integration fails:
- Ensure both the Risk Engine and Web Crawler Agent are running
- Check network connectivity between services
- Verify URL parsing and extraction is working correctly

## Contributing

Contributions are welcome! Areas for improvement:
- Enhanced sector-specific risk modeling
- Machine learning integration for smarter risk assessment
- Additional financial metrics analysis
- Improved data extraction from websites

## License

This project is licensed under the MIT License - see the LICENSE file for details. 