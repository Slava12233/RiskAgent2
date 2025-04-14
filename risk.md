# Web Crawler Agent with Risk Engine

## System Overview

The Web Crawler Agent with Risk Engine integration combines web crawling capabilities with financial risk assessment. The system allows users to interact with a conversational agent that can extract financial information from company websites and analyze the company's risk profile.

![System Architecture](https://mermaid.ink/img/pako:eNp1kk1vgzAMhv-K5fPAhRKgTOVj6nHqYey9TblYxK0jCATlY1Mq_vvCoGqruvlg-_Xj2HYvhCuJJCahMLJVGm_UWcHnQmNlW9lI87VVeH2rHRTatmBfmgauP2Q3HhP_5AZ5fZjBVUL2KqjvCxBzrq3QZdQpKPRJQmJjKYJtF5HrS9GYyApNyoOkD7DdYSOqbSeFVqiDCqKECbXoUXYjNNOTY-z1XAKV-Kf_hZxVnl_-ZeEbXH7d59vIVJXa8B4bFZwG-TJSLmAYmvEOFfbCQX7Lp_Nnv5a1KsF3hG8Lp2qKRWjdSMFXIodXpqcJsX1vG0w4YeF8j7Qp-5nZsCdRYFLYEVQr0_Yd3HNu8YwJx2KYUGFLsaTUdkbmhLOwhxuqYHKyIOYQw4K0-CVHuLXo20DCkbFJEk3iaBnHi_kqjR9Z-pAuyX08dXJI9X0aTvMLj-KA9w?type=png)

## Process Flow

The system follows a specific flow to process user requests, crawl websites, and analyze risk:

1. **User Input Processing**: The agent analyzes the user's message to determine if it's a web crawling request, risk analysis request, or general query
2. **Web Crawling**: If required, the agent crawls the company website using:
   - Simple Crawler (primary, using requests/BeautifulSoup)
   - Playwright Crawler (fallback for complex sites)
3. **Data Extraction**: Financial metrics are extracted from the crawled content
4. **Risk Analysis**: This data is sent to the risk engine for evaluation
5. **Response Generation**: The risk assessment is formatted and presented to the user

## Risk Factors and Weights

| Risk Factor | Description | Weight |
|-------------|-------------|--------|
| Debt-to-Equity Ratio | Measures financial leverage by comparing total debt to shareholders' equity | 30% |
| Net Profit | Company's bottom-line earnings after all expenses, taxes, and costs | 25% |
| Negative News | Measure of negative sentiment in content about the company | 20% |
| Late Payments | Rate of late payments to suppliers, indicating potential cash flow issues | 25% |

## Risk Factor Determination Process

### 1. Debt-to-Equity Ratio
- **Data Extraction**: Found using regex patterns or defaults to 2.0
- **Risk Categories**:
  - ≤1.0: "Healthy range" (Low risk)
  - 1.0-2.0: "Moderate financial leverage" (Medium risk)
  - 2.0-3.0: "High financial risk" (High risk)
  - >3.0: "Significant financial leverage" (Very high risk)

### 2. Net Profit Assessment
- **Data Extraction**: Searches for profit figures or defaults to 0 (break-even)
- **Risk Categories**:
  - >$500,000: "Excellent financial health" (Very low risk)
  - >$100,000: "Good financial health" (Low risk)
  - >$0: "Modest positive net profit" (Medium risk)
  - >-$100,000: "Concerning financial performance" (High risk)
  - <-$100,000: "Serious financial challenges" (Very high risk)

### 3. Negative News Score
- **Data Extraction**: Frequency of negative terms relative to total content
- **Risk Categories**:
  - ≤0.2: "Low negative news coverage" (Low risk)
  - 0.2-0.4: "Moderate negative news coverage" (Medium risk)
  - 0.4-0.6: "May impact business reputation" (High risk)
  - >0.6: "Significant reputational risk" (Very high risk)

### 4. Late Payments Rate
- **Data Extraction**: Usually defaults to 0.1 (difficult to extract reliably)
- **Risk Categories**:
  - ≤0.05: "Good cash flow management" (Low risk)
  - 0.05-0.1: "Moderate rate of late payments" (Medium risk)
  - 0.1-0.2: "May indicate cash flow issues" (High risk)
  - >0.2: "Cash flow problems" (Very high risk)

### 5. Sector Risk Assessment
- **Data Extraction**: Determined by counting industry-related keywords
- **Sector Risk Multipliers**:

  | Sector | Risk Multiplier | Risk Level |
  |--------|----------------|-----------|
  | Healthcare | 0.9 | Lower Risk |
  | Utilities | 0.85 | Lower Risk |
  | Technology | 1.0 | Average Risk |
  | General | 1.0 | Average Risk |
  | Retail | 1.1 | Higher Risk |
  | Real Estate | 1.15 | Higher Risk |
  | Finance | 1.2 | Higher Risk |
  | Energy/Oil/Gas | 1.3 | Much Higher Risk |

## Risk Score Calculation

```
Final Score = (Weighted Sum of Risk Factors) × Sector Multiplier × 100
```

Where:
- Weighted Sum = (Debt-to-Equity × 0.3) + (Net Profit × 0.25) + (Negative News × 0.2) + (Late Payments × 0.25)
- Sector Multiplier = Value from Sector Risk Table

## Risk Levels

| Risk Score | Risk Level | Interpretation |
|------------|------------|----------------|
| 0-40 | Low Risk | Good financial health, low concern |
| 41-70 | Medium Risk | Some financial challenges, moderate concern |
| 71-100 | High Risk | Significant financial issues, high concern |

## Example Analysis

For a company with:
- Debt-to-Equity: 2.0 (default)
- Net Profit: $0 (break-even)
- Negative News: 0.15 (low)
- Late Payments: 0.1 (moderate)
- Sector: General (multiplier: 1.0)

The calculation would be:
```
Weighted Sum = (2.0 × 0.3) + (0 × 0.25) + (0.15 × 0.2) + (0.1 × 0.25) = 0.67
Final Score = 0.67 × 1.0 × 100 = 67
```

**Result**: Medium Risk (score: 67)
