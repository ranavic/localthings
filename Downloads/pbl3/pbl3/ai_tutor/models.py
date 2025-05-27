from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import uuid

# For demo purposes, using a simplified model structure
# This avoids the need for complex migrations and database setup

# Note: For a full implementation, uncomment and properly configure these models


# Placeholder models for demonstration purposes only
# These models are not used in the actual views but ensure Django doesn't error
# when loading the app

class SimpleTutorSession(models.Model):
    """Simplified model for demo purposes."""
    session_id = models.CharField(max_length=36, unique=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Untitled Session")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Session {self.session_id[:8]} - {self.title}"


class SimpleMessage(models.Model):
    """Simplified message model for demo purposes."""
    session = models.ForeignKey(SimpleTutorSession, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_ai = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{'AI' if self.is_ai else 'User'} Message at {self.timestamp.strftime('%H:%M:%S')}"


class SimpleConcept(models.Model):
    """Simplified concept model for demo purposes."""
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
