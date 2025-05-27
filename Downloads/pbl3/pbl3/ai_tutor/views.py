from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging
import os
from datetime import datetime

# Import MongoDB models
from .mongo_models import AiTutorSession, LearningActivity, UserLearningPattern

# Import OpenAI service
from .openai_service import OpenAITutor

logger = logging.getLogger(__name__)

# Create your views here.

class AiTutorHomeView(TemplateView):
    template_name = 'ai_tutor/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Sample data for quick action cards
        context['quick_actions'] = [
            {
                'title': 'Continue Learning',
                'description': 'Continue where you left off in Python Intermediate',
                'icon': 'bi-play-circle',
                'link': '#',
                'color': 'primary'
            },
            {
                'title': 'Practice Problems',
                'description': 'Solve today\'s challenges to earn XP points',
                'icon': 'bi-code-slash',
                'link': '/ai_tutor/practice/',
                'color': 'success'
            },
            {
                'title': 'Explore Concepts',
                'description': 'Browse and learn new programming concepts',
                'icon': 'bi-book',
                'link': '/ai_tutor/explain/',
                'color': 'info'
            },
            {
                'title': 'New Chat',
                'description': 'Start a fresh chat with the AI Tutor',
                'icon': 'bi-chat-dots',
                'link': '/ai_tutor/chat/',
                'color': 'secondary'
            }
        ]
        
        # Sample recent sessions for sidebar
        context['recent_sessions'] = [
            {
                'id': 1,
                'title': 'Python Fundamentals',
                'last_message': 'How do I use list comprehensions?',
                'timestamp': '2 hours ago'
            },
            {
                'id': 2,
                'title': 'Web Development',
                'last_message': 'Explain how API endpoints work',
                'timestamp': 'Yesterday'
            },
            {
                'id': 3,
                'title': 'Data Structures',
                'last_message': 'What\'s the difference between stacks and queues?',
                'timestamp': '3 days ago'
            }
        ]
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class AiTutorChatView(LoginRequiredMixin, View):
    template_name = 'ai_tutor/chat.html'
    login_url = '/login/'
    
    def get(self, request, *args, **kwargs):
        # Set up the basic context for the view
        context = {
            'session_id': kwargs.get('session_id', 'new'),
        }
        
        # Get user's recent sessions from MongoDB
        if request.user.is_authenticated:
            # Get recent sessions from MongoDB
            user_sessions = AiTutorSession.get_user_sessions(request.user.id, limit=5)
            
            # Format sessions for the UI
            recent_sessions = []
            for session in user_sessions:
                # Get the last message if available
                last_message = ''
                if session.get('messages') and len(session['messages']) > 0:
                    last_message = session['messages'][-1]['content']
                    if len(last_message) > 50:
                        last_message = last_message[:50] + '...'
                
                # Format session data
                recent_sessions.append({
                    'id': str(session['_id']),
                    'title': session.get('title', 'Untitled Session'),
                    'last_message': last_message,
                    'timestamp': session.get('updated_at', datetime.now()).strftime('%Y-%m-%d %H:%M')
                })
            
            context['recent_sessions'] = recent_sessions
        else:
            # Provide empty list for non-authenticated users
            context['recent_sessions'] = []
        
        # If a specific session is requested, load its messages from MongoDB
        if kwargs.get('session_id') and kwargs.get('session_id') != 'new':
            session_id = kwargs.get('session_id')
            
            # Retrieve the session from MongoDB
            session = AiTutorSession.get_session(session_id)
            
            if session:
                # Format the messages for the UI
                messages = []
                for msg in session.get('messages', []):
                    messages.append({
                        'sender': msg.get('sender'),
                        'content': msg.get('content'),
                        'timestamp': msg.get('timestamp').strftime('%Y-%m-%dT%H:%M:%S')
                    })
                
                context['messages'] = messages
                context['session_title'] = session.get('title', 'Chat Session')
            else:
                # Session not found, create a new one
                context['messages'] = []
                context['session_title'] = 'New Session'
        else:
            # New session
            context['messages'] = []
            context['session_title'] = 'New Session'
        
        # Record the user's visit to the AI tutor in learning activity
        if request.user.is_authenticated:
            LearningActivity.log_activity(
                user_id=request.user.id,
                activity_type='tutor_access',
                content='Accessed AI Tutor',
                metadata={
                    'session_id': context['session_id'],
                    'path': request.path,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests to the chat view (user messages)"""
        try:
            # Parse the request body as JSON
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                # Handle malformed JSON
                logger.warning("Received malformed JSON in chat request")
                return JsonResponse({'response': "I'm sorry, there was an error processing your request. Please try again.", 
                                  'error': 'Invalid JSON'}, status=200)  # Return 200 to show a friendly message
                
            # Extract data with defaults
            user_message = data.get('message', '').strip()
            session_id = data.get('session_id', 'new')
            topic = data.get('topic', '')
            
            # Validate user message
            if not user_message:
                return JsonResponse({'response': "I didn't receive your message. Could you please try again?", 
                                  'session_id': session_id}, status=200)
            
            # Create new session if needed
            try:
                if session_id == 'new':
                    session_title = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    if topic:
                        session_title = f"{topic} - {session_title}"
                        
                    session_id = AiTutorSession.create_session(
                        user_id=request.user.id,
                        topic=topic,
                        title=session_title
                    )
            except Exception as e:
                logger.warning(f"Could not create session: {str(e)} - using temporary session")
                session_id = f"temp_{datetime.now().timestamp()}"
            
            # Try to add message to session - don't fail if this doesn't work
            try:
                AiTutorSession.add_message(
                    session_id=session_id,
                    content=user_message,
                    sender='user',
                    metadata={
                        'timestamp': datetime.now().isoformat(),
                        'user_id': request.user.id,
                        'topic': topic
                    }
                )
                
                # Try to log activity
                LearningActivity.log_activity(
                    user_id=request.user.id,
                    activity_type='ask_question',
                    content=user_message,
                    metadata={
                        'session_id': session_id,
                        'topic': topic
                    }
                )
            except Exception as e:
                logger.warning(f"Could not save message or log activity: {str(e)}")
            
            # Try to get conversation history, empty list as fallback
            conversation_history = []
            try:
                if session_id != 'new' and not session_id.startswith('temp_'):
                    messages = AiTutorSession.get_messages(session_id, limit=5)
                    for msg in messages:
                        role = "assistant" if msg.get('sender') == 'ai' else "user"
                        conversation_history.append({
                            "role": role,
                            "content": msg.get('content', '')
                        })
            except Exception as e:
                logger.warning(f"Could not get conversation history: {str(e)}")
            
            # Generate response using OpenAI - this should never fail with the new resilient implementation
            openai_tutor = OpenAITutor()
            logger.info(f"Processing request for user {request.user.id}, topic: {topic}")
            
            # Get the response - our implementation guarantees this won't throw exceptions
            response_content = openai_tutor.get_response(
                message=user_message,
                topic=topic,
                conversation_history=conversation_history
            )
            
            # Log the successful response
            logger.info(f"Generated response for user {request.user.id}, length: {len(response_content)}")
            timestamp = datetime.now()
            
            # Try to save the AI's response
            try:
                AiTutorSession.add_message(
                    session_id=session_id,
                    content=response_content,
                    sender='ai',
                    metadata={
                        'timestamp': timestamp.isoformat(),
                        'topic': topic
                    }
                )
                
                # Try to log learning patterns
                UserLearningPattern.log_pattern(
                    user_id=request.user.id,
                    pattern_type='question_topic',
                    content=topic or 'general',
                    metadata={
                        'question_length': len(user_message),
                        'timestamp': datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logger.warning(f"Could not save AI response or log pattern: {str(e)}")
            
            # Always return a 200 response with the AI's answer
            return JsonResponse({
                'response': response_content,
                'session_id': session_id,
                'timestamp': timestamp.isoformat()
            })
        except Exception as e:
            # Catch-all exception handler to ensure we never return a 500 error
            logger.error(f"Unexpected error in chat POST: {str(e)}")
            return JsonResponse({
                'response': "I apologize, but I'm having trouble processing your request right now. Please try again in a moment.",
                'session_id': 'error',
                'timestamp': datetime.now().isoformat()
            }, status=200)  # Return 200 instead of 500 to show a friendly message
            
    # This method is now replaced by the OpenAI integration
    # Keeping this as a fallback in case the OpenAI service fails
    def generate_educational_response_fallback(self, question, topic=None):
        """
        Generate a fallback AI tutor response when OpenAI is unavailable.
        
        Args:
            question: The question from the user
            topic: Optional topic for context
            
        Returns:
            str: Educational response with explanations and examples
        """
        # Topic-based responses with educational content for common programming topics
        programming_topics = {
            'python': {
                'basics': [
                    "Python is a high-level, interpreted programming language known for its readability and simplicity. Here's a basic example:\n```python\nprint('Hello, World!')\nfor i in range(5):\n    print(f'Count: {i}')\n```\n\nPython uses indentation to define code blocks, which makes the code clean and readable.",
                    "Python variables don't need explicit type declarations. For example:\n```python\nname = 'Alice'  # string\nage = 25       # integer\nheight = 5.7   # float\n```\n\nYou can check the type using the `type()` function."
                ],
                'functions': [
                    "In Python, functions are defined using the `def` keyword. Here's an example:\n```python\ndef greet(name):\n    return f'Hello, {name}!'\n\nresult = greet('World')\nprint(result)  # Output: Hello, World!\n```\n\nFunctions can have default parameters and return multiple values as tuples.",
                    "Python supports lambda functions for short, anonymous operations:\n```python\nsquare = lambda x: x**2\nprint(square(5))  # Output: 25\n\nnumbers = [1, 2, 3, 4, 5]\nsquared = list(map(lambda x: x**2, numbers))\nprint(squared)  # Output: [1, 4, 9, 16, 25]\n```"
                ],
                'data_structures': [
                    "Python has several built-in data structures. Lists are ordered, mutable collections:\n```python\nfruits = ['apple', 'banana', 'cherry']\nfruits.append('orange')\nprint(fruits[0])  # Output: apple\n```\n\nDictionaries store key-value pairs:\n```python\nperson = {'name': 'Alice', 'age': 25}\nprint(person['name'])  # Output: Alice\n```",
                    "Python sets are unordered collections of unique elements:\n```python\nunique_numbers = {1, 2, 3, 3, 4, 4, 5}\nprint(unique_numbers)  # Output: {1, 2, 3, 4, 5}\n\n# Set operations\nset1 = {1, 2, 3}\nset2 = {3, 4, 5}\nprint(set1.union(set2))        # {1, 2, 3, 4, 5}\nprint(set1.intersection(set2))  # {3}\n```"
                ]
            },
            'javascript': {
                'basics': [
                    "JavaScript is a versatile language primarily used for web development. Here's a basic example:\n```javascript\nconsole.log('Hello, World!');\n\nfor (let i = 0; i < 5; i++) {\n    console.log(`Count: ${i}`);\n}\n```\n\nJavaScript uses curly braces to define code blocks and semicolons to end statements.",
                    "JavaScript has several variable declaration keywords:\n```javascript\nlet name = 'Alice';   // Block-scoped variable\nconst age = 25;       // Block-scoped constant\nvar height = 5.7;     // Function-scoped variable\n```\n\nModern JavaScript prefers `let` and `const` over `var`."
                ],
                'functions': [
                    "JavaScript functions can be declared in several ways:\n```javascript\n// Function declaration\nfunction greet(name) {\n    return `Hello, ${name}!`;\n}\n\n// Function expression\nconst sayGoodbye = function(name) {\n    return `Goodbye, ${name}!`;\n};\n\n// Arrow function (ES6+)\nconst multiply = (a, b) => a * b;\n\nconsole.log(greet('World'));     // Output: Hello, World!\nconsole.log(multiply(5, 3));     // Output: 15\n```",
                    "JavaScript functions can be assigned to variables and passed as arguments to other functions:\n```javascript\nconst numbers = [1, 2, 3, 4, 5];\nconst squared = numbers.map(x => x * x);\nconsole.log(squared);  // Output: [1, 4, 9, 16, 25]\n\nconst sum = numbers.reduce((total, num) => total + num, 0);\nconsole.log(sum);      // Output: 15\n```"
                ],
                'dom': [
                    "The Document Object Model (DOM) allows JavaScript to interact with HTML:\n```javascript\n// Selecting elements\nconst heading = document.getElementById('main-heading');\nconst paragraphs = document.querySelectorAll('p');\n\n// Modifying content\nheading.textContent = 'New Heading';\nheading.style.color = 'blue';\n\n// Creating elements\nconst newButton = document.createElement('button');\nnewButton.textContent = 'Click Me';\ndocument.body.appendChild(newButton);\n```",
                    "JavaScript can handle DOM events to create interactive web pages:\n```javascript\nconst button = document.querySelector('button');\n\nbutton.addEventListener('click', function() {\n    alert('Button was clicked!');\n});\n\ndocument.addEventListener('DOMContentLoaded', function() {\n    console.log('The document has fully loaded');\n});\n```"
                ]
            },
            'web_development': {
                'html': [
                    "HTML (HyperText Markup Language) is the standard markup language for creating web pages:\n```html\n<!DOCTYPE html>\n<html>\n<head>\n    <title>My Web Page</title>\n</head>\n<body>\n    <h1>Welcome to My Website</h1>\n    <p>This is a paragraph of text.</p>\n    <ul>\n        <li>Item 1</li>\n        <li>Item 2</li>\n    </ul>\n</body>\n</html>\n```\n\nHTML uses tags to define elements on the page.",
                    "HTML5 introduced semantic elements that describe their meaning to browsers and developers:\n```html\n<header>\n    <nav>\n        <ul>\n            <li><a href="#">Home</a></li>\n            <li><a href="#">About</a></li>\n        </ul>\n    </nav>\n</header>\n<main>\n    <section>\n        <h2>Article Title</h2>\n        <article>Content goes here...</article>\n    </section>\n    <aside>Related information</aside>\n</main>\n<footer>Copyright 2025</footer>\n```"
                ],
                'css': [
                    "CSS (Cascading Style Sheets) is used for styling web pages:\n```css\n/* Selecting elements */\nbody {\n    font-family: Arial, sans-serif;\n    line-height: 1.6;\n    color: #333;\n}\n\nh1 {\n    color: #0066cc;\n    text-align: center;\n}\n\n/* Class selector */\n.container {\n    max-width: 1200px;\n    margin: 0 auto;\n    padding: 0 15px;\n}\n\n/* ID selector */\n#main-header {\n    background-color: #f4f4f4;\n    padding: 20px;\n}\n```",
                    "CSS Flexbox is a one-dimensional layout method for arranging items:\n```css\n.flex-container {\n    display: flex;\n    justify-content: space-between; /* Horizontal alignment */\n    align-items: center; /* Vertical alignment */\n    flex-wrap: wrap; /* Allow items to wrap */\n}\n\n.flex-item {\n    flex: 1; /* Grow and shrink equally */\n    margin: 10px;\n}\n```"
                ],
                'frameworks': [
                    "React is a popular JavaScript library for building user interfaces:\n```jsx\nimport React, { useState } from 'react';\n\nfunction Counter() {\n    const [count, setCount] = useState(0);\n    \n    return (\n        <div>\n            <p>You clicked {count} times</p>\n            <button onClick={() => setCount(count + 1)}>\n                Click me\n            </button>\n        </div>\n    );\n}\n\nexport default Counter;\n```",
                    "Django is a high-level Python web framework:\n```python\n# models.py\nfrom django.db import models\n\nclass Post(models.Model):\n    title = models.CharField(max_length=200)\n    content = models.TextField()\n    created_at = models.DateTimeField(auto_now_add=True)\n    \n    def __str__(self):\n        return self.title\n\n# views.py\nfrom django.shortcuts import render\nfrom .models import Post\n\ndef post_list(request):\n    posts = Post.objects.all().order_by('-created_at')\n    return render(request, 'blog/post_list.html', {'posts': posts})\n```"
                ]
            },
            'data_science': {
                'basics': [
                    "Data science combines domain expertise, programming, and math/statistics to extract knowledge from data.\n\nCommon Python libraries for data science include:\n- NumPy: For numerical computing\n- Pandas: For data manipulation and analysis\n- Matplotlib & Seaborn: For data visualization\n- Scikit-learn: For machine learning\n\nHere's a simple example using pandas:\n```python\nimport pandas as pd\n\n# Load data from CSV file\ndf = pd.read_csv('data.csv')\n\n# Display first 5 rows\nprint(df.head())\n\n# Basic statistics\nprint(df.describe())\n```",
                    "NumPy is fundamental for numerical computing in Python:\n```python\nimport numpy as np\n\n# Create an array\narr = np.array([1, 2, 3, 4, 5])\n\n# Basic operations\nprint(arr.mean())   # Output: 3.0\nprint(arr.std())    # Standard deviation\nprint(arr * 2)      # Element-wise multiplication: [2, 4, 6, 8, 10]\n\n# Creating a matrix\nmatrix = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])\nprint(matrix.shape)  # Output: (3, 3)\nprint(matrix.sum(axis=0))  # Sum of each column\n```"
                ],
                'machine_learning': [
                    "Machine learning allows computers to learn from data without being explicitly programmed.\n\nHere's a simple classification example using scikit-learn:\n```python\nfrom sklearn.datasets import load_iris\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.metrics import accuracy_score\n\n# Load data\niris = load_iris()\nX, y = iris.data, iris.target\n\n# Split data into training and testing sets\nX_train, X_test, y_train, y_test = train_test_split(\n    X, y, test_size=0.3, random_state=42)\n\n# Create and train the model\nmodel = RandomForestClassifier(n_estimators=100)\nmodel.fit(X_train, y_train)\n\n# Make predictions\npredictions = model.predict(X_test)\n\n# Evaluate the model\naccuracy = accuracy_score(y_test, predictions)\nprint(f'Accuracy: {accuracy:.2f}')\n```",
                    "Linear regression is a basic supervised learning algorithm for predicting a continuous value:\n```python\nimport numpy as np\nfrom sklearn.linear_model import LinearRegression\nimport matplotlib.pyplot as plt\n\n# Generate synthetic data\nX = np.array([[5], [15], [25], [35], [45], [55]])\ny = np.array([5, 20, 14, 32, 22, 38])\n\n# Create and train the model\nmodel = LinearRegression()\nmodel.fit(X, y)\n\n# Make predictions\nX_new = np.array([[5], [15], [25], [35], [45], [55]])\npredictions = model.predict(X_new)\n\n# Plot the results\nplt.scatter(X, y, color='blue', label='Actual data')\nplt.plot(X, predictions, color='red', label='Linear regression')\nplt.xlabel('X')\nplt.ylabel('y')\nplt.legend()\nplt.show()\n\nprint(f'Coefficient: {model.coef_[0]:.2f}')\nprint(f'Intercept: {model.intercept_:.2f}')\n```"
                ],
                'data_visualization': [
                    "Data visualization is crucial for understanding patterns and communicating insights.\n\nMatplotlib is a popular visualization library:\n```python\nimport matplotlib.pyplot as plt\nimport numpy as np\n\n# Generate data\nx = np.linspace(0, 10, 100)\ny1 = np.sin(x)\ny2 = np.cos(x)\n\n# Create plot\nplt.figure(figsize=(10, 6))\nplt.plot(x, y1, label='sin(x)', color='blue')\nplt.plot(x, y2, label='cos(x)', color='red', linestyle='--')\nplt.xlabel('x')\nplt.ylabel('y')\nplt.title('Sine and Cosine Functions')\nplt.legend()\nplt.grid(True)\nplt.show()\n```",
                    "Seaborn builds on matplotlib and provides a higher-level interface:\n```python\nimport seaborn as sns\nimport matplotlib.pyplot as plt\nimport pandas as pd\nimport numpy as np\n\n# Create a dataset\ndata = pd.DataFrame({\n    'x': np.random.normal(0, 1, 1000),\n    'y': np.random.normal(0, 1, 1000),\n    'category': np.random.choice(['A', 'B', 'C'], 1000)\n})\n\n# Create different visualizations\nplt.figure(figsize=(15, 10))\n\nplt.subplot(2, 2, 1)\nsns.histplot(data['x'], kde=True)\nplt.title('Histogram with KDE')\n\nplt.subplot(2, 2, 2)\nsns.scatterplot(data=data, x='x', y='y', hue='category')\nplt.title('Scatter Plot by Category')\n\nplt.subplot(2, 2, 3)\nsns.boxplot(data=data, x='category', y='x')\nplt.title('Box Plot by Category')\n\nplt.subplot(2, 2, 4)\nsns.heatmap(data.corr(), annot=True, cmap='coolwarm')\nplt.title('Correlation Heatmap')\n\nplt.tight_layout()\nplt.show()\n```"
                ]
            }
        }
        
        # General AI tutor responses for different types of questions
        general_responses = {
            'conceptual': [
                "Let me explain this concept in simple terms. {}",
                "The key idea behind {} is that it allows you to {}.",
                "Think of {} as {}. This analogy helps because {}."
            ],
            'procedural': [
                "Here's how to {}:\n\n1. First, {}\n2. Next, {}\n3. Finally, {}\n\nLet me know if you need clarification on any of these steps!",
                "To accomplish {}, follow these steps:\n\n1. {}\n2. {}\n3. {}\n\nThe most common mistake is {}, so be careful with that.",
                "When you want to {}, the process involves:\n\n1. {}\n2. {}\n3. {}\n\nAn important tip: {}"
            ],
            'comparison': [
                "Let's compare {} and {}:\n\n**{}**:\n- {}\n- {}\n- {}\n\n**{}**:\n- {}\n- {}\n- {}\n\nThe main difference is {}.",
                "When choosing between {} and {}, consider these factors:\n\n**{}** excels at {}, while **{}** is better for {}.\n\nIf you're working on {}, I'd recommend {} because {}."
            ],
            'error': [
                "This error typically occurs because {}. To fix it, try {}.",
                "I see what's happening. The issue is {}. You can resolve this by {}.",
                "This is a common error in {}. It happens when {}. The solution is to {}."
            ],
            'generic': [
                "That's an interesting question about {}. Let me elaborate on that topic...",
                "I'd be happy to help you understand {}. Here's what you need to know...",
                "Great question! When it comes to {}, there are several important points to consider..."
            ]
        }
        
        # Keywords to help determine the type of question
        question_indicators = {
            'conceptual': ['what is', 'what are', 'define', 'explain', 'concept', 'meaning', 'understand'],
            'procedural': ['how to', 'how do', 'steps', 'process', 'implement', 'create', 'make', 'build'],
            'comparison': ['difference', 'compare', 'versus', 'vs', 'better', 'advantage', 'disadvantage'],
            'error': ['error', 'bug', 'problem', 'issue', 'fix', 'solve', 'troubleshoot', 'doesn\'t work']
        }
        
        # Determine question type
        question_lower = question.lower()
        question_type = 'generic'
        for qtype, indicators in question_indicators.items():
            if any(indicator in question_lower for indicator in indicators):
                question_type = qtype
                break
        
        # First, try to match with a specific topic
        if topic:
            topic_lower = topic.lower()
            for main_topic, subtopics in programming_topics.items():
                if main_topic in topic_lower:
                    for subtopic, responses in subtopics.items():
                        if subtopic in topic_lower or any(kw in question_lower for kw in subtopic.split('_')):
                            return random.choice(responses)
                    
                    # If no subtopic match, just pick from the first subtopic
                    first_subtopic = list(subtopics.keys())[0]
                    return random.choice(subtopics[first_subtopic])
        
        # If no direct topic match, try keywords from the question
        for main_topic, subtopics in programming_topics.items():
            if main_topic in question_lower:
                for subtopic, responses in subtopics.items():
                    if subtopic in question_lower or any(kw in question_lower for kw in subtopic.split('_')):
                        return random.choice(responses)
        
        # If no specific content match, use general responses
        selected_response = random.choice(general_responses[question_type])
        
        # If it's a generic response, try to extract subject from the question
        if question_type == 'generic':
            subject = question.replace('?', '').replace('what is', '').replace('how to', '').strip()
            return selected_response.format(subject)
        
        # For other types, we need more context to fill in the template, so return a detailed generic answer
        return f"I'd be happy to help you with your question about {question}. Let's explore this topic.\n\nThis is an important concept in programming and computer science. To answer your question thoroughly, I'd typically connect to an AI model like GPT to generate a comprehensive response with code examples and explanations tailored to your specific question.\n\nIn your SkillForge account, premium users get unlimited AI tutor interactions with our advanced language models. Would you like to continue exploring this topic?"


class ExplainConceptView(TemplateView):
    template_name = 'ai_tutor/explain_concept.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Sample concepts for demonstration
        context['popular_concepts'] = [
            {'title': 'Object-Oriented Programming', 'category': 'Programming', 'searches': 1250},
            {'title': 'RESTful API Design', 'category': 'Web Development', 'searches': 987},
            {'title': 'Binary Search Trees', 'category': 'Data Structures', 'searches': 834},
            {'title': 'Regression Analysis', 'category': 'Machine Learning', 'searches': 760},
            {'title': 'SQL Joins', 'category': 'Databases', 'searches': 645},
        ]
        
        # Get concept from URL parameter or set a default
        concept = self.request.GET.get('concept', None)
        
        if concept:
            # In a real implementation, fetch the concept details from a database
            # For demo, we'll hard-code a sample concept
            context['concept'] = {
                'title': concept,
                'description': 'This is a detailed explanation of the concept...',
                'examples': [
                    {
                        'title': 'Basic Example',
                        'code': 'print("Hello, World!")'
                    },
                    {
                        'title': 'Advanced Example',
                        'code': 'def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b'
                    }
                ],
                'related_concepts': [
                    {'title': 'Variables', 'link': '?concept=Variables'},
                    {'title': 'Functions', 'link': '?concept=Functions'},
                    {'title': 'Loops', 'link': '?concept=Loops'}
                ]
            }
        
        return context


class PracticeProblemsView(TemplateView):
    template_name = 'ai_tutor/practice_problems.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # In a real implementation, fetch problems from a database with filtering
        # Sample data for demonstration
        topic_filter = self.request.GET.get('topic', None)
        difficulty = self.request.GET.get('difficulty', None)
        
        # For demo purposes, we'll ignore the filters and return all problems
        # In production, this would apply the filters to a database query
        
        return context


class SubmitSolutionView(View):
    """Handle solution submissions for practice problems"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            problem_id = data.get('problem_id')
            solution = data.get('solution')
            
            # In a real implementation, this would:
            # 1. Validate the solution (maybe run tests against it)
            # 2. Save the submission to a database
            # 3. Return feedback
            
            # Demo implementation with static response
            is_correct = bool(random.getrandbits(1))  # Random result for demo
            
            if is_correct:
                feedback = {
                    'status': 'correct',
                    'message': 'Great job! Your solution is correct.',
                    'details': {
                        'time_complexity': 'O(n)',
                        'space_complexity': 'O(n)',
                        'suggested_improvements': 'Consider using a more efficient algorithm for larger inputs.'
                    }
                }
            else:
                feedback = {
                    'status': 'incorrect',
                    'message': 'Your solution doesn\'t pass all test cases.',
                    'details': {
                        'test_cases': [
                            {'input': 'test input 1', 'expected': 'expected output 1', 'actual': 'your output 1', 'passed': True},
                            {'input': 'test input 2', 'expected': 'expected output 2', 'actual': 'your output 2', 'passed': False}
                        ],
                        'hint': 'Think about edge cases, such as empty inputs or special characters.'
                    }
                }
            
            return JsonResponse({
                'status': 'success',
                'feedback': feedback
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
