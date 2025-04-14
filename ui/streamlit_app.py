"""
Streamlit UI for the web crawler conversational agent.

This module provides a simplified and robust web interface for users to interact with
the conversational agent powered by Google ADK.
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
    page_title="Web Crawler Assistant",
    page_icon="🌐",
    layout="centered",
    initial_sidebar_state="auto",
)

# Apply custom CSS
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
        width: 100%;
        max-width: 800px;
        margin: 0 auto;
    }
    .stChatMessage {
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .source-info {
        margin-top: 8px;
        padding: 8px;
        background-color: #f0f2f6;
        border-radius: 4px;
        border-left: 3px solid #4169e1;
        font-size: 0.85em;
        color: #444;
    }
    .source-info a {
        color: #1e88e5;
        text-decoration: none;
        overflow-wrap: break-word;
        word-wrap: break-word;
        word-break: break-all;
    }
    .source-info a:hover {
        text-decoration: underline;
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

def display_chat_history():
    """Display the chat message history."""
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🤖"):
            st.markdown(content)

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
    
    # Display user message
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_input)
    
    # Show thinking/loading indicator
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            # Get response with our reliable method
            response_text, crawled_urls = get_response(user_input)
    
        # Display the response
        message_placeholder.markdown(response_text)
        
        # Display crawled URLs if any
        if crawled_urls:
            with st.container():
                st.markdown("""<div class="source-info">
                    <strong>Sources crawled:</strong>
                    </div>""", unsafe_allow_html=True)
                for i, url in enumerate(crawled_urls):
                    st.markdown(f"""<div class="source-info">
                        {i+1}. <a href="{url}" target="_blank">{url}</a>
                        </div>""", unsafe_allow_html=True)
    
    # Add assistant response to chat history (including URL info for later reference)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "crawled_urls": crawled_urls  # Store the crawled URLs with the message
    })

def main():
    """Main function to set up the Streamlit UI."""
    # Initialize session
    init_session()
    
    # App header
    st.title("🌐 Web Crawler Assistant")
    
    # Simple sidebar
    with st.sidebar:
        st.markdown("### About")
        st.markdown("This assistant can search the web for information to answer your questions.")
        
        # Debug mode toggle
        st.session_state.debug = st.checkbox("Debug Mode", value=st.session_state.debug)
        
        # Example queries section
        st.markdown("### Example Queries")
        if st.button("Latest news on SpaceX"):
            process_user_message("What are the latest developments with SpaceX?")
        if st.button("Best programming laptops"):
            process_user_message("What are the best laptops for programming in 2024?")
        if st.button("Compare React vs Angular"):
            process_user_message("Compare React and Angular for web development")
    
    # Main chat area
    with st.container():
        # Display welcome message if this is a new conversation
        if not st.session_state.messages:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown("""
                👋 Hi there! I'm your AI research assistant.
                
                I can search the web to find information on various topics. 
                Ask me something specific like "latest news on climate change" 
                or "compare Python vs JavaScript".
                """)
        
        # Display existing chat history
        display_chat_history()
    
    # Chat input at the bottom
    user_input = st.chat_input("Ask me anything...")
    if user_input:
        process_user_message(user_input)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        if st.session_state.get("debug", False):
            st.exception(e)
