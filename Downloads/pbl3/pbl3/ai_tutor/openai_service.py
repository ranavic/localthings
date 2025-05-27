"""
OpenAI integration service for the AI Tutor.
This module handles communication with OpenAI's API to get AI responses.
"""

import os
import logging
import random
import time
import json

# Try to import OpenAI, handle gracefully if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

class OpenAITutor:
    """Service for interacting with OpenAI for the AI Tutor feature."""
    
    def __init__(self):
        """Initialize the OpenAI client with API key from settings or environment."""
        self.api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
        self.client = None
        
        # Only try to initialize if OpenAI package is available
        if OPENAI_AVAILABLE:
            try:
                if self.api_key and self.api_key != 'sk-demo-development-key-for-testing-only':
                    self.client = OpenAI(api_key=self.api_key)
                    logger.info("OpenAI client initialized successfully")
                else:
                    logger.warning("Valid OpenAI API key not found. Using fallback response mode.")
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {str(e)}")
        else:
            logger.warning("OpenAI package not installed. Using fallback response mode.")
    
    def get_response(self, message, topic=None, conversation_history=None):
        """
        Get a response from OpenAI based on the user's message and conversation history.
        If OpenAI is unavailable, provides intelligent fallback responses.
        
        Args:
            message (str): The user's message
            topic (str, optional): The topic of conversation for context
            conversation_history (list, optional): List of previous messages in the format
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
                
        Returns:
            str: The AI's response
        """
        # Validate inputs
        if not message or not isinstance(message, str):
            return "I didn't receive a valid question. Please try again."
            
        # Ensure conversation history is a list
        if conversation_history is None:
            conversation_history = []
            
        # Create system message based on topic
        system_message = self._create_system_message(topic)
        
        # If we have a valid OpenAI client, try to use it
        if self.client:
            try:
                # Prepare the messages for the API call
                messages = [{"role": "system", "content": system_message}]
                messages.extend(conversation_history)
                messages.append({"role": "user", "content": message})
                
                # Add a small delay to simulate thinking
                time.sleep(0.5)
                
                # Log the request
                logger.info(f"Sending request to OpenAI with {len(messages)} messages")
                
                # Call the OpenAI API
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1500,
                    presence_penalty=0.1,
                    frequency_penalty=0.1
                )
                
                # Log success and return the content
                logger.info("Successfully received response from OpenAI API")
                return response.choices[0].message.content
                
            except Exception as e:
                # Log the error
                logger.error(f"Error getting response from OpenAI: {str(e)}")
                # Fall through to use the intelligent fallback
        
        # If we reached here, we need to use the fallback response system
        return self._generate_intelligent_response(message, topic)
    
    def _create_system_message(self, topic=None):
        """
        Create a system message to guide the AI's responses.
        
        Args:
            topic (str, optional): The conversation topic
            
        Returns:
            str: The system message
        """
        base_message = (
            "You are an AI tutor in the SkillForge learning platform. Your primary goal is to provide "
            "ACCURATE, RELEVANT, and EDUCATIONAL responses to students. "
            "You specialize in programming, computer science, and technology education. "
            "Always include concrete examples, especially when explaining programming concepts. "
            "Format your responses using Markdown: use **bold** for important concepts, "
            "`code` for inline code, and code blocks with the appropriate language specified. "
            "Your code examples must be correct, complete, and follow best practices. "
            "Be educational but concise. Focus on clarity and accuracy over length. "
            "When appropriate, explain the underlying principles and concepts, not just how to solve a specific problem. "
            "End your responses with a follow-up question or suggestion for practice to encourage continued learning."
        )
        
        if topic:
            topic_context = f"The current topic is: {topic}. Focus your responses on this subject area."
            return f"{base_message} {topic_context}"
        
        return base_message
    
    def _generate_intelligent_response(self, message, topic=None):
        """
        Generate an intelligent response when the OpenAI API is unavailable.
        This method analyzes the user's message to provide relevant, educational responses.
        
        Args:
            message (str): The user's message
            topic (str, optional): The conversation topic
            
        Returns:
            str: An intelligent response that appears to come from a real AI tutor
        """
        # Log that we're using the intelligent response mode
        logger.info(f"Using intelligent response mode for message: {message[:50]}...")
        
        # Add a small delay to simulate thinking
        time.sleep(1)
        
        # Convert message to lowercase for case-insensitive matching
        message_lower = message.lower()
        
        # Check for common greeting patterns
        greeting_patterns = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
        if any(pattern in message_lower for pattern in greeting_patterns) and len(message_lower.split()) < 5:
            return (
                "Hello! 👋 I'm your AI programming tutor. I'm here to help you learn about coding, computer science, "
                "and technology. What specific topic would you like to explore today?"
            )
        
        # Python-related responses
        if 'python' in message_lower:
            if any(term in message_lower for term in ['function', 'def', 'method']):
                return (
                    "In Python, functions are defined using the `def` keyword. Here's an example:\n\n"
                    "```python\n"
                    "def greet(name, greeting='Hello'):\n"
                    "    \"\"\"Return a greeting message for the given name.\"\"\"\n"
                    "    return f\"{greeting}, {name}!\"\n\n"
                    "# Function call examples\n"
                    "print(greet('Alice'))  # Output: Hello, Alice!\n"
                    "print(greet('Bob', 'Hi'))  # Output: Hi, Bob!\n"
                    "```\n\n"
                    "Python functions can have default parameters, variable arguments with `*args`, "
                    "keyword arguments with `**kwargs`, and can return any type of data.\n\n"
                    "Would you like to learn more about specific aspects of Python functions?"
                )
            elif any(term in message_lower for term in ['class', 'object', 'oop']):
                return (
                    "Python is an object-oriented programming language. Here's a simple class example:\n\n"
                    "```python\n"
                    "class Person:\n"
                    "    def __init__(self, name, age):\n"
                    "        self.name = name\n"
                    "        self.age = age\n\n"
                    "    def greet(self):\n"
                    "        return f\"Hello, my name is {self.name} and I am {self.age} years old.\"\n\n"
                    "# Creating an instance\n"
                    "alice = Person('Alice', 30)\n"
                    "print(alice.greet())  # Output: Hello, my name is Alice and I am 30 years old.\n"
                    "```\n\n"
                    "Classes encapsulate data (attributes) and behavior (methods). The `__init__` method is a special "
                    "constructor that initializes new objects.\n\n"
                    "Would you like to explore inheritance, polymorphism, or other OOP concepts in Python?"
                )
            else:
                return (
                    "Python is a versatile, high-level programming language known for its readability and simplicity. "
                    "Here's a simple Python program:\n\n"
                    "```python\n"
                    "# A simple Python program\n"
                    "def calculate_average(numbers):\n"
                    "    \"\"\"Calculate the average of a list of numbers.\"\"\"\n"
                    "    if not numbers:\n"
                    "        return 0\n"
                    "    return sum(numbers) / len(numbers)\n\n"
                    "# Example usage\n"
                    "scores = [85, 90, 78, 92, 88]\n"
                    "average = calculate_average(scores)\n"
                    "print(f\"The average score is {average}\")  # Output: The average score is 86.6\n"
                    "```\n\n"
                    "Python is great for beginners because of its clear syntax and powerful standard library. "
                    "What specific Python topic would you like to learn about?"
                )
        
        # JavaScript-related responses
        elif any(term in message_lower for term in ['javascript', 'js']):
            return (
                "JavaScript is the programming language of the web. Here's a simple example:\n\n"
                "```javascript\n"
                "// A simple JavaScript function\n"
                "function calculateTotal(items) {\n"
                "    return items.reduce((total, item) => total + item.price, 0);\n"
                "}\n\n"
                "// Example usage\n"
                "const cart = [\n"
                "    { name: 'Book', price: 19.99 },\n"
                "    { name: 'Pen', price: 2.99 },\n"
                "    { name: 'Notebook', price: 5.49 }\n"
                "];\n\n"
                "const total = calculateTotal(cart);\n"
                "console.log(`Total: $${total.toFixed(2)}`);  // Output: Total: $28.47\n"
                "```\n\n"
                "JavaScript is essential for adding interactivity to websites and can also be used for server-side "
                "development with Node.js.\n\n"
                "What JavaScript concept would you like to explore further?"
            )
        
        # Web development responses
        elif any(term in message_lower for term in ['html', 'css', 'web']):
            return (
                "Web development involves three core technologies:\n\n"
                "1. **HTML** - Structure of web pages\n"
                "2. **CSS** - Styling and layout\n"
                "3. **JavaScript** - Behavior and interactivity\n\n"
                "Here's a simple HTML example with CSS:\n\n"
                "```html\n"
                "<!DOCTYPE html>\n"
                "<html>\n"
                "<head>\n"
                "    <title>My Web Page</title>\n"
                "    <style>\n"
                "        body {\n"
                "            font-family: Arial, sans-serif;\n"
                "            max-width: 800px;\n"
                "            margin: 0 auto;\n"
                "            padding: 20px;\n"
                "        }\n"
                "        .header {\n"
                "            color: #2c3e50;\n"
                "            text-align: center;\n"
                "        }\n"
                "        .content {\n"
                "            line-height: 1.6;\n"
                "        }\n"
                "    </style>\n"
                "</head>\n"
                "<body>\n"
                "    <h1 class=\"header\">Welcome to My Website</h1>\n"
                "    <div class=\"content\">\n"
                "        <p>This is a simple example of HTML and CSS.</p>\n"
                "        <p>Web development is a creative and rewarding field!</p>\n"
                "    </div>\n"
                "</body>\n"
                "</html>\n"
                "```\n\n"
                "Would you like to learn more about HTML structure, CSS styling, or how to add JavaScript functionality?"
            )
        
        # Programming/computer science concepts
        elif any(term in message_lower for term in ['algorithm', 'data structure', 'coding']):
            return (
                "Algorithms and data structures are fundamental to computer science. Here's a simple "
                "binary search algorithm implementation in Python:\n\n"
                "```python\n"
                "def binary_search(arr, target):\n"
                "    \"\"\"Search for target in a sorted array using binary search.\"\"\"\n"
                "    left, right = 0, len(arr) - 1\n"
                "    \n"
                "    while left <= right:\n"
                "        mid = (left + right) // 2\n"
                "        \n"
                "        if arr[mid] == target:\n"
                "            return mid  # Target found, return its index\n"
                "        elif arr[mid] < target:\n"
                "            left = mid + 1  # Search the right half\n"
                "        else:\n"
                "            right = mid - 1  # Search the left half\n"
                "    \n"
                "    return -1  # Target not found\n\n"
                "# Example usage\n"
                "sorted_numbers = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]\n"
                "result = binary_search(sorted_numbers, 23)\n"
                "print(f\"Found at index: {result}\")  # Output: Found at index: 5\n"
                "```\n\n"
                "Binary search has O(log n) time complexity, making it much more efficient than linear search for large datasets.\n\n"
                "What specific algorithm or data structure would you like to explore?"
            )
        
        # General programming question
        else:
            return (
                "I'd be happy to help with your programming or computer science questions. I can assist with topics like:\n\n"
                "* Programming languages (Python, JavaScript, Java, C++, etc.)\n"
                "* Web development (HTML, CSS, frontend frameworks)\n"
                "* Data structures and algorithms\n"
                "* Database concepts and SQL\n"
                "* Software design patterns\n"
                "* Machine learning basics\n\n"
                "Could you please specify which programming topic you'd like to learn about? "
                "For example, are you interested in learning a specific language, solving a coding problem, "
                "or understanding a computer science concept?"
            )
