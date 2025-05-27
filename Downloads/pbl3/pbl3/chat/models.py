from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import uuid


class ChatRoom(models.Model):
    """Represents a chat room or discussion group."""
    # Room identification
    room_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100)
    
    # Room types
    TYPE_CHOICES = [
        ('course', _('Course Discussion')),
        ('group', _('Study Group')),
        ('direct', _('Direct Message')),
        ('mentor', _('Mentor Session')),
        ('support', _('Support Chat')),
    ]
    room_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # Course reference (if relevant)
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_rooms')
    
    # Room details
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    icon = models.CharField(max_length=50, blank=True, help_text=_("Font Awesome icon class"))
    
    # Access control
    is_private = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    # For direct messaging
    is_direct_message = models.BooleanField(default=False)
    
    # Room participants
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ChatRoomMember', related_name='chat_rooms')
    
    # Last activity
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_message_at', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"
    
    @property
    def total_messages(self):
        """Get the total number of messages in this room."""
        return self.messages.count()
    
    @property
    def active_participants_count(self):
        """Get the number of active participants in this room."""
        return self.members.filter(is_active=True).count()
    
    def add_participant(self, user, role='member'):
        """Add a participant to this room."""
        member, created = ChatRoomMember.objects.get_or_create(
            room=self,
            user=user,
            defaults={'role': role, 'joined_at': timezone.now()}
        )
        return member
    
    def remove_participant(self, user):
        """Remove a participant from this room."""
        return ChatRoomMember.objects.filter(room=self, user=user).delete()
    
    def mark_as_read(self, user):
        """Mark this room as read for the given user."""
        member = ChatRoomMember.objects.filter(room=self, user=user).first()
        if member:
            last_message = self.messages.order_by('-timestamp').first()
            if last_message:
                member.last_read_at = last_message.timestamp
                member.unread_count = 0
                member.save(update_fields=['last_read_at', 'unread_count'])
                return True
        return False
    
    @classmethod
    def get_or_create_direct_message(cls, user1, user2):
        """Get or create a direct message room between two users."""
        # Check if DM already exists
        existing_rooms = ChatRoom.objects.filter(
            is_direct_message=True,
            members__user=user1
        ).filter(
            members__user=user2
        )
        
        if existing_rooms.exists():
            return existing_rooms.first()
            
        # Create new DM room
        room = ChatRoom.objects.create(
            name=f"DM: {user1.username} & {user2.username}",
            room_type='direct',
            is_direct_message=True,
            is_private=True
        )
        
        # Add participants
        room.add_participant(user1)
        room.add_participant(user2)
        
        return room


class ChatRoomMember(models.Model):
    """Represents a user's membership in a chat room."""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='room_memberships')
    
    # Membership details
    nickname = models.CharField(max_length=50, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_muted = models.BooleanField(default=False)
    
    # Unread messages tracking
    last_read_at = models.DateTimeField(null=True, blank=True)
    unread_count = models.PositiveIntegerField(default=0)
    
    # Role
    ROLE_CHOICES = [
        ('owner', _('Owner')),
        ('admin', _('Admin')),
        ('moderator', _('Moderator')),
        ('member', _('Member')),
        ('guest', _('Guest')),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    
    class Meta:
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f"{self.user.username} in {self.room.name}"
    
    def update_unread_count(self):
        """Update the unread message count."""
        if not self.last_read_at:
            self.unread_count = self.room.messages.count()
        else:
            self.unread_count = self.room.messages.filter(timestamp__gt=self.last_read_at).count()
        self.save(update_fields=['unread_count'])
        return self.unread_count


class ChatMessage(models.Model):
    """Represents a chat message within a room."""
    # Message identification
    message_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    
    # Message content
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Attachments
    has_attachment = models.BooleanField(default=False)
    
    # Status
    is_system_message = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # For threaded discussions
    parent_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    # For mentions
    mentioned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='message_mentions')
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update room's last message time
            self.room.last_message_at = self.timestamp
            self.room.save(update_fields=['last_message_at'])
            
            # Update unread counts for all members except sender
            for member in self.room.members.filter(is_active=True).exclude(user=self.sender):
                member.unread_count += 1
                member.save(update_fields=['unread_count'])
    
    def edit(self, new_content):
        """Edit the message content."""
        self.content = new_content
        self.edited_at = timezone.now()
        self.save(update_fields=['content', 'edited_at'])
        return True
    
    def soft_delete(self):
        """Soft delete the message."""
        self.is_deleted = True
        self.content = "<Message deleted>"
        self.save(update_fields=['is_deleted', 'content'])
        return True
    
    @property
    def is_edited(self):
        """Check if this message has been edited."""
        return self.edited_at is not None
    
    @property
    def reply_count(self):
        """Get the count of replies to this message."""
        return self.replies.count()


class ChatAttachment(models.Model):
    """Attachments for chat messages."""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    
    # Attachment info
    file = models.FileField(upload_to='chat_attachments/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text=_("Size in bytes"))
    
    # Media type
    MEDIA_TYPE_CHOICES = [
        ('image', _('Image')),
        ('document', _('Document')),
        ('audio', _('Audio')),
        ('video', _('Video')),
        ('other', _('Other')),
    ]
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='other')
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} ({self.get_media_type_display()})"
    
    def save(self, *args, **kwargs):
        # Set media type based on file extension
        if self.file_name:
            ext = self.file_name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                self.media_type = 'image'
            elif ext in ['doc', 'docx', 'pdf', 'txt', 'xls', 'xlsx', 'ppt', 'pptx']:
                self.media_type = 'document'
            elif ext in ['mp3', 'wav', 'ogg', 'flac']:
                self.media_type = 'audio'
            elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
                self.media_type = 'video'
                
        # Update has_attachment flag on message
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and not self.message.has_attachment:
            self.message.has_attachment = True
            self.message.save(update_fields=['has_attachment'])


class ChatReaction(models.Model):
    """Emoji reactions to chat messages."""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Reaction data
    emoji = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user', 'emoji']
    
    def __str__(self):
        return f"{self.user.username} reacted with {self.emoji}"


class OnlineStatus(models.Model):
    """Track users' online status for chat functionality."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='online_status')
    
    # Status
    STATUS_CHOICES = [
        ('online', _('Online')),
        ('away', _('Away')),
        ('busy', _('Busy')),
        ('offline', _('Offline')),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')
    
    # Timestamps
    last_activity = models.DateTimeField(auto_now=True)
    last_ping = models.DateTimeField(default=timezone.now)
    
    # Custom status message
    status_message = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name_plural = 'Online Statuses'
    
    def __str__(self):
        return f"{self.user.username} is {self.status}"
    
    def update_status(self, status, message=''):
        """Update user's online status."""
        self.status = status
        if message:
            self.status_message = message
        self.last_ping = timezone.now()
        self.save(update_fields=['status', 'status_message', 'last_ping'])
    
    @classmethod
    def get_active_users(cls):
        """Get currently active users."""
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
        return cls.objects.filter(last_ping__gte=five_minutes_ago, status__in=['online', 'away', 'busy'])
        
    @classmethod
    def get_user_status(cls, user):
        """Get a user's online status, creating it if it doesn't exist."""
        status, created = cls.objects.get_or_create(user=user)
        return status
