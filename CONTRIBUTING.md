# Contributing to the Web Crawler Conversational Agent

Thank you for considering contributing to this project! This document provides guidelines and instructions for setting up your development environment and contributing code.

## Setting Up the Development Environment

### Prerequisites

- Python 3.9 or higher
- pip package manager
- Git

### Installation Steps

1. Clone the repository
```bash
git clone <repository-url>
cd RiskAgent2
```

2. Create a virtual environment
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers
```bash
playwright install
```

5. Create a `.env` file with your API key
```
GOOGLE_API_KEY=your_google_api_key_here
```

6. Run the application to verify everything works
```bash
python main.py
```

## Project Structure

- `agent.py`: Google ADK agent implementation
- `tools/web_crawler.py`: Web crawler tool implementation
- `utils/`: Utility functions
- `ui/streamlit_app.py`: Streamlit UI components
- `main.py`: Application entry point

## Development Workflow

1. Create a new branch for your feature or bug fix
2. Make your changes
3. Test your changes both manually and with any automated tests
4. Update documentation if necessary
5. Submit a pull request with a clear description of your changes

## Code Style

- Follow PEP8 guidelines for Python code
- Use type hints for function parameters and return values
- Write docstrings for all functions, classes, and modules
- Keep functions focused and under 50 lines where possible
- Use meaningful variable and function names

## Adding New Features

When adding new features, please follow these guidelines:

1. First check `TASK.md` to see if your feature is already planned
2. Add appropriate error handling for your feature
3. Update any relevant documentation
4. Add docstrings to new functions and classes
5. If appropriate, add your feature to the `TASK.md` file under "Optional Enhancements"

## Testing

- Test your changes manually by running the application
- Ensure all features work as expected
- Verify that your changes don't introduce new bugs 