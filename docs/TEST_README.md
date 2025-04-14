# Web Crawler Agent Testing Guide

This document provides guidance on testing the Web Crawler Agent and troubleshooting common issues.

## Running Tests

You can run the test suite using the following command:

```bash
python run_tests.py
```

The test suite includes several test cases that verify the agent's ability to:
- Crawl news websites
- Compare technologies
- Search for location-based information
- Retrieve programming documentation
- Find product information

## Test Results

Test results are saved in the `test_logs` directory in JSON format. Each test run creates a new log file with a timestamp.

## Troubleshooting Playwright Issues

The agent primarily uses Playwright for web crawling but falls back to HTTP requests if Playwright encounters issues.

### Common Playwright Problems

1. **Timeout Errors**
   - If you see "Timeout exceeded" errors in the logs, try increasing the `DEFAULT_TIMEOUT` value in `tools/web_crawler.py`.
   - The crawler now implements retry logic with different wait strategies to handle this.

2. **Browser Initialization Failures**
   - If Playwright fails to initialize, ensure it's properly installed:
   ```bash
   python install_playwright.py
   ```

3. **Navigation Issues**
   - Some websites employ anti-bot measures that may block Playwright.
   - The retry logic will attempt different strategies before falling back to HTTP.

4. **Resource Consumption**
   - Playwright can consume significant memory with multiple browser instances.
   - The crawler now uses a semaphore to limit concurrent browser operations.

### Interpreting Logs

The logs contain detailed information about the crawler's operations:

- **Initialization logs** show browser startup and configuration
- **Navigation logs** show URL access attempts and results
- **Fallback logs** indicate when HTTP fallback is triggered
- **Content extraction logs** show what was retrieved from websites

### Testing with Different Website Types

To test specific website types:

1. **News Sites**: Test with queries like "What are the latest developments in [topic]?"
2. **Technical Documentation**: Test with queries like "How do I use [technology]?"
3. **E-commerce/Product Sites**: Test with queries like "What are the best [products]?"
4. **Travel Sites**: Test with queries like "What are tourist attractions in [location]?"

## Debugging the UI Integration

If the agent works in tests but not in the UI:

1. Check if the same timeout issues occur in both environments
2. Verify session management is working correctly
3. Look for differences in how the agent is initialized in tests vs. UI
4. Ensure error messages from the crawler are properly displayed in the UI

## Advanced Testing

For more advanced testing and debugging:

1. **Single URL Testing**: Test crawling a single URL directly:
   ```python
   from tools.web_crawler import crawl_webpage_sync
   result = crawl_webpage_sync("https://example.com")
   print(result)
   ```

2. **Multiple URL Testing**: Test crawling multiple URLs:
   ```python
   from tools.web_crawler import crawl_multiple_webpages_sync
   urls = ["https://example1.com", "https://example2.com"]
   result = crawl_multiple_webpages_sync(urls)
   print(result)
   ```

3. **Browser Environment Testing**: To check if Playwright can run:
   ```python
   from tools.web_crawler import check_playwright_installed_sync
   is_available = check_playwright_installed_sync()
   print(f"Playwright available: {is_available}")
   ```

## Reporting Issues

When reporting issues:

1. Include the full log file
2. Describe the query that caused the issue
3. Note whether it occurred in tests, UI, or both
4. Include system information (OS, Python version, etc.)
5. Describe any recent changes that might have affected the behavior
