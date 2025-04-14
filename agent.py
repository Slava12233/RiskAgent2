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
from typing import Dict, List, Optional, Any, Union, Tuple
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

# Import the risk analyzer tool
try:
    import risk_analyzer
    RISK_ANALYZER_AVAILABLE = True
    print("Risk analyzer module loaded successfully")
except ImportError:
    RISK_ANALYZER_AVAILABLE = False
    print("Risk analyzer module not available")

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
                        },
                        {
                            "name": "analyze_company_risk",
                            "description": "Analyze a company's risk profile based on its website",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "url": {
                                        "type": "string",
                                        "description": "The URL of the company website to analyze (required)"
                                    },
                                    "company_name": {
                                        "type": "string",
                                        "description": "Name of the company (optional, will be extracted from URL if not provided)"
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
    
    def analyze_company_risk(self, url: str, company_name: Optional[str] = None, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Analyze the financial risk of a company given its website URL.
        
        Args:
            url: URL of the company website
            company_name: Optional company name
            user_id: Identifier for the user making the request
            
        Returns:
            Dict with risk analysis results or error information
        """
        try:
            if not RISK_ANALYZER_AVAILABLE:
                return {
                    "error": "Risk Analysis Unavailable",
                    "message": "The risk analysis module is not available."
                }
            
            # Use risk_analyzer to analyze the company from the URL
            logger.info(f"Analyzing risk for company: {company_name} at URL: {url}")
            analysis_result = risk_analyzer.analyze_company_from_url(url, company_name, user_id)
            
            # Ensure we have all data sources
            if "data_sources" not in analysis_result and "website" in analysis_result:
                analysis_result["data_sources"] = [analysis_result["website"]]
                
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing company risk: {str(e)}")
            return {
                "error": "Analysis Error",
                "message": f"An error occurred during risk analysis: {str(e)}"
            }
    
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

When the user asks about company analysis or risk assessment:
1. Determine if they want financial risk analysis for a company
2. If yes, use the analyze_company_risk tool with the company website URL
3. Present the risk analysis in a clear, structured format
4. Explain the risk factors and recommendations

Guidelines:
- Be conversational and friendly
- Provide accurate information based on crawled content
- Clearly indicate when information comes from the web
- If web crawling fails, explain the issue and suggest alternatives
- For complex topics, break information into clear sections
- When dealing with long webpages, consider using the summarization feature

When using the crawl_webpage tool:
- The "url" parameter is required and should be the full URL including https://
- The "context" parameter is optional and can provide additional information about what to look for
- The "summary" parameter is a boolean that when set to True will return a concise summary of the page instead of the full content. Use this for long articles or when the user specifically asks for a summary.

When using the analyze_company_risk tool:
- The "url" parameter is required and should be the full URL of the company website
- The "company_name" parameter is optional and will be extracted from the URL if not provided"""

            # Send system message
            self.sessions[user_id].send_message(f"SYSTEM: {system_message}")
            
        return self.sessions[user_id]
    
    def detect_url_in_message(self, message: str) -> Optional[str]:
        """
        Detect if the message contains a URL to crawl or a command to scrape a website.
        
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
        
        # Detect domain names (e.g., python.org, github.com)
        domain_pattern = r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|org|net|edu|io|co|ai|app|dev|gov))\b'
        domains = re.findall(domain_pattern, message.lower())
        
        # First check for direct company mentions - higher priority than pattern matching
        message_lower = message.lower()
        
        # Check for action verbs that indicate web crawling intent
        crawl_verbs = ["scrape", "crawl", "visit", "check", "browse", "go to", "open", 
                      "navigate", "explore", "analyze", "view", "read", "extract", "see", 
                      "look at", "get information from", "access"]
        
        has_crawl_intent = any(verb in message_lower for verb in crawl_verbs)
        
        # Only proceed with entity detection if there's a crawling intent
        if has_crawl_intent:
            # Direct company/entity detection - maps entity names to their URLs
            entity_urls = {
                "tesla": "https://www.tesla.com",
                "apple": "https://www.apple.com",
                "microsoft": "https://www.microsoft.com",
                "amazon": "https://www.amazon.com",
                "facebook": "https://www.facebook.com",
                "meta": "https://www.meta.com",
                "google": "https://www.google.com",
                "twitter": "https://twitter.com",
                "x": "https://twitter.com",
                "reddit": "https://www.reddit.com",
                "instagram": "https://www.instagram.com",
                "tiktok": "https://www.tiktok.com",
                "linkedin": "https://www.linkedin.com",
                "netflix": "https://www.netflix.com",
                "disney": "https://www.disney.com",
                "walmart": "https://www.walmart.com",
                "target": "https://www.target.com",
                "nike": "https://www.nike.com",
                "adidas": "https://www.adidas.com",
                "coca cola": "https://www.coca-cola.com",
                "coca-cola": "https://www.coca-cola.com",
                "pepsi": "https://www.pepsi.com",
                "starbucks": "https://www.starbucks.com",
                "mcdonalds": "https://www.mcdonalds.com",
                "ibm": "https://www.ibm.com",
                "intel": "https://www.intel.com",
                "nvidia": "https://www.nvidia.com",
                "amd": "https://www.amd.com",
                "samsung": "https://www.samsung.com",
                "sony": "https://www.sony.com",
                "nyt": "https://www.nytimes.com",
                "new york times": "https://www.nytimes.com",
                "wsj": "https://www.wsj.com",
                "wall street journal": "https://www.wsj.com",
                "bbc": "https://www.bbc.com",
                "cnn": "https://www.cnn.com",
                "fox news": "https://www.foxnews.com",
                "youtube": "https://www.youtube.com",
                "python": "https://www.python.org",
                "github": "https://github.com",
                "stackoverflow": "https://stackoverflow.com",
                "uber": "https://www.uber.com",
                "lyft": "https://www.lyft.com",
                "airbnb": "https://www.airbnb.com",
                "spotify": "https://www.spotify.com",
                "hbo": "https://www.hbo.com",
                "hulu": "https://www.hulu.com"
            }
            
            # Check if any of the entity names are mentioned with a crawl verb nearby
            for entity, url in entity_urls.items():
                if entity in message_lower:
                    # Find position of entity and crawl verbs to ensure they're related
                    entity_pos = message_lower.find(entity)
                    
                    # Check if any crawl verb is within a reasonable distance of the entity
                    # This helps filter out cases like "Tell me about Tesla" vs "Scrape Tesla website"
                    for verb in crawl_verbs:
                        if verb in message_lower:
                            verb_pos = message_lower.find(verb)
                            # If verb is within 30 characters of entity name, it's likely a crawl request
                            if abs(verb_pos - entity_pos) < 30:
                                print(f"Detected entity '{entity}' with URL: {url}")
                                return url
            
            # Check for domain names combined with crawl verbs
            if domains and has_crawl_intent:
                domain = domains[0]  # Take the first domain
                if not domain.startswith(('http://', 'https://')):
                    url = f"https://{domain}"
                    print(f"Constructed URL from domain: {url}")
                    return url
            
            # Check for direct scraping commands with pattern matching
            scrape_patterns = [
                r'(?:scrape|crawl|get|check|visit|open|view|analyze|read|extract|access)\s+(?:the\s+)?(?:website|site|webpage|page|url|content)?\s+(?:of|for|from|about)?\s+([a-zA-Z0-9\s\.]+)',
                r'(?:scrape|crawl|get|check|visit|open|view|analyze|read|extract|access)\s+([a-zA-Z0-9\s\.]+?)(?:\s+website|\s+site|\s+webpage|\s+page|\s+url|\s+content)?',
                r'(?:go\s+to|navigate\s+to|browse|look\s+at)\s+(?:the\s+)?([a-zA-Z0-9\s\.]+?)(?:\s+website|\s+site|\s+webpage|\s+page|\s+url)?'
            ]
            
            # Check against scraping patterns
            for pattern in scrape_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    entity = match.group(1).strip()
                    
                    # Skip common words that don't indicate a real website
                    skip_words = ['it', 'this', 'that', 'these', 'those', 'their', 'some', 'your', 'my', 'our']
                    if entity in skip_words or len(entity) <= 2:
                        continue
                        
                    # Check if the entity matches an entry in our dictionary
                    for known_entity, url in entity_urls.items():
                        if known_entity == entity.lower() or known_entity in entity.lower():
                            print(f"Matched entity '{known_entity}' with URL: {url}")
                            return url
                        
                    # Handle domain names in the entity
                    if '.' in entity and any(tld in entity for tld in ['.com', '.org', '.net', '.io', '.co']):
                        if not entity.startswith(('http://', 'https://')):
                            url = f"https://{entity}"
                            print(f"Formatted URL with https: {url}")
                            return url
                        else:
                            return entity  # Already a full URL
                    
                    # Construct URL for unknown entities
                    if len(entity.split()) <= 3:  # Only auto-construct if it's 1-3 words (likely a company/site name)
                        # Remove spaces and special characters for domain
                        domain = entity.lower()
                        # For multi-word domains, we have options:
                        if ' ' in domain:
                            # 1. Remove spaces: "new york times" -> "newyorktimes"
                            domain_option1 = domain.replace(' ', '')
                            # 2. Replace spaces with hyphens: "new york times" -> "new-york-times" 
                            domain_option2 = domain.replace(' ', '-')
                            
                            # Let's prefer option 1 for common company names
                            domain = domain_option1
                        
                        if '.' not in domain:  # Only append .com if there's no TLD already
                            url = f"https://www.{domain}.com"
                            print(f"Constructed URL from command: {url}")
                            return url
                        else:
                            # If there's already a TLD, make sure it has http/https
                            if not domain.startswith('http'):
                                url = f"https://{domain}"
                                print(f"Formatted URL with https: {url}")
                                return url
                            else:
                                return domain  # Already a full URL
        
        # No clear web crawling intent or website detected
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
            elif function_name == "analyze_company_risk":
                if not RISK_ANALYZER_AVAILABLE:
                    responses.append({
                        "tool_call_id": tool_call.id,
                        "function_response": {"content": "Risk analyzer not available"}
                    })
                    continue
                
                url = args.get("url")
                company_name = args.get("company_name")
                
                print(f"Analyzing company risk for: {url}")
                
                # Call the risk analyzer
                try:
                    analysis_result = self.analyze_company_risk(url, company_name)
                    if "error" in analysis_result:
                        error_message = f"Error analyzing company risk: {analysis_result.get('message', 'Unknown error')}"
                        responses.append({
                            "tool_call_id": tool_call.id,
                            "function_response": {"content": error_message}
                        })
                    else:
                        responses.append({
                            "tool_call_id": tool_call.id,
                            "function_response": {"content": analysis_result['formatted_analysis']}
                        })
                except Exception as e:
                    error_message = f"Error analyzing company risk: {str(e)}"
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
        
        # Check for product-related queries first as they're very common
        product_keywords = [
            "best", "review", "compare", "recommendation", "recommend", "top", "vs", "versus",
            "difference between", "camera", "laptop", "phone", "smartphone", "tablet", "headphones",
            "earbuds", "tv", "monitor", "printer", "router", "device", "gadget", "product", "buy", "purchase"
        ]
        
        # Direct product search patterns - high priority
        product_patterns = [
            r'(?:what|which)(?:\s+(?:is|are))?\s+(?:the\s+)?best\s+(.*?)(?:for|to|in|of|on)',
            r'(?:find|get|show|tell|give)(?:\s+me)?\s+(?:the\s+)?best\s+(.*?)(?:for|to|in|of|on)',
            r'(?:recommended|good|great|top|high[- ]quality)\s+(.*?)(?:for|to|in|of|on)'
        ]
        
        for pattern in product_patterns:
            match = re.search(pattern, message_lower)
            if match:
                return message
        
        # Check for direct product keywords
        if any(keyword in message_lower for keyword in product_keywords):
            return message
        
        # Check for news and current events queries 
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
            "tell me about", "information about", "details on", "facts about",
            "help me", "I need", "looking for", "searching for", 
            "guide to", "tutorial for", "how-to"
        ]
        
        if any(phrase in message_lower for phrase in search_phrases):
            return message
        
        # Check for questions that likely require current information
        question_starters = ["what", "who", "where", "when", "why", "how", "which"]
        if any(message_lower.startswith(starter) for starter in question_starters):
            # Check if the question is about a topic that likely requires web search
            web_topics = ["news", "event", "development", "situation", "conflict", "war", 
                         "technology", "product", "service", "company", "organization",
                         "person", "celebrity", "politician", "athlete", "artist",
                         "movie", "book", "music", "game", "sport", "team",
                         "camera", "laptop", "phone", "device", "software", "hardware",
                         "app", "application", "website", "platform", "tool"]
            
            if any(topic in message_lower for topic in web_topics):
                return message
        
        # If the message contains a question and is relatively long, it's likely a web search
        if ('?' in message) and len(message.split()) >= 5:
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

    def detect_company_risk_query(self, message: str) -> Optional[Dict[str, str]]:
        """
        Check if the message is asking for a company risk analysis.
        
        Args:
            message: The user message to analyze
            
        Returns:
            Dict with company name and URL if found, None otherwise
        """
        # Patterns to detect company risk analysis queries
        risk_patterns = [
            r'risk(?:\s+analysis|\s+assessment|\s+profile)?\s+(?:for|of)\s+(?:company|business)?\s+([A-Za-z0-9\s&]+)',
            r'analyze\s+(?:the\s+)?risk\s+(?:of|for)\s+([A-Za-z0-9\s&]+)',
            r'company\s+risk\s+(?:for|of)\s+([A-Za-z0-9\s&]+)',
            r'financial\s+(?:risk|health)\s+(?:of|for)\s+([A-Za-z0-9\s&]+)',
            r'analyze\s+(?:the\s+)?(?:company|business)\s+([A-Za-z0-9\s&]+)'
        ]
        
        # Check for company mention and URL in the same message
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, message)
        
        # First, check for direct mentions of well-known companies
        well_known_companies = {
            "apple": "https://www.apple.com",
            "microsoft": "https://www.microsoft.com",
            "amazon": "https://www.amazon.com",
            "google": "https://www.google.com",
            "alphabet": "https://www.google.com",
            "tesla": "https://www.tesla.com",
            "meta": "https://www.meta.com",
            "facebook": "https://www.facebook.com",
            "netflix": "https://www.netflix.com",
            "nvidia": "https://www.nvidia.com"
        }
        
        message_lower = message.lower()
        if ("risk" in message_lower or "analyze" in message_lower or "financial" in message_lower):
            # Check for direct company mentions
            for company, url in well_known_companies.items():
                if company in message_lower:
                    # For well-known companies with stock tickers, prefer financial data URLs
                    if RISK_ANALYZER_AVAILABLE:
                        try:
                            # Try to get stock symbol
                            stock_symbol = risk_analyzer.get_stock_symbol(company)
                            if stock_symbol:
                                # Use Yahoo Finance for comprehensive financial data
                                finance_url = f"https://finance.yahoo.com/quote/{stock_symbol}"
                                return {
                                    "company_name": company.capitalize(),
                                    "url": finance_url
                                }
                        except (ImportError, AttributeError):
                            # If risk_analyzer or the function isn't available, use company website
                            pass
                    
                    # Fallback to company website
                    return {
                        "company_name": company.capitalize(),
                        "url": url
                    }
        
        # Next, check for company name patterns
        company_name = None
        for pattern in risk_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                company_name = match.group(1).strip()
                # Check if the extracted company is a well-known one
                for known_company, company_url in well_known_companies.items():
                    if known_company.lower() in company_name.lower():
                        # For well-known companies, use their website URL
                        return {
                            "company_name": known_company.capitalize(),
                            "url": company_url
                        }
                break
        
        # If we have URLs in the message and either a company name or company-related keywords
        if urls and (company_name or 'company' in message.lower() or 'business' in message.lower()):
            # Return the first URL if we have a company name or company-related keywords
            return {
                "company_name": company_name,
                "url": urls[0]
            }
        
        # If we have a company name but no URL, try to construct a URL
        if company_name and not urls:
            # Sanitize the company name for URL
            url_name = company_name.lower().replace(" ", "").replace("&", "and")
            url = f"https://www.{url_name}.com"
            return {
                "company_name": company_name,
                "url": url
            }
        
        return None

    def process_message(self, user_id: str, message: str) -> Tuple[str, List[str]]:
        """
        Process a user message and return a response with crawled URLs.
        
        Args:
            user_id (str): Unique identifier for the user
            message (str): User message
            
        Returns:
            Tuple[str, List[str]]: Response text and list of crawled URLs
        """
        crawled_urls = []
        
        # Check if this is a risk analysis request
        company_info = self.detect_company_risk_query(message)
        if company_info:
            company_name = company_info["company_name"]
            company_url = company_info["url"]
            
            # Process risk analysis request
            logger.info(f"Processing risk analysis for company: {company_name}, URL: {company_url}")
            
            # Analyze the company risk
            risk_result = self.analyze_company_risk(company_url, company_name, user_id)
            
            # Get crawled URLs
            if "data_sources" in risk_result:
                crawled_urls.extend(risk_result["data_sources"])
            else:
                crawled_urls.append(company_url)
            
            # Format the risk analysis for display
            risk_analysis_text = risk_analyzer.format_risk_analysis_for_display(risk_result)
            
            # Prepend a risk icon to the response
            response_text = f"🛡️\n{risk_analysis_text}"
            
            return response_text, crawled_urls
        
        # Check for simple greetings or very short messages first
        simple_greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        if message.lower().strip() in simple_greetings:
            greeting_response = f"Hello! I'm your web research assistant. What would you like to know?"
            return greeting_response, crawled_urls  # No URLs crawled for greetings
        
        if len(message.strip()) < 5:
            short_response = "Please provide more details about what you'd like to know."
            return short_response, crawled_urls  # No URLs crawled for short messages
        
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
                
                response = self.get_or_create_session(user_id).send_message(prompt)
                return response.text, crawled_urls
                
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
                
                response = self.get_or_create_session(user_id).send_message(prompt)
                return response.text, crawled_urls
            
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
                    
                    response = self.get_or_create_session(user_id).send_message(prompt)
                    return response.text, crawled_urls
            except Exception as e:
                print(f"Error processing web search query: {str(e)}")
                # Continue to other methods if search query fails
                pass
        
        # 4. Default to regular chat without web crawling if all other methods fail
        print("Using standard processing without web crawling")
        # Send the message directly to the model
        response = self.get_or_create_session(user_id).send_message(message)
        return response.text, crawled_urls


# Create a singleton instance
crawler_agent = WebCrawlerAgent()


def get_agent() -> WebCrawlerAgent:
    """Get the singleton agent instance."""
    return crawler_agent
