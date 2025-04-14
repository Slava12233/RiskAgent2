"""
Streamlit UI for Risk Agent - A web crawler and financial risk analysis assistant
powered by Google Gemini model.
"""

import os
import sys
import uuid
import streamlit as st
from typing import Dict, List, Tuple
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import agent with a fallback mechanism
try:
    from agent import get_agent
except Exception as e:
    st.error(f"Failed to import agent: {str(e)}")
    st.stop()

# Set page configuration
st.set_page_config(
    page_title="Risk Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS for styling that matches the screenshot
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 0;
        max-width: 100%;
    }
    
    /* Remove default Streamlit padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* Hide header decoration */
    header {
        visibility: hidden;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: white;
        padding-top: 1rem;
    }
    
    /* Global typography */
    body {
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* ChatGPT style heading */
    .chatgpt-heading {
        text-align: center;
        font-size: 2rem;
        font-weight: 600;
        margin-top: 7rem;
        margin-bottom: 3rem;
        color: rgb(25, 25, 25);
    }
    
    /* API status box styling */
    .api-status {
        background-color: #ecfdf5;
        color: #065f46;
        padding: 8px 12px;
        border-radius: 6px;
        margin-bottom: 16px;
        font-size: 0.9rem;
    }
    
    /* Debug mode checkbox with no label */
    .no-label label {
        display: none;
    }
    
    /* Button styling */
    div.stButton > button {
        width: 100%;
        border-radius: 4px;
        border: 1px solid #e5e7eb;
        padding: 8px 12px;
        font-size: 0.9rem;
        text-align: left;
        background-color: white;
        color: #374151;
        font-weight: normal;
        margin-bottom: 8px;
    }
    
    div.stButton > button:hover {
        background-color: #f9fafb;
    }
    
    /* Chat message styling */
    .stChatMessage {
        padding: 0.75rem 0.5rem;
    }
    
    /* User message avatar styling */
    [data-testid="stChatMessageAvatar"].user {
        background-color: #F43F5E !important;
    }
    
    /* Assistant message avatar styling */
    [data-testid="stChatMessageAvatar"].assistant {
        background-color: #F59E0B !important;
    }
    
    /* Source styling */
    .source-info {
        margin-top: 8px;
        padding: 8px 12px;
        background-color: #F7F7F8;
        border-radius: 6px;
        border-left: 2px solid #3B82F6;
        font-size: 0.875rem;
        color: #374151;
    }
    
    .source-info a {
        color: #3B82F6;
        text-decoration: none;
    }
    
    .source-info a:hover {
        text-decoration: underline;
    }
    
    /* Chat input styling */
    .stChatInputContainer {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Make the chat input rounded with border */
    div.stChatInputContainer > div {
        border: 1px solid #e5e7eb;
        border-radius: 9999px;
        box-shadow: none;
        max-width: 750px;
        margin: 0 auto;
    }
    
    /* Send button styling */
    button[data-testid="chat-input-submit-button"] {
        background-color: transparent !important;
    }
    
    /* Section headers */
    .section-header {
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        color: #111827;
        font-size: 0.95rem;
    }
    
    /* Shield icon for header */
    .shield-icon {
        margin-right: 0.25rem;
        color: #7c3aed;
    }
    
    /* About section text */
    .about-text {
        font-size: 0.9rem;
        color: #4b5563;
        line-height: 1.5;
    }
    
    /* About section bullets */
    .about-text ul {
        margin-top: 0.5rem;
        padding-left: 1.2rem;
    }
    
    .about-text li {
        margin-bottom: 0.25rem;
    }
    
    /* Footer text */
    .footer-text {
        font-size: 0.75rem;
        color: #9ca3af;
        margin-top: 3rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Define hardcoded responses for common greetings
GREETING_RESPONSES = {
    "hi": "Hi there! How can I help you today?",
    "hello": "Hello! I'm your web research assistant. What would you like to know?",
    "hey": "Hey! I'm ready to help. What information are you looking for?",
    "greetings": "Greetings! I'm your AI assistant. How can I assist you?",
    "good morning": "Good morning! How can I assist you today?",
    "good afternoon": "Good afternoon! What can I help you with?",
    "good evening": "Good evening! What information can I find for you?"
}

# Initialize session state
def init_session():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "user_id" not in st.session_state:
            st.session_state.user_id = str(uuid.uuid4())
    
    if "agent" not in st.session_state:
        try:
            st.session_state.agent = get_agent()
        except Exception as e:
            st.error(f"Error initializing agent: {str(e)}")
            st.session_state.agent = None
    
    # Add debug mode if not present
    if "debug" not in st.session_state:
        st.session_state.debug = False
    
    # Add thinking state
    if "thinking" not in st.session_state:
        st.session_state.thinking = False
    
    # Add API key state
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("GOOGLE_API_KEY", "")

def display_chat_history():
    """Display the chat message history."""
    # Display each message
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        # Set avatar based on role
        avatar = "👤" if role == "user" else "🛡️"
        
        with st.chat_message(role, avatar=avatar):
            st.markdown(content)

            # Display sources if available for assistant messages
            if role == "assistant" and "crawled_urls" in message and message["crawled_urls"]:
                crawled_urls = message["crawled_urls"]
                if crawled_urls:
                    st.markdown("""<div class="source-info">
                        <strong>Sources:</strong>
                        </div>""", unsafe_allow_html=True)
                    for i, url in enumerate(crawled_urls):
                        st.markdown(f"""<div class="source-info">
                            {i+1}. <a href="{url}" target="_blank">{url}</a>
                            </div>""", unsafe_allow_html=True)

def get_response(user_input: str) -> tuple:
    """Get response for a user input with reliable fallbacks."""
    # Check for simple greetings
    if user_input.lower().strip() in GREETING_RESPONSES:
        return GREETING_RESPONSES[user_input.lower().strip()], []
    
    # Try with the agent
    try:
        if st.session_state.agent:
            # Allow 3 retries for robustness
            for attempt in range(3):
                try:
                    response_data = st.session_state.agent.process_message(
                        st.session_state.user_id,
                        user_input
                    )
                    
                    # Check if response is already a tuple (newer version)
                    if isinstance(response_data, tuple):
                        response_text, crawled_urls = response_data
                    else:
                        # Backward compatibility for older version
                        response_text = response_data
                        crawled_urls = []
                        
                    if response_text and response_text.strip():
                        return response_text, crawled_urls
                except Exception as e:
                    print(f"Agent error on attempt {attempt+1}: {str(e)}")
                    if attempt == 2:  # Last attempt
                        raise
        
        # If we get here, we didn't get a valid response
        return "I'm sorry, I couldn't process your request. Please try asking something else.", []
    except Exception as e:
        print(f"Error getting response: {str(e)}")
        return f"I'm sorry, I encountered an error: {str(e)}. Please try a different question.", []

def process_user_message(user_input: str):
    """Process a user message and add the response to the chat history."""
    if not user_input.strip():
        return
    
    # Add user message to chat history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Signal thinking state
    st.session_state.thinking = True
    
    # Rerun to show the user message immediately
    st.rerun()

def generate_assistant_response():
    """Generate the assistant response for the latest user message."""
    if not st.session_state.thinking or not st.session_state.messages:
        return
    
    # Get the last user message
    last_user_message = None
    for message in reversed(st.session_state.messages):
        if message["role"] == "user":
            last_user_message = message["content"]
            break
    
    if not last_user_message:
        st.session_state.thinking = False
        return
    
    # Create a placeholder for the assistant message
    with st.chat_message("assistant", avatar="🛡️"):
        message_placeholder = st.empty()
        
        # Show thinking indicator
        message_placeholder.markdown("<span style='color:#6B7280;font-style:italic;'>Thinking...</span>", unsafe_allow_html=True)
        time.sleep(0.5)
        
        # Get the response
        response_text, crawled_urls = get_response(last_user_message)
        
        # Display the final response
        message_placeholder.markdown(response_text)
        
        # Display sources
        if crawled_urls:
            st.markdown("""<div class="source-info">
                <strong>Sources:</strong>
                </div>""", unsafe_allow_html=True)
            for i, url in enumerate(crawled_urls):
                st.markdown(f"""<div class="source-info">
                    {i+1}. <a href="{url}" target="_blank">{url}</a>
                    </div>""", unsafe_allow_html=True)
    
    # Add the assistant response to the chat history
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "crawled_urls": crawled_urls
    })
    
    # Reset thinking state
    st.session_state.thinking = False

def clear_chat():
    """Clear the chat history."""
    st.session_state.messages = []
    st.rerun()

def run_subtest(test_name):
    """Run a specific subtest to validate functionality."""
    if test_name == "greeting":
        return "Hi there! This is a test greeting.", []
    elif test_name == "web_search":
        return "This is a test of the web search function. In a real scenario, this would return search results.", ["https://example.com/test"]
    elif test_name == "risk_analysis":
        return "This is a test of the risk analysis function. Sample risk score: 72/100 (Medium Risk)", ["https://example.com/risk"]
    else:
        return f"Unknown test: {test_name}", []

def main():
    """Main function to set up the Streamlit UI."""
    # Initialize session
    init_session()
    
    # Only show sidebar if there are messages
    if st.session_state.messages:
        show_sidebar = True
    else:
        show_sidebar = False
    
    # Show welcome heading if no messages
    if not st.session_state.messages:
        st.markdown('<div class="chatgpt-heading">What\'s on your mind today?</div>', unsafe_allow_html=True)
    
    # Sidebar setup
    with st.sidebar:
        # Title with shield icon
        st.markdown('<span class="shield-icon">🛡️</span> <span style="font-size:1rem;font-weight:500;">Risk Agent</span>', unsafe_allow_html=True)
        
        # Description
        st.markdown('<p style="font-size:0.8rem;margin-top:0.3rem;line-height:1.2;">This chatbot is created using the Risk Agent web crawler powered by Google Gemini.</p>', unsafe_allow_html=True)
        
        # API Key status
        if st.session_state.api_key:
            st.markdown('<div class="api-status">✓ API key already provided!</div>', unsafe_allow_html=True)
        
        # Debug mode checkbox
        debug_col = st.container()
        with debug_col:
            st.markdown('<div class="no-label">', unsafe_allow_html=True)
            st.checkbox("Debug Mode", value=st.session_state.debug, key="debug_mode", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Clear conversation button
        if st.button("Clear Conversation"):
            clear_chat()
        
        # Example prompts section
        st.markdown('<div class="section-header">Example Prompts</div>', unsafe_allow_html=True)
        
        if st.button("Tell me about the latest news on SpaceX"):
            process_user_message("Tell me about the latest news on SpaceX")
        
        if st.button("What are the best laptops for programming?"):
            process_user_message("What are the best laptops for programming?")
        
        if st.button("Compare React and Angular for web development"):
            process_user_message("Compare React and Angular for web development")
        
        if st.button("Analyze the risk for Apple https://www.apple.com"):
            process_user_message("Analyze the risk for Apple https://www.apple.com")
        
        # Subtest section (if in debug mode)
        if st.session_state.debug:
            st.markdown('<div class="section-header">Subtests</div>', unsafe_allow_html=True)
            
            subtest_cols = st.columns(2)
            with subtest_cols[0]:
                if st.button("Test Greeting"):
                    response, _ = run_subtest("greeting")
                    st.session_state.messages.append({"role": "user", "content": "[SUBTEST] Greeting Test"})
                    st.session_state.messages.append({"role": "assistant", "content": response, "crawled_urls": []})
                    st.rerun()
            
            with subtest_cols[1]:
                if st.button("Test Search"):
                    response, urls = run_subtest("web_search")
                    st.session_state.messages.append({"role": "user", "content": "[SUBTEST] Web Search Test"})
                    st.session_state.messages.append({"role": "assistant", "content": response, "crawled_urls": urls})
                    st.rerun()
            
            if st.button("Test Risk Analysis"):
                response, urls = run_subtest("risk_analysis")
                st.session_state.messages.append({"role": "user", "content": "[SUBTEST] Risk Analysis Test"})
                st.session_state.messages.append({"role": "assistant", "content": response, "crawled_urls": urls})
                st.rerun()
        
        # About section
        st.markdown('<div class="section-header">About</div>', unsafe_allow_html=True)
        st.markdown('''
        <div class="about-text">
        This assistant can search the web for information and analyze companies for financial risk.
        <ul>
            <li>Search the web for current information</li>
            <li>Analyze multiple sources for comprehensive answers</li>
            <li>Evaluate company risk profiles</li>
        </ul>
        </div>
        ''', unsafe_allow_html=True)
    
    # Main chat area
    display_chat_history()
    
    # Generate response if in thinking state
    if st.session_state.thinking:
        generate_assistant_response()
    
    # Chat input at the bottom
    user_input = st.chat_input("How can I help you today?", disabled=st.session_state.thinking)
    if user_input:
        process_user_message(user_input)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        if st.session_state.get("debug", False):
            st.exception(e)
