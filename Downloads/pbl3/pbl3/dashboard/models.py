from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import uuid


class UserDashboardPreference(models.Model):
    """User preferences for dashboard layout and widgets."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_preferences')
    
    # Layout preferences
    LAYOUT_CHOICES = [
        ('grid', _('Grid Layout')),
        ('masonry', _('Masonry Layout')),
        ('tabbed', _('Tabbed Layout')),
        ('sidebar', _('Sidebar Layout')),
    ]
    layout_type = models.CharField(max_length=10, choices=LAYOUT_CHOICES, default='grid')
    
    # Color theme
    THEME_CHOICES = [
        ('light', _('Light')),
        ('dark', _('Dark')),
        ('system', _('System Default')),
        ('custom', _('Custom')),
    ]
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='system')
    
    # Custom theme colors (if theme is 'custom')
    primary_color = models.CharField(max_length=7, default='#4A90E2')
    secondary_color = models.CharField(max_length=7, default='#F5A623')
    
    # Widget preferences
    enabled_widgets = models.JSONField(default=list)
    widget_layout = models.JSONField(default=dict)
    
    # Display preferences
    show_progress_percent = models.BooleanField(default=True)
    show_streaks = models.BooleanField(default=True)
    show_recommendations = models.BooleanField(default=True)
    show_leaderboards = models.BooleanField(default=True)
    show_statistics = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('Dashboard Preference')
        verbose_name_plural = _('Dashboard Preferences')
    
    def __str__(self):
        return f"Dashboard preferences for {self.user.username}"
    
    def get_default_widgets(self):
        """Get the default widgets for a new user."""
        return [
            'current_courses',
            'learning_progress',
            'upcoming_deadlines',
            'recommendations',
            'streaks',
            'achievements',
            'recent_activity',
        ]
    
    def save(self, *args, **kwargs):
        # Set default enabled widgets if empty
        if not self.enabled_widgets:
            self.enabled_widgets = self.get_default_widgets()
            
        # Set default widget layout if empty
        if not self.widget_layout:
            self.widget_layout = {
                'current_courses': {'row': 0, 'col': 0, 'width': 2, 'height': 2},
                'learning_progress': {'row': 0, 'col': 2, 'width': 1, 'height': 1},
                'upcoming_deadlines': {'row': 0, 'col': 3, 'width': 1, 'height': 1},
                'recommendations': {'row': 1, 'col': 2, 'width': 2, 'height': 1},
                'streaks': {'row': 1, 'col': 0, 'width': 1, 'height': 1},
                'achievements': {'row': 1, 'col': 1, 'width': 1, 'height': 1},
                'recent_activity': {'row': 2, 'col': 0, 'width': 4, 'height': 1},
            }
            
        super().save(*args, **kwargs)


class DashboardWidget(models.Model):
    """Available dashboard widgets."""
    # Widget identification
    widget_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Widget properties
    icon = models.CharField(max_length=50, blank=True, help_text=_("Font Awesome icon class"))
    template_name = models.CharField(max_length=100)
    js_module = models.CharField(max_length=100, blank=True)
    
    # Widget categorization
    CATEGORY_CHOICES = [
        ('progress', _('Learning Progress')),
        ('courses', _('Courses')),
        ('achievements', _('Achievements & Gamification')),
        ('social', _('Social & Community')),
        ('schedule', _('Schedule & Calendar')),
        ('analytics', _('Analytics & Reports')),
        ('recommendation', _('Recommendations')),
        ('other', _('Other')),
    ]
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='other')
    
    # Display properties
    min_width = models.PositiveSmallIntegerField(default=1)
    min_height = models.PositiveSmallIntegerField(default=1)
    default_width = models.PositiveSmallIntegerField(default=1)
    default_height = models.PositiveSmallIntegerField(default=1)
    
    # Widget status
    is_active = models.BooleanField(default=True)
    
    # Widget access control
    is_premium = models.BooleanField(default=False)
    required_role = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name


class LearningAnalytics(models.Model):
    """Analytics data for user learning patterns."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_analytics')
    
    # Tracking period
    date = models.DateField(default=timezone.now)
    
    # Time spent metrics
    total_study_time = models.PositiveIntegerField(default=0, help_text=_("Time spent in seconds"))
    time_by_course = models.JSONField(default=dict)
    
    # Activity metrics
    lessons_completed = models.PositiveSmallIntegerField(default=0)
    quizzes_completed = models.PositiveSmallIntegerField(default=0)
    assignments_completed = models.PositiveSmallIntegerField(default=0)
    
    # Performance metrics
    quiz_avg_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Engagement metrics
    messages_sent = models.PositiveSmallIntegerField(default=0)
    forum_posts = models.PositiveSmallIntegerField(default=0)
    mentor_sessions = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = 'Learning Analytics'
        unique_together = ['user', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics for {self.user.username} on {self.date}"


class UserRecommendation(models.Model):
    """Personalized course and content recommendations."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendations')
    
    # Recommendation types
    TYPE_CHOICES = [
        ('course', _('Course')),
        ('resource', _('Learning Resource')),
        ('mentor', _('Mentor')),
        ('peer', _('Peer Learner')),
        ('event', _('Learning Event')),
        ('content', _('Content')),
    ]
    recommendation_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # Recommendation details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    thumbnail = models.URLField(blank=True)
    
    # Reference to the recommended item
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Recommendation metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=3, help_text=_("1-5, where 1 is highest priority"))
    
    # Recommendation source
    SOURCE_CHOICES = [
        ('ai', _('AI Algorithm')),
        ('interest', _('Interest Based')),
        ('behavior', _('Behavior Based')),
        ('popular', _('Popularity Based')),
        ('manual', _('Manually Curated')),
    ]
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='ai')
    
    # User interaction
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    is_followed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.get_recommendation_type_display()} recommendation for {self.user.username}: {self.title}"
    
    def mark_read(self):
        """Mark this recommendation as read."""
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    def dismiss(self):
        """Dismiss this recommendation."""
        self.is_dismissed = True
        self.save(update_fields=['is_dismissed'])
    
    def follow(self):
        """Mark this recommendation as followed."""
        self.is_followed = True
        self.is_read = True
        self.save(update_fields=['is_followed', 'is_read'])


class UserGoal(models.Model):
    """Learning goals set by users."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_goals')
    
    # Goal details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Goal tracking
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    
    # Goal status
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('abandoned', _('Abandoned')),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Related courses/skills
    courses = models.ManyToManyField('courses.Course', blank=True, related_name='user_goals')
    skills = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['status', 'target_date', '-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s goal: {self.title}"
    
    def update_progress(self, percent):
        """Update the goal progress."""
        self.progress_percent = min(100, percent)
        
        if self.progress_percent == 100 and self.status == 'active':
            self.status = 'completed'
            self.completed_at = timezone.now()
            
        self.save(update_fields=['progress_percent', 'status', 'completed_at'])
        return self.status == 'completed'
    
    def mark_completed(self):
        """Mark this goal as completed."""
        self.status = 'completed'
        self.progress_percent = 100
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'progress_percent', 'completed_at'])
        return True


class LearningPath(models.Model):
    """Custom learning paths for users."""
    # Path identification
    path_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_paths')
    
    # Path details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    objective = models.TextField(blank=True, help_text=_("What you aim to achieve with this path"))
    
    # Path metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Path tracking
    is_active = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    
    # Path generation
    is_ai_generated = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-is_active', '-updated_at']
        
    def __str__(self):
        return f"{self.user.username}'s path: {self.title}"
    
    @property
    def total_steps(self):
        """Get the total number of steps in this learning path."""
        return self.steps.count()
    
    @property
    def completed_steps(self):
        """Get the number of completed steps in this learning path."""
        return self.steps.filter(is_completed=True).count()
    
    def update_progress(self):
        """Update the progress percentage based on completed steps."""
        if self.total_steps > 0:
            self.progress_percent = int((self.completed_steps / self.total_steps) * 100)
            if self.progress_percent == 100:
                self.completed = True
            self.save(update_fields=['progress_percent', 'completed'])
        return self.progress_percent


class LearningPathStep(models.Model):
    """Individual steps within a learning path."""
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='steps')
    
    # Step details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    
    # Step status
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Step type and content
    TYPE_CHOICES = [
        ('course', _('Course')),
        ('lesson', _('Lesson')),
        ('quiz', _('Quiz')),
        ('resource', _('External Resource')),
        ('task', _('Manual Task')),
    ]
    step_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # References to related objects
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True)
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.SET_NULL, null=True, blank=True)
    quiz = models.ForeignKey('quizzes.Quiz', on_delete=models.SET_NULL, null=True, blank=True)
    
    # For external resources
    resource_url = models.URLField(blank=True)
    resource_type = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.learning_path.title} - Step {self.order + 1}: {self.title}"
    
    def mark_completed(self):
        """Mark this step as completed."""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['is_completed', 'completed_at'])
        
        # Update the learning path progress
        self.learning_path.update_progress()
        return True


class NotificationPreference(models.Model):
    """User preferences for dashboard notifications."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # General settings
    receive_notifications = models.BooleanField(default=True)
    
    # Notification channels
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    in_app_notifications = models.BooleanField(default=True)
    
    # Notification types
    course_updates = models.BooleanField(default=True)
    assignment_reminders = models.BooleanField(default=True)
    mentor_messages = models.BooleanField(default=True)
    forum_replies = models.BooleanField(default=True)
    achievement_alerts = models.BooleanField(default=True)
    recommendations = models.BooleanField(default=True)
    platform_announcements = models.BooleanField(default=True)
    
    # Time preferences
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
        
    def __str__(self):
        return f"Notification preferences for {self.user.username}"


class DashboardNotification(models.Model):
    """Notifications displayed on user dashboard."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_notifications')
    
    # Notification content
    title = models.CharField(max_length=200)
    message = models.TextField()
    icon = models.CharField(max_length=50, blank=True)
    image_url = models.URLField(blank=True)
    
    # Notification metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Notification type
    TYPE_CHOICES = [
        ('info', _('Information')),
        ('success', _('Success')),
        ('warning', _('Warning')),
        ('error', _('Error')),
        ('achievement', _('Achievement')),
        ('reminder', _('Reminder')),
    ]
    notification_type = models.CharField(max_length=12, choices=TYPE_CHOICES, default='info')
    
    # Related content
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    
    # Notification status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Priority level
    PRIORITY_CHOICES = [
        (1, _('Low')),
        (2, _('Medium')),
        (3, _('High')),
        (4, _('Urgent')),
    ]
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES, default=2)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
    
    def mark_as_read(self):
        """Mark this notification as read."""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
        return True
