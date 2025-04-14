# Web Crawler Conversational Agent

A web crawler conversational agent powered by Google's Gemini model that can search and extract information from the internet to answer user queries.

## Recent Updates

- **Dual Crawler System**: Simple Crawler using requests/BeautifulSoup as the primary crawler with Playwright as fallback
- **Improved Reliability**: Enhanced retry logic with progressive timeouts (15s, 22.5s, 30s)
- **Resource Management**: Reduced concurrency (3 workers max) to prevent resource exhaustion
- **Enhanced Error Handling**: Graceful fallbacks between crawlers with comprehensive logging
- **Improved UI**: Added display of crawled URLs in the interface for transparency
- **Advanced Content Extraction**: More intelligent extraction of content from various website types

## Features

- Natural language conversation with an AI assistant
- Reliable multi-strategy web crawling to fetch relevant information
- Support for crawling multiple websites for comprehensive answers
- Content summarization for large webpages
- Provides sources for all information retrieved with visible URLs
- Beautiful Streamlit user interface
- Comprehensive logging system

## Prerequisites

- Python 3.9 or higher
- Google API Key (Gemini model access)
- Required packages: requests, BeautifulSoup4, Playwright

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/web-crawler-agent.git
cd web-crawler-agent
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers (used as fallback crawler):
```bash
python install_playwright.py
```

5. Create a `.env` file with your Google API key:
```
GOOGLE_API_KEY=your_google_api_key_here
```

You can get a Google API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

## Usage

Run the Streamlit app:
```bash
python main.py
```

Then select option 1 to launch the Streamlit UI, or follow the on-screen instructions for other options.

Alternatively, you can run the Streamlit app directly:
```bash
streamlit run ui/streamlit_app.py
```

## How It Works

1. The user enters a query through the Streamlit UI
2. The agent analyzes the query to determine if web crawling is needed:
   - Checks for direct URLs
   - Detects multi-site information requests
   - Identifies web search queries
3. For web crawling, the system uses a dual-crawler approach:
   - **Primary**: Simple Crawler (requests/BeautifulSoup) for reliability
   - **Fallback**: Playwright-based crawler for complex sites
4. Multiple retry attempts with progressive timeouts ensure maximum content retrieval
5. The agent formulates a response based on the crawled content and its knowledge
6. The response is displayed to the user along with links to the source URLs

## System Architecture

The system consists of several key components:

- **Agent (agent.py)**: Core logic for processing messages and orchestrating crawlers
- **Simple Crawler (simple_crawler.py)**: Primary crawler using requests/BeautifulSoup
- **Web Crawler (tools/web_crawler.py)**: Secondary crawler using Playwright
- **UI (ui/streamlit_app.py)**: Streamlit interface for user interaction
- **Utility Modules**: Error handling, logging, and helper functions

## Troubleshooting

### Crawler Reliability Issues

If specific websites consistently fail to be crawled:

1. Check the logs for specific error messages (usually 403 Forbidden errors)
2. Some websites actively block automated access and may require manual viewing
3. Try modifying the USER_AGENT in simple_crawler.py to mimic different browsers
4. Adjust timeout settings if network conditions are poor

### Playwright Installation Issues

If you encounter issues with the fallback Playwright installation, try:

```bash
python -m playwright install --with-deps chromium
```

Or run the included installation script:

```bash
python install_playwright.py
```

## Testing

Run the end-to-end test suite to verify that the agent is working correctly:

```bash
python test_e2e_conversation.py
```

The tests include several scenarios:
- News queries (e.g., Israel news)
- Product reviews (e.g., laptop comparisons)
- Technology topics (e.g., programming language comparisons)

Test results are saved as JSON files with timestamps.

## Project Structure

- `agent.py` - The main agent implementation
- `simple_crawler.py` - Primary web crawler using requests/BeautifulSoup
- `tools/web_crawler.py` - Secondary web crawler using Playwright
- `ui/streamlit_app.py` - Streamlit UI with source URL display
- `utils/` - Utility functions for error handling and logging
- `tests/` - Test files including end-to-end conversation tests
- `test_e2e_conversation.py` - End-to-end test runner

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) for the language model
- [Requests](https://requests.readthedocs.io/) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for primary crawling
- [Playwright](https://playwright.dev/) for fallback web crawling capabilities
- [Streamlit](https://streamlit.io/) for the user interface 