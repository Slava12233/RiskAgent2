"""
Agent implementation for web crawling conversational agent.

This module defines the LLM agent powered by Gemini that will handle
conversations and utilize web crawling capabilities.
"""

import os
import sys
import re
import asyncio
import json
import random
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
from dotenv import load_dotenv
import google.generativeai as genai
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Import crawlers - simple crawler is now primary, original as fallback
try:
    # Import the simple crawler as the primary crawler
    import simple_crawler
    SIMPLE_CRAWLER_AVAILABLE = True
    print("Simple crawler module loaded successfully")
except ImportError:
    SIMPLE_CRAWLER_AVAILABLE = False
    print("Simple crawler module not available")

# Import the original crawler as a fallback
from tools.web_crawler import (
    crawl_webpage_sync, 
    crawl_multiple_webpages_sync as original_crawl_multiple_webpages_sync,
    detect_website_type
)

from utils.error_handling import get_user_friendly_error_message
# Use simple_crawler's search if available, otherwise the original
if SIMPLE_CRAWLER_AVAILABLE:
    get_relevant_urls = simple_crawler.get_relevant_urls
else:
    from tools.search_api import get_relevant_urls

# Load environment variables from .env file
load_dotenv()

# Constants
DEFAULT_MODEL = "gemini-1.5-flash"

# Configure Google API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("\033[91mERROR: GOOGLE_API_KEY environment variable is not set.\033[0m")
    print("Please create a .env file in the project root with your API key:")
    print("  GOOGLE_API_KEY=your_api_key_here")
    print("Or set it as an environment variable before running the application.")
    sys.exit(1)

# Configure Google AI
genai.configure(api_key=GOOGLE_API_KEY)

class WebCrawlerAgent:
    """Main agent class that handles conversation and web crawling."""
    
    def __init__(self):
        """Initialize the agent with Gemini model."""
        try:
            # Initialize the model
            self.model = genai.GenerativeModel(DEFAULT_MODEL)
            
            # Define tools for the model
            self.tools = [
                {
                    "function_declarations": [
                        {
                            "name": "crawl_webpage",
                            "description": "Crawl a webpage and return its content as markdown",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "url": {
                                        "type": "string",
                                        "description": "The URL to crawl (required)"
                                    },
                                    "context": {
                                        "type": "string",
                                        "description": "Additional context or specific information to look for (optional)"
                                    },
                                    "summary": {
                                        "type": "boolean",
                                        "description": "Whether to return only a summary of the page (optional, default: False)"
                                    }
                                },
                                "required": ["url"]
                            }
                        }
                    ]
                }
            ]
            
            # Store active sessions
            self.sessions = {}
            
        except Exception as e:
            print(f"\033[91mERROR: Failed to initialize the agent: {str(e)}\033[0m")
            print("This might be due to an invalid or expired API key.")
            sys.exit(1)
    
    def get_or_create_session(self, user_id: str):
        """
        Get existing chat session for user or create new one.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            ChatSession: The chat session for this user
        """
        if user_id not in self.sessions:
            # First create an empty chat session
            self.sessions[user_id] = self.model.start_chat(history=[])
            
            # Add the system message as a regular message exchange
            system_message = """You are a helpful web research assistant. 
                
You can have natural conversations with users and help them find information from the web when needed.

When the user asks about information that might be on the web:
1. Determine if you need to search the web to answer accurately
2. If yes, use the crawl_webpage tool to fetch relevant information
3. Formulate a helpful response based on the crawled content
4. If the information is already within your knowledge, respond directly

Guidelines:
- Be conversational and friendly
- Provide accurate information based on crawled content
- Clearly indicate when information comes from the web
- If web crawling fails, explain the issue and suggest alternatives
- For complex topics, break information into clear sections
- When dealing with long webpages, consider using the summarization feature
- When comparing information from multiple sources, highlight similarities and differences

When using the crawl_webpage tool:
- The "url" parameter is required and should be the full URL including https://
- The "context" parameter is optional and can provide additional information about what to look for
- The "summary" parameter is a boolean that when set to True will return a concise summary of the page instead of the full content. Use this for long articles or when the user specifically asks for a summary."""

            # Send system message
            self.sessions[user_id].send_message(f"SYSTEM: {system_message}")
            
        return self.sessions[user_id]
    
    def detect_url_in_message(self, message: str) -> Optional[str]:
        """
        Detect if the message contains a URL to crawl.
        
        Args:
            message: The user message
            
        Returns:
            Optional[str]: The detected URL or None
        """
        # URL pattern matching for common URL formats
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, message)
        
        # If we found a URL directly in the message, return it
        if urls:
            return urls[0]  # Return the first URL
        
        # Special handling for specific keywords regardless of web intent
        message_lower = message.lower()
        if "python.org" in message_lower:
            return "https://www.python.org"
        elif "react" in message_lower and "framework" in message_lower:
            return "https://www.react.dev"
        elif "javascript" in message_lower and "language" in message_lower:
            return "https://developer.mozilla.org/en-US/docs/Web/JavaScript"
        
        # Check if message has keywords related to web browsing/crawling
        has_web_keywords = any(keyword in message_lower for keyword in [
            "website", "webpage", "site", "url", "link", "browse", "web",
            "visit", "open", "navigate", "go to", "check", "look at", "research",
            "content", "page", "search", "find", "information", "details",
            "according to"
        ])
        
        return None
    
    def extract_summary_flag(self, message: str) -> bool:
        """Check if the user wants a summary."""
        summary_keywords = ["summary", "summarize", "brief", "overview", "tldr", "short version"]
        return any(keyword in message.lower() for keyword in summary_keywords)
    
    def detect_multiple_sites_request(self, user_message: str) -> List[str]:
        """
        Detect if the user is requesting information from multiple websites
        and return a list of relevant websites based on the message.
        
        Args:
            user_message: The user's message
            
        Returns:
            A list of detected URLs or keywords
        """
        # Check if the message contains keywords suggesting a comparison or multiple sources
        comparison_pattern = re.compile(r'\b(compare|comparison|versus|vs\.?|different|sources|multiple|websites|sites)\b', 
                                        re.IGNORECASE)
        news_pattern = re.compile(r'\b(news|latest|recent|update|current events)\b', re.IGNORECASE)
        
        is_comparison = bool(comparison_pattern.search(user_message))
        is_news = bool(news_pattern.search(user_message))
        
        if is_comparison or is_news:
            # Extract the main topic from the user message for relevant searches
            topics = self._extract_query_topics(user_message)
            if topics:
                # Use our search API to find relevant websites
                topic_str = " ".join(topics)
                category = self._determine_query_category(user_message)
                
                urls = get_relevant_urls(topic_str, 
                                        num_results=5,  # Limit to 5 URLs to avoid excessive crawling
                                        category=category)
                
                return urls if urls else []
            
        return []

    def extract_main_topic(self, message: str) -> str:
        """
        Extract the main topic from a message.
        
        Args:
            message: The message to extract from
            
        Returns:
            str: The extracted main topic or empty string if none found
        """
        # Remove common stop words to focus on key terms
        stop_words = ["the", "a", "an", "is", "are", "what", "tell", "me", "about", 
                      "latest", "news", "on", "in", "of", "for", "how", "why", "when",
                      "who", "which", "where", "can", "you", "get", "find", "search"]
        
        words = message.lower().split()
        topic_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        if not topic_words:
            return ""
        
        # Use the most frequent relevant words as the topic
        from collections import Counter
        word_counts = Counter(topic_words)
        common_words = [word for word, count in word_counts.most_common(3)]
        
        return " ".join(common_words)

    def find_relevant_websites(self, user_message: str, num_urls: int = 5) -> List[str]:
        """
        Find relevant websites based on user message using the search API.
        
        Args:
            user_message: The user's message
            num_urls: Maximum number of URLs to return
            
        Returns:
            List of relevant website URLs
        """
        # Detect the category from the query
        category = self._determine_query_category(user_message)
        
        # Extract the main topic(s) from the user message
        topics = self._extract_query_topics(user_message)
        topic_str = " ".join(topics) if topics else user_message
        
        # Get relevant URLs from search API
        try:
            urls = get_relevant_urls(topic_str, num_results=num_urls, category=category)
            if urls:
                return urls
        except Exception as e:
            print(f"Error using search API: {str(e)}")
        
        # Fallback to old method if search API fails
        return self._get_websites_by_category(category, topic_str, topics, num_urls)
    
    def _determine_query_category(self, query: str) -> str:
        """
        Determine the category of a query.
        
        Args:
            query: The user's query
            
        Returns:
            Category string: "tech", "product", "news", "travel", "health", or "general"
        """
        query = query.lower()
        
        # Look for specific news entities first (highest priority)
        news_entities = ["conflict", "war", "middle east", "gaza", "israel", "ukraine", "russia", 
                         "election", "politics", "president", "government", "minister"]
        if any(entity in query for entity in news_entities):
            return "news"
        
        # Check for product-related terms (high priority)
        product_terms = ["review", "product", "laptop", "phone", "smartphone", "camera", 
                         "headphones", "best", "top", "compare", "vs", "versus", "better", 
                         "which", "recommend", "buy", "purchase", "affordable"]
        if any(term in query for term in product_terms):
            # Special check for programming laptops - this should be product not tech
            if "laptop" in query or "computer" in query or "device" in query:
                return "product"
        
        # Check for programming and technology terms
        tech_terms = ["programming", "code", "python", "javascript", "html", "css", 
                      "api", "framework", "software", "app", "development", "github", 
                      "coding", "algorithm", "developer", "web development"]
        if any(term in query for term in tech_terms):
            return "tech"
        
        # Check again for product-related terms if not matched as tech
        if any(term in query for term in product_terms):
            return "product"
        
        # Check for news-related terms
        news_terms = ["news", "latest", "current", "recent", "today", "yesterday", 
                      "week", "breaking", "update", "headline", "report", "announcement",
                      "development"]
        if any(term in query for term in news_terms):
            return "news"
        
        # Check for travel-related terms
        travel_terms = ["travel", "vacation", "holiday", "destination", "trip", 
                        "flight", "hotel", "resort", "tourist", "tourism", "visit"]
        if any(term in query for term in travel_terms):
            return "travel"
        
        # Check for health-related terms
        health_terms = ["health", "medical", "medicine", "disease", "symptom", 
                        "treatment", "doctor", "hospital", "therapy", "diagnosis", 
                        "cure", "workout", "fitness", "diet", "nutrition"]
        if any(term in query for term in health_terms):
            return "health"
        
        # Default to general category
        return "general"
    
    def _extract_query_topics(self, query: str) -> List[str]:
        """
        Extract main topics from a query by removing stopwords.
        
        Args:
            query: The user's query
            
        Returns:
            List of main topic words
        """
        # Download NLTK resources if not already present
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
        
        try:
            # Tokenize and remove stopwords
            query = re.sub(r'[^\w\s]', ' ', query.lower())  # Remove punctuation
            tokens = word_tokenize(query)
            stop_words = set(stopwords.words('english'))
            
            # Additional words to filter out
            custom_stops = {"tell", "me", "about", "information", "find", "get", "know", "want", "need", "what", "how", "why", "who", "when", "where", "explain", "describe", "give", "show"}
            stop_words.update(custom_stops)
            
            # Filter out stopwords and short words
            topics = [word for word in tokens if word not in stop_words and len(word) > 2]
            
            # Return most important words (first 3-5 depending on length)
            return topics[:min(5, len(topics))]
        except Exception as e:
            print(f"Error using NLTK tokenization: {str(e)}")
            # Fallback: simple word split and basic filtering
            query = re.sub(r'[^\w\s]', ' ', query.lower())  # Remove punctuation
            words = query.split()
            
            # Basic stop words list
            basic_stops = {"a", "an", "the", "is", "are", "was", "were", "be", "been", "being", 
                         "in", "on", "at", "to", "for", "with", "by", "about", "like", "of", 
                         "from", "that", "this", "these", "those", "it", "its", "tell", "me", 
                         "i", "you", "he", "she", "they", "we", "my", "your", "his", "her", 
                         "their", "our", "what", "when", "where", "why", "how", "which", "who"}
            
            # Filter out stop words and short words
            topics = [word for word in words if word not in basic_stops and len(word) > 2]
            
            # Return most important words (first 3-5 depending on length)
            return topics[:min(5, len(topics))]
    
    def _extract_topics_from_query(self, query: str) -> List[str]:
        """
        Alias for _extract_query_topics for backward compatibility with tests.
        
        Args:
            query: The user's query
            
        Returns:
            List of main topic words
        """
        return self._extract_query_topics(query)
    
    def _get_websites_by_category(self, category: str, topic_str: str, topics: List[str], num_results: int = 5) -> List[str]:
        """
        Get a list of recommended websites based on the category and topics.
        This is a fallback method if the search API fails.
        
        Args:
            category: The category of the query
            topic_str: String representation of the topic
            topics: List of topic words
            num_results: Maximum number of URLs to return
            
        Returns:
            List of website URLs
        """
        # Create a mapping of categories to websites
        category_websites = {
            "tech": [
                "https://stackoverflow.com/questions/tagged/{topic}",
                "https://github.com/topics/{topic}",
                "https://dev.to/t/{topic}",
                "https://www.freecodecamp.org/news/{topic}",
                "https://medium.com/tag/{topic}",
                "https://hackernoon.com/tagged/{topic}",
                "https://www.reddit.com/r/{topic}"
            ],
            "product": [
                "https://www.cnet.com/search/?query={topic}",
                "https://www.techradar.com/search?searchTerm={topic}",
                "https://www.theverge.com/search?q={topic}",
                "https://www.tomsguide.com/search?searchTerm={topic}",
                "https://www.rtings.com/search?query={topic}",
                "https://www.amazon.com/s?k={topic}",
                "https://www.reddit.com/r/gadgets/search/?q={topic}"
            ],
            "news": [
                "https://news.google.com/search?q={topic}",
                "https://www.bbc.com/news/search?q={topic}",
                "https://www.reuters.com/search/news?blob={topic}",
                "https://apnews.com/search?q={topic}",
                "https://www.aljazeera.com/search/{topic}",
                "https://www.cnn.com/search?q={topic}",
                "https://www.nytimes.com/search?query={topic}"
            ],
            "travel": [
                "https://www.tripadvisor.com/Search?q={topic}",
                "https://www.lonelyplanet.com/search?q={topic}",
                "https://www.booking.com/searchresults.html?ss={topic}",
                "https://www.expedia.com/Hotel-Search?destination={topic}",
                "https://wikitravel.org/en/Special:Search?search={topic}",
                "https://www.kayak.com/explore/{topic}",
                "https://www.reddit.com/r/travel/search/?q={topic}"
            ],
            "health": [
                "https://www.webmd.com/search/search_results/default.aspx?query={topic}",
                "https://www.mayoclinic.org/search/search-results?q={topic}",
                "https://medlineplus.gov/search.html?query={topic}",
                "https://www.healthline.com/search?q1={topic}",
                "https://www.nih.gov/search/{topic}",
                "https://www.cdc.gov/search/?query={topic}",
                "https://www.reddit.com/r/health/search/?q={topic}"
            ],
            "general": [
                "https://en.wikipedia.org/wiki/{topic}",
                "https://www.britannica.com/search?query={topic}",
                "https://www.reddit.com/search/?q={topic}",
                "https://www.quora.com/search?q={topic}",
                "https://medium.com/search?q={topic}",
                "https://duckduckgo.com/?q={topic}",
                "https://www.wikihow.com/wikiHowTo?search={topic}"
            ]
        }
        
        # Get websites for the category
        websites = category_websites.get(category, category_websites["general"])
        
        # Format the URLs with the main topic
        formatted_urls = []
        
        # Use the first topic as the main search term if available
        main_topic = topics[0] if topics else ""
        
        if main_topic:
            # Format each URL template with the main topic
            formatted_urls = [url.format(topic=main_topic) for url in websites]
            
            # If multiple topics available, add some combined search URLs
            if len(topics) > 1:
                combined_topic = "+".join(topics[:3])
                general_search_urls = [
                    f"https://www.google.com/search?q={combined_topic}",
                    f"https://duckduckgo.com/?q={combined_topic}",
                    f"https://en.wikipedia.org/wiki/Special:Search?search={combined_topic}"
                ]
                formatted_urls.extend(general_search_urls)
        else:
            # Use generic URLs if no specific topic found
            formatted_urls = [
                "https://en.wikipedia.org/wiki/Main_Page",
                "https://www.britannica.com/",
                "https://www.wolframalpha.com/",
                "https://www.reddit.com/",
                "https://news.google.com/",
                "https://www.bbc.com/news"
            ]
        
        # Return unique URLs up to the requested number
        unique_urls = list(dict.fromkeys(formatted_urls))
        return unique_urls[:num_results]

    def process_multiple_sites(self, urls: List[str], message: str) -> str:
        """
        Process multiple websites and return consolidated information.
        
        Args:
            urls: List of URLs to process
            message: Original user message
            
        Returns:
            str: Consolidated information from multiple sites
        """
        # Determine if summary is requested
        summary = self.extract_summary_flag(message)
        
        try:
            print(f"Crawling multiple webpages: {urls}")
            # Use the new crawl_multiple_webpages_sync function
            combined_content = original_crawl_multiple_webpages_sync(urls, context=message, summary=True)
            
            # Add a sources section at the beginning
            sources_section = "## Sources Being Crawled\n"
            for i, url in enumerate(urls):
                sources_section += f"{i+1}. [{url}]({url})\n"
            
            return f"{sources_section}\n\n{combined_content}"
        except Exception as e:
            print(f"Error processing multiple sites: {str(e)}")
            
            # Fallback to individual crawling if the batch method fails
            results = []
            
            # Add a sources section at the beginning
            sources_section = "## Sources Being Crawled\n"
            for i, url in enumerate(urls):
                sources_section += f"{i+1}. [{url}]({url})\n"
            results.append(sources_section)
            
            for url in urls:
                try:
                    print(f"Crawling webpage: {url}")
                    content = crawl_webpage_sync(url, context=message, summary=True)
                    results.append(f"## Information from {url}\n\n{content}")
                except Exception as e:
                    results.append(f"## Error accessing {url}\n\n{str(e)}")
            
            # Combine all results
            combined_content = "\n\n".join(results)
            return combined_content
    
    def process_tool_calls(self, tool_calls: list):
        """Process function tool calls from the model."""
        responses = []
        
        for tool_call in tool_calls:
            function_call = tool_call.function_call
            function_name = function_call.name
            
            # Extract arguments
            args = function_call.args
            
            if function_name == "crawl_webpage":
                url = args.get("url")
                context = args.get("context")
                summary = args.get("summary", False)
                
                print(f"Crawling webpage: {url}")
                
                # Call the crawler function
                try:
                    result = crawl_webpage_sync(url, context, summary)
                    responses.append({
                        "tool_call_id": tool_call.id,
                        "function_response": {"content": result}
                    })
                except Exception as e:
                    error_message = f"Error crawling webpage: {str(e)}"
                    responses.append({
                        "tool_call_id": tool_call.id,
                        "function_response": {"content": error_message}
                    })
            else:
                responses.append({
                    "tool_call_id": tool_call.id,
                    "function_response": {"content": "Function not implemented"}
                })
                
        return responses
    
    def detect_web_search_query(self, message: str) -> Optional[str]:
        """
        Detect if the message is a search query that requires web information.
        
        Args:
            message: The user message
            
        Returns:
            Optional[str]: The detected search query or None
        """
        message_lower = message.lower()
        
        # Check for news and current events queries first
        news_keywords = ["news", "latest", "recent", "current", "update", "development", "conflict", "war", "politics", "election"]
        news_entities = ["israel", "gaza", "ukraine", "russia", "middle east", "election", "president", "prime minister"]
        
        # If the message contains news keywords and entities, it's likely a news query
        if any(keyword in message_lower for keyword in news_keywords) and any(entity in message_lower for entity in news_entities):
            return message
        
        # Common patterns for web search queries
        search_patterns = [
            (r"find (?:me |the )?(.*?)(?:in|near|at) (.*)", "find_location"),
            (r"best (.*?)(?:in|near|at) (.*)", "best_in_location"),
            (r"top (\d+) (.*?)(?:in|near|at) (.*)", "top_n_in_location"),
            (r"where (?:can|could) I (.*?)(?:in|near|at) (.*)", "where_in_location"),
            (r"how (?:can|could|do) I (.*?)(?:in|near|at) (.*)", "how_in_location"),
            (r"(?:search for|look up|show me) (.*?)(?:about|related to) (.*)", "search_about"),
            (r"compare (.*?) (?:and|vs|versus) (.*?)(?:in|near|at)? ?(.*)?", "compare"),
            (r"what (?:is|are) the latest (.*?)(?:in|on|about) (.*)", "latest_info"),
            (r"what (?:is|are) the (?:current|recent) (.*?)(?:in|on|about) (.*)", "current_info")
        ]
        
        for pattern, query_type in search_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Extract components based on query type
                if query_type == "find_location" or query_type == "best_in_location":
                    item = match.group(1).strip()
                    location = match.group(2).strip()
                    return f"{item} in {location}"
                elif query_type == "top_n_in_location":
                    count = match.group(1).strip()
                    item = match.group(2).strip()
                    location = match.group(3).strip()
                    return f"top {count} {item} in {location}"
                elif query_type == "where_in_location" or query_type == "how_in_location":
                    action = match.group(1).strip()
                    location = match.group(2).strip()
                    return f"{action} in {location}"
                elif query_type == "search_about":
                    item = match.group(1).strip()
                    topic = match.group(2).strip()
                    return f"{item} about {topic}"
                elif query_type == "compare":
                    item1 = match.group(1).strip()
                    item2 = match.group(2).strip()
                    location = match.group(3).strip() if match.group(3) else ""
                    if location:
                        return f"compare {item1} and {item2} in {location}"
                    else:
                        return f"compare {item1} and {item2}"
                elif query_type in ["latest_info", "current_info"]:
                    topic = match.group(1).strip()
                    context = match.group(2).strip()
                    return f"latest {topic} in {context}"
        
        # Check for common search phrases
        search_phrases = [
            "find me", "where can I find", "best places", "top places", 
            "recommend", "suggestions for", "where is", "how to get to",
            "reviews of", "ratings for", "popular", "nearest", "closest",
            "what is", "who is", "when is", "where is", "why is", "how is",
            "latest news", "current events", "recent developments", "updates on",
            "tell me about", "information about", "details on", "facts about"
        ]
        
        if any(phrase in message_lower for phrase in search_phrases):
            return message
        
        # Check for questions that likely require current information
        question_starters = ["what", "who", "where", "when", "why", "how"]
        if any(message_lower.startswith(starter) for starter in question_starters):
            # Check if the question is about a topic that likely requires web search
            web_topics = ["news", "event", "development", "situation", "conflict", "war", 
                         "technology", "product", "service", "company", "organization",
                         "person", "celebrity", "politician", "athlete", "artist",
                         "movie", "book", "music", "game", "sport", "team"]
            
            if any(topic in message_lower for topic in web_topics):
                return message
        
        return None

    def process_web_search_query(self, query: str) -> str:
        """
        Process a web search query and return information from relevant websites.
        
        Args:
            query: The search query
            
        Returns:
            str: The combined information from relevant websites
        """
        # Find relevant websites based on the query
        websites = self.find_relevant_websites(query)
        
        if not websites:
            return "I couldn't find relevant websites for your query. Could you try rephrasing or providing more details?"
        
        # Crawl the websites and get the combined content
        try:
            print(f"Websites: {websites}")
            combined_content = original_crawl_multiple_webpages_sync(websites, context=query, summary=True)
            return combined_content
        except Exception as e:
            print(f"Error crawling websites: {str(e)}")
            return f"Error retrieving information: {str(e)}"

    def process_message(self, user_id: str, message: str) -> Union[str, tuple]:
        """
        Process a message from the user and get agent response.
        
        Args:
            user_id: Unique identifier for the user
            message: The message text from the user
            
        Returns:
            Union[str, tuple]: Either the agent's response text or a tuple of (response_text, list_of_crawled_urls)
        """
        try:
            # Get or create session
            session = self.get_or_create_session(user_id)
            
            # Track crawled URLs
            crawled_urls = []
            
            # Check for simple greetings or very short messages first
            simple_greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
            if message.lower().strip() in simple_greetings:
                greeting_response = f"Hello! I'm your web research assistant. What would you like to know?"
                return (greeting_response, crawled_urls)  # No URLs crawled for greetings
            
            if len(message.strip()) < 5:
                short_response = "Please provide more details about what you'd like to know."
                return (short_response, crawled_urls)  # No URLs crawled for short messages
            
            # Try different ways to process the message
            
            # 1. Check if message has a direct URL
            url = self.detect_url_in_message(message)
            if url:
                print(f"Using simple crawler for URL: {url}")
                try:
                    if SIMPLE_CRAWLER_AVAILABLE:
                        # Use simple crawler with retries
                        content = simple_crawler.crawl_webpage(url, context=message, summary=self.extract_summary_flag(message))
                        crawled_urls.append(url)
                    else:
                        # Fall back to original crawler
                        content = crawl_webpage_sync(url, context=message, summary=self.extract_summary_flag(message))
                        crawled_urls.append(url)
                    
                    # Generate response from the model using the content
                    prompt = f"""Based on the provided content about {url}, please provide an informative response
                    to the user's query: "{message}"
                    
                    Content:
                    {content}
                    
                    Provide a comprehensive response addressing the user's query specifically. 
                    If the content doesn't fully answer the query, acknowledge the limitations.
                    """
                    
                    response = session.send_message(prompt)
                    return (response.text, crawled_urls)
                    
                except Exception as e:
                    print(f"Error using direct URL: {str(e)}")
                    # Continue to other methods if direct URL crawling fails
                    pass
            
            # 2. Check if multiple sites information is requested
            multiple_sites = self.detect_multiple_sites_request(message)
            if multiple_sites:
                print(f"Using simple crawler for multiple URLs: {multiple_sites}")
                try:
                    # Limit to first 3 URLs to reduce load
                    urls_to_crawl = multiple_sites[:3]
                    crawled_urls.extend(urls_to_crawl)
                    
                    if SIMPLE_CRAWLER_AVAILABLE:
                        # Use simple crawler with reduced concurrency and better error handling
                        content = simple_crawler.crawl_multiple_webpages_sync(
                            urls_to_crawl,
                            context=message,
                            summary=True
                        )
                    else:
                        # Fall back to original crawler
                        content = original_crawl_multiple_webpages_sync(
                            urls_to_crawl,
                            context=message,
                            summary=True
                        )
                    
                    # Generate response from the model using the combined content
                    prompt = f"""Based on the provided content from multiple websites, please provide an informative response
                    to the user's query: "{message}"
                    
                    Content:
                    {content}
                    
                    Provide a comprehensive response addressing the user's query specifically.
                    If the content doesn't fully answer the query, acknowledge the limitations.
                    Summarize the key information from all sources and note any contradictions or differences between them.
                    """
                    
                    response = session.send_message(prompt)
                    return (response.text, crawled_urls)
                    
                except Exception as e:
                    print(f"Error processing multiple sites: {str(e)}")
                    # Continue to other methods if multiple sites crawling fails
                    pass
            
            # 3. Check if message is a web search query
            search_query = self.detect_web_search_query(message)
            if search_query:
                print(f"Using simple crawler's search for: {search_query}")
                try:
                    # Get relevant URLs using simple crawler if available
                    if SIMPLE_CRAWLER_AVAILABLE:
                        search_urls = simple_crawler.get_relevant_urls(search_query, num_results=3)
                        if search_urls:
                            print(f"Using simple crawler for search results URLs: {search_urls}")
                            crawled_urls.extend(search_urls)
                            content = simple_crawler.crawl_multiple_webpages_sync(
                                search_urls,
                                context=message,
                                summary=True
                            )
                    else:
                        # Fall back to original methods
                        search_urls = get_relevant_urls(search_query, num_results=3)
                        if search_urls:
                            print(f"Using original crawler for search results URLs: {search_urls}")
                            crawled_urls.extend(search_urls)
                            content = original_crawl_multiple_webpages_sync(
                                search_urls,
                                context=message,
                                summary=True
                            )
                    
                    if search_urls:
                        # Generate response from the model using the content
                        prompt = f"""Based on the provided content from a web search for "{search_query}", 
                        please provide an informative response to the user's query: "{message}"
                        
                        Content:
                        {content}
                        
                        Provide a comprehensive response addressing the user's query specifically.
                        If the content doesn't fully answer the query, acknowledge the limitations.
                        """
                        
                        response = session.send_message(prompt)
                        return (response.text, crawled_urls)
                except Exception as e:
                    print(f"Error processing web search query: {str(e)}")
                    # Continue to other methods if search query fails
                    pass
            
            # 4. Default to regular chat without web crawling if all other methods fail
            print("Using standard processing without web crawling")
            # Send the message directly to the model
            response = session.send_message(message)
            return (response.text, crawled_urls)
            
        except Exception as e:
            print(f"Error in process_message: {str(e)}")
            error_message = get_user_friendly_error_message(str(e))
            return (f"I encountered an error: {error_message}. Please try a different query or rephrase your question.", [])


# Create a singleton instance
crawler_agent = WebCrawlerAgent()


def get_agent() -> WebCrawlerAgent:
    """Get the singleton agent instance."""
    return crawler_agent
