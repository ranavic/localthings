"""
MongoDB models for AI Tutor.
These are not Django ORM models, but classes that facilitate working with MongoDB collections.
"""
from datetime import datetime
from utils.mongodb import get_collection, is_mongo_available
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

class AiTutorSession:
    """
    Represents an AI Tutor session with a user, storing the conversation history
    and learning context in MongoDB.
    
    Note: All methods gracefully handle the case where MongoDB is not available by 
    returning appropriate default values.
    """
    
    @staticmethod
    def get_collection():
        """Get the MongoDB collection for AI tutor sessions"""
        return get_collection('ai_tutor_sessions')
    
    @classmethod
    def create_session(cls, user_id, topic=None, title=None, metadata=None):
        """
        Create a new AI Tutor session.
        
        Args:
            user_id: ID of the user who owns this session
            topic: Optional topic for this session
            title: Optional title for this session
            metadata: Optional additional metadata
            
        Returns:
            str: ID of the newly created session or 'temp_session' if MongoDB is unavailable
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - using temporary session ID")
            return f"temp_session_{datetime.now().timestamp()}"
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - using temporary session ID")
            return f"temp_session_{datetime.now().timestamp()}"
        
        try:
            session = {
                'user_id': user_id,
                'topic': topic,
                'title': title or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'metadata': metadata or {},
                'messages': [],
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'is_active': True
            }
            
            result = collection.insert_one(session)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating MongoDB session: {str(e)}")
            return f"temp_session_{datetime.now().timestamp()}"
    
    @classmethod
    def add_message(cls, session_id, content, sender, metadata=None):
        """
        Add a message to an existing session.
        
        Args:
            session_id: ID of the session to add the message to
            content: Content of the message
            sender: Who sent the message ('user' or 'ai')
            metadata: Optional additional metadata
            
        Returns:
            bool: True if the message was added successfully or if in fallback mode
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - message not saved")
            return True  # Return success in fallback mode
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - message not saved")
            return True  # Return success in fallback mode
        
        try:
            message = {
                'content': content,
                'sender': sender,
                'timestamp': datetime.now(),
                'metadata': metadata or {}
            }
            
            result = collection.update_one(
                {'_id': session_id},
                {
                    '$push': {'messages': message},
                    '$set': {'updated_at': datetime.now()}
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding message to MongoDB: {str(e)}")
            return True  # Return success in fallback mode
    
    @classmethod
    def get_session(cls, session_id):
        """
        Get a session by its ID.
        
        Args:
            session_id: ID of the session to retrieve
            
        Returns:
            dict: The session document or None if not found or if MongoDB is unavailable
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - returning None for session")
            return None
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - returning None for session")
            return None
            
        try:
            return collection.find_one({'_id': session_id})
        except Exception as e:
            logger.error(f"Error retrieving MongoDB session: {str(e)}")
            return None
    
    @classmethod
    def get_messages(cls, session_id, limit=5):
        """Get messages from a session, ordered by timestamp.
        
        Args:
            session_id: The session ID
            limit: Maximum number of messages to return (default: 5)
            
        Returns:
            list: The messages in the session, or an empty list if not found
        """
        try:
            session = cls.get_session(session_id)
            if not session:
                return []
                
            messages = session.get('messages', [])
            
            # Sort by timestamp if available
            messages.sort(key=lambda x: x.get('metadata', {}).get('timestamp', ''), reverse=True)
            
            # Return the most recent messages up to the limit
            return messages[:limit][::-1]  # Reverse to get chronological order
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {str(e)}")
            return []
    
    @classmethod
    def get_user_sessions(cls, user_id, limit=10, skip=0):
        """
        Get sessions for a specific user.
        
        Args:
            user_id: ID of the user whose sessions to retrieve
            limit: Maximum number of sessions to retrieve
            skip: Number of sessions to skip (for pagination)
            
        Returns:
            list: List of session documents or empty list if MongoDB is unavailable
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - returning empty session list")
            return []
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - returning empty session list")
            return []
            
        try:
            return list(collection.find(
                {'user_id': user_id},
                sort=[('updated_at', -1)],
                limit=limit,
                skip=skip
            ))
        except Exception as e:
            logger.error(f"Error retrieving user sessions from MongoDB: {str(e)}")
            return []
    
    @classmethod
    def delete_session(cls, session_id):
        """
        Delete a session.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            bool: True if the session was deleted successfully or if in fallback mode
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - session deletion skipped")
            return True  # Return success in fallback mode
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - session deletion skipped")
            return True  # Return success in fallback mode
            
        try:
            result = collection.delete_one({'_id': session_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting MongoDB session: {str(e)}")
            return True  # Return success in fallback mode


class LearningActivity:
    """
    Represents a user's learning activity and progress tracked in MongoDB.
    
    Note: All methods gracefully handle the case where MongoDB is not available by 
    returning appropriate default values.
    """
    
    @staticmethod
    def get_collection():
        """Get the MongoDB collection for learning activity"""
        return get_collection('learning_activity')
    
    @classmethod
    def log_activity(cls, user_id, activity_type, content, metadata=None):
        """
        Log a learning activity for a user.
        
        Args:
            user_id: ID of the user performing the activity
            activity_type: Type of activity (e.g., 'question', 'practice', 'concept_explanation')
            content: Content of the activity
            metadata: Optional additional metadata
            
        Returns:
            str: ID of the newly created activity record or 'temp_id' if MongoDB is unavailable
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - activity not logged")
            return f"temp_id_{datetime.now().timestamp()}"
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - activity not logged")
            return f"temp_id_{datetime.now().timestamp()}"
            
        try:
            activity = {
                'user_id': user_id,
                'activity_type': activity_type,
                'content': content,
                'metadata': metadata or {},
                'timestamp': datetime.now()
            }
            
            result = collection.insert_one(activity)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error logging activity to MongoDB: {str(e)}")
            return f"temp_id_{datetime.now().timestamp()}"
    
    @classmethod
    def get_user_activities(cls, user_id, activity_type=None, limit=50, skip=0):
        """
        Get learning activities for a specific user.
        
        Args:
            user_id: ID of the user whose activities to retrieve
            activity_type: Optional type of activities to filter by
            limit: Maximum number of activities to retrieve
            skip: Number of activities to skip (for pagination)
            
        Returns:
            list: List of activity documents or empty list if MongoDB is unavailable
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - returning empty activities list")
            return []
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - returning empty activities list")
            return []
            
        try:
            query = {'user_id': user_id}
            if activity_type:
                query['activity_type'] = activity_type
                
            return list(collection.find(
                query,
                sort=[('timestamp', -1)],
                limit=limit,
                skip=skip
            ))
        except Exception as e:
            logger.error(f"Error retrieving user activities from MongoDB: {str(e)}")
            return []


class UserLearningPattern:
    """
    Stores and analyzes user learning patterns for AI personalization.
    
    Note: All methods gracefully handle the case where MongoDB is not available by 
    returning appropriate default values.
    """
    
    @staticmethod
    def get_collection():
        """Get the MongoDB collection for user learning patterns"""
        return get_collection('user_learning_patterns')
    
    @classmethod
    def update_learning_pattern(cls, user_id, topic, learning_style=None, difficulty_level=None, 
                               comprehension_score=None, engagement_metrics=None, metadata=None):
        """
        Update a user's learning pattern for a specific topic.
        
        Args:
            user_id: ID of the user
            topic: The subject/topic being learned
            learning_style: Optional recorded learning style preference
            difficulty_level: Optional difficulty level the user is comfortable with
            comprehension_score: Optional score indicating comprehension level
            engagement_metrics: Optional metrics on user engagement
            metadata: Optional additional metadata
            
        Returns:
            bool: True if the pattern was updated successfully or if in fallback mode
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - learning pattern update skipped")
            return True  # Return success in fallback mode
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - learning pattern update skipped")
            return True  # Return success in fallback mode
            
        try:
            update_data = {'updated_at': datetime.now()}
            
            if learning_style is not None:
                update_data['learning_style'] = learning_style
                
            if difficulty_level is not None:
                update_data['difficulty_level'] = difficulty_level
                
            if comprehension_score is not None:
                update_data['comprehension_score'] = comprehension_score
                
            if engagement_metrics is not None:
                update_data['engagement_metrics'] = engagement_metrics
                
            if metadata is not None:
                update_data['metadata'] = metadata
            
            result = collection.update_one(
                {'user_id': user_id, 'topic': topic},
                {
                    '$set': update_data,
                    '$setOnInsert': {
                        'user_id': user_id,
                        'topic': topic,
                        'created_at': datetime.now()
                    }
                },
                upsert=True
            )
            
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error updating learning pattern in MongoDB: {str(e)}")
            return True  # Return success in fallback mode
    
    @classmethod
    def get_user_learning_patterns(cls, user_id):
        """
        Get all learning patterns for a specific user.
        
        Args:
            user_id: ID of the user whose patterns to retrieve
            
        Returns:
            list: List of learning pattern documents or empty list if MongoDB is unavailable
        """
        if not is_mongo_available():
            logger.warning("MongoDB unavailable - returning empty learning patterns list")
            return []
            
        collection = cls.get_collection()
        if collection is None:
            logger.warning("MongoDB collection unavailable - returning empty learning patterns list")
            return []
            
        try:
            return list(collection.find({'user_id': user_id}))
        except Exception as e:
            logger.error(f"Error retrieving learning patterns from MongoDB: {str(e)}")
            return []
