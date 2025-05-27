"""
MongoDB utility for connecting and interacting with MongoDB databases.
This utility provides a direct connection to MongoDB using pymongo,
independent of Django's ORM system.

NOTE: This implementation gracefully handles cases where MongoDB is not available,
allowing the application to keep running with degraded functionality.
"""
import os
import logging
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB client with lazy initialization
_mongo_client = None
_mongo_available = False

def is_mongo_available():
    """
    Check if MongoDB is available
    
    Returns:
        bool: True if MongoDB is available, False otherwise
    """
    global _mongo_available
    return _mongo_available

# In-memory storage for fallback when MongoDB is unavailable
_memory_collections = {}

# Mock MongoDB Collection class for in-memory fallback
class MockCollection:
    def __init__(self, name):
        self.name = name
        if name not in _memory_collections:
            _memory_collections[name] = []
    
    def insert_one(self, document):
        if '_id' not in document:
            import uuid
            document['_id'] = str(uuid.uuid4())
        _memory_collections[self.name].append(document)
        return type('MockResult', (), {'inserted_id': document['_id']})
    
    def find(self, query=None):
        # Simple in-memory query implementation
        results = _memory_collections.get(self.name, [])
        if query:
            # Very basic filtering - real MongoDB queries can be complex
            filtered = []
            for doc in results:
                match = True
                for key, value in query.items():
                    if key not in doc or doc[key] != value:
                        match = False
                        break
                if match:
                    filtered.append(doc)
            return filtered
        return results
    
    def find_one(self, query=None):
        results = self.find(query)
        return results[0] if results else None


def get_mongo_client():
    """
    Get MongoDB client using connection string from environment variable
    or settings if available, otherwise use default localhost connection.
    
    Returns:
        MongoClient or None: MongoDB client if available, None otherwise
    """
    global _mongo_client, _mongo_available
    
    # Return existing client if we already have one
    if _mongo_client is not None:
        return _mongo_client
        
    try:
        # Try to import pymongo - if it's not available, we'll handle gracefully
        from pymongo import MongoClient
        
        # Try to get connection string from environment or settings
        connection_string = os.environ.get(
            'MONGODB_URI', 
            getattr(settings, 'MONGODB_URI', 'mongodb://localhost:27017')
        )
        
        # Attempt to connect with short timeout
        _mongo_client = MongoClient(connection_string, serverSelectionTimeoutMS=2000)
        
        # Validate connection
        _mongo_client.admin.command('ping')
        
        # If we got here, connection is successful
        _mongo_available = True
        logger.info("MongoDB connection established")
        return _mongo_client
    except ImportError:
        logger.warning("pymongo not installed. Using in-memory fallback.")
        _mongo_available = False
        return None
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB: {str(e)}. Using in-memory fallback.")
        _mongo_available = False
        return None

def get_database(db_name=None):
    """
    Get a specific MongoDB database.
    
    Args:
        db_name (str, optional): Name of the database to connect to.
            If not provided, uses the database name from settings or 'skillforge' as default.
            
    Returns:
        pymongo.database.Database or None: MongoDB database object if available, None otherwise
    """
    client = get_mongo_client()
    if client is None:
        return None
        
    db_name = db_name or getattr(settings, 'MONGODB_NAME', 'skillforge')
    return client[db_name]

def get_collection(collection_name, db_name=None):
    """
    Get a specific MongoDB collection.
    
    Args:
        collection_name (str): Name of the collection to get
        db_name (str, optional): Name of the database. If not provided, uses the default database.
        
    Returns:
        pymongo.collection.Collection or MockCollection: MongoDB collection if available, MockCollection otherwise
    """
    db = get_database(db_name)
    if db is None:
        # Return a mock collection when MongoDB is unavailable
        logger.debug(f"Using in-memory MockCollection for {collection_name}")
        return MockCollection(collection_name)
        
    return db[collection_name]
