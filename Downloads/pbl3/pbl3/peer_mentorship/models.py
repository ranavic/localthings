from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class MentorProfile(models.Model):
    """Profile for users who are eligible to be mentors."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentor_profile')
    
    # Mentor status
    STATUS_CHOICES = [
        ('pending', _('Approval Pending')),
        ('approved', _('Approved')),
        ('suspended', _('Suspended')),
        ('inactive', _('Inactive')),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Mentor fields
    biography = models.TextField(help_text=_("Mentor's background and teaching philosophy"))
    expertise = models.ManyToManyField('MentorExpertise', blank=True, related_name='mentors')
    
    # Qualifications
    is_verified = models.BooleanField(default=False, help_text=_("Whether qualifications have been verified"))
    qualifications = models.TextField(blank=True, help_text=_("Academic qualifications or achievements"))
    
    # Mentoring metrics
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0, 
                                   help_text=_("Mentor's hourly rate in points (0 = free)"))
    max_mentees = models.PositiveSmallIntegerField(default=5, help_text=_("Maximum number of mentees"))
    
    # Platform metrics
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, 
                              validators=[MinValueValidator(0), MaxValueValidator(5)])
    total_sessions = models.PositiveIntegerField(default=0)
    total_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    
    # Account info
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 null=True, blank=True, related_name='approved_mentors')
    
    class Meta:
        ordering = ['-rating', '-total_sessions']
        
    def __str__(self):
        return f"Mentor: {self.user.username}"
    
    def approve(self, approver):
        """Approve this mentor profile."""
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = approver
        self.save(update_fields=['status', 'approved_at', 'approved_by'])
        return True
    
    def suspend(self, reason=''):
        """Suspend this mentor profile."""
        self.status = 'suspended'
        self.save(update_fields=['status'])
        
        # Log the suspension
        MentorStatusChange.objects.create(
            mentor=self,
            old_status='approved',
            new_status='suspended',
            reason=reason
        )
        return True
    
    @property
    def can_accept_mentees(self):
        """Check if mentor can accept more mentees."""
        return (self.status == 'approved' and 
                self.active_mentorships.count() < self.max_mentees)
    
    @property
    def active_mentorships(self):
        """Get active mentorship relationships."""
        return self.mentorships.filter(status='active')


class MentorExpertise(models.Model):
    """Areas of expertise for mentors."""
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True)
    
    # Associated courses/subjects
    courses = models.ManyToManyField('courses.Course', blank=True, related_name='mentor_expertise_areas')
    
    class Meta:
        ordering = ['category', 'name']
        
    def __str__(self):
        return self.name


class MentorAvailability(models.Model):
    """Represents a mentor's availability schedule."""
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='availability')
    
    # Schedule
    DAY_CHOICES = [
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday')),
    ]
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Repeat settings
    is_recurring = models.BooleanField(default=True)
    
    # Status
    is_available = models.BooleanField(default=True, help_text=_("Whether this time slot is currently available"))
    
    class Meta:
        verbose_name_plural = 'Mentor Availabilities'
        ordering = ['day_of_week', 'start_time']
        
    def __str__(self):
        day = self.get_day_of_week_display()
        return f"{self.mentor.user.username}: {day} {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"


class MentorStatusChange(models.Model):
    """Log of changes to a mentor's status."""
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='status_changes')
    
    # Status change details
    old_status = models.CharField(max_length=10)
    new_status = models.CharField(max_length=10)
    
    # Change metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='mentor_status_changes')
    reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.mentor.user.username}: {self.old_status} -> {self.new_status} ({self.timestamp.strftime('%Y-%m-%d')})"


class MentorshipRelationship(models.Model):
    """A mentorship relationship between a mentor and mentee."""
    # Relationship identification
    relationship_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Participants
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='mentorships')
    mentee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentee_relationships')
    
    # Relationship fields
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Mentorship details
    focus_areas = models.ManyToManyField(MentorExpertise, blank=True, related_name='mentorships')
    goals = models.TextField(blank=True, help_text=_("What the mentee hopes to achieve"))
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='mentorships')
    
    # Timeframe
    started_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.TextField(blank=True)
    
    # Metrics
    total_sessions = models.PositiveSmallIntegerField(default=0)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-started_at']
        unique_together = ['mentor', 'mentee', 'status']
        
    def __str__(self):
        return f"Mentorship: {self.mentor.user.username} -> {self.mentee.username}"
    
    def accept(self):
        """Accept a pending mentorship request."""
        if self.status == 'pending':
            self.status = 'active'
            self.accepted_at = timezone.now()
            self.save(update_fields=['status', 'accepted_at'])
            return True
        return False
    
    def complete(self, reason=''):
        """Complete a mentorship relationship."""
        if self.status == 'active':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.end_reason = reason
            self.save(update_fields=['status', 'completed_at', 'end_reason'])
            return True
        return False
    
    def cancel(self, reason=''):
        """Cancel a mentorship relationship."""
        if self.status in ['pending', 'active']:
            self.status = 'cancelled'
            self.completed_at = timezone.now()
            self.end_reason = reason
            self.save(update_fields=['status', 'completed_at', 'end_reason'])
            return True
        return False


class MentorshipSession(models.Model):
    """A session between mentor and mentee."""
    # Session identification
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    relationship = models.ForeignKey(MentorshipRelationship, on_delete=models.CASCADE, related_name='sessions')
    
    # Session details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Session scheduling
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    
    # Session status
    STATUS_CHOICES = [
        ('scheduled', _('Scheduled')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
        ('missed', _('Missed')),
    ]
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='scheduled')
    
    # Session tracking
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    
    # Attendance
    mentee_attended = models.BooleanField(null=True, blank=True)
    mentor_attended = models.BooleanField(null=True, blank=True)
    
    # Communication
    chat_room = models.ForeignKey('chat.ChatRoom', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Files/Resources
    session_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-scheduled_start']
        
    def __str__(self):
        return f"Session: {self.title} ({self.scheduled_start.strftime('%Y-%m-%d %H:%M')})"
    
    def start_session(self):
        """Mark the session as started."""
        if self.status == 'scheduled':
            self.status = 'in_progress'
            self.actual_start = timezone.now()
            self.save(update_fields=['status', 'actual_start'])
            return True
        return False
    
    def complete_session(self, mentor_attended=True, mentee_attended=True):
        """Mark the session as completed."""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.actual_end = timezone.now()
            
            # Calculate duration
            if self.actual_start:
                self.duration = self.actual_end - self.actual_start
                
            # Record attendance
            self.mentor_attended = mentor_attended
            self.mentee_attended = mentee_attended
            
            self.save(update_fields=['status', 'actual_end', 'duration', 'mentor_attended', 'mentee_attended'])
            
            # Update relationship stats
            relationship = self.relationship
            relationship.total_sessions += 1
            if self.duration:
                hours = self.duration.total_seconds() / 3600
                relationship.total_hours += hours
                
                # Also update mentor stats
                mentor = relationship.mentor
                mentor.total_sessions += 1
                mentor.total_hours += hours
                mentor.save(update_fields=['total_sessions', 'total_hours'])
                
            relationship.save(update_fields=['total_sessions', 'total_hours'])
            
            return True
        return False
    
    def cancel_session(self):
        """Cancel a scheduled session."""
        if self.status in ['scheduled', 'in_progress']:
            self.status = 'cancelled'
            self.save(update_fields=['status'])
            return True
        return False


class MentorshipFeedback(models.Model):
    """Feedback for a mentorship session."""
    session = models.ForeignKey(MentorshipSession, on_delete=models.CASCADE, related_name='feedback')
    
    # Who gave the feedback
    feedback_type = models.CharField(max_length=10, choices=[
        ('mentor', _('From Mentor')),
        ('mentee', _('From Mentee')),
    ])
    
    # Feedback details
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True)
    
    # Specific feedback areas
    knowledge_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], 
                                                     null=True, blank=True)
    communication_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], 
                                                         null=True, blank=True)
    helpfulness_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], 
                                                       null=True, blank=True)
    
    # Private feedback
    private_comments = models.TextField(blank=True, help_text=_("Comments only visible to administrators"))
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'feedback_type']
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_feedback_type_display()} for {self.session}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update mentor's rating if this is feedback from a mentee
        if is_new and self.feedback_type == 'mentee':
            mentor = self.session.relationship.mentor
            
            # Calculate new average rating
            feedback_count = MentorshipFeedback.objects.filter(
                session__relationship__mentor=mentor,
                feedback_type='mentee'
            ).count()
            
            if feedback_count > 0:
                avg_rating = MentorshipFeedback.objects.filter(
                    session__relationship__mentor=mentor,
                    feedback_type='mentee'
                ).aggregate(models.Avg('rating'))['rating__avg']
                
                mentor.rating = avg_rating
                mentor.save(update_fields=['rating'])


class MentorApplication(models.Model):
    """Application to become a mentor."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentor_applications')
    
    # Application details
    statement = models.TextField(help_text=_("Why you want to be a mentor"))
    expertise_areas = models.ManyToManyField(MentorExpertise, related_name='applications')
    qualifications = models.TextField()
    relevant_experience = models.TextField(blank=True)
    
    # Application status
    STATUS_CHOICES = [
        ('pending', _('Under Review')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('more_info', _('More Information Needed')),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='reviewed_applications')
    feedback = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Mentor Application: {self.user.username} ({self.get_status_display()})"
    
    def approve(self, reviewer, feedback=''):
        """Approve the mentor application."""
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.feedback = feedback
        self.save(update_fields=['status', 'reviewed_at', 'reviewed_by', 'feedback'])
        
        # Create or update mentor profile
        mentor_profile, created = MentorProfile.objects.get_or_create(
            user=self.user,
            defaults={
                'biography': self.statement,
                'qualifications': self.qualifications,
                'status': 'approved',
                'approved_at': timezone.now(),
                'approved_by': reviewer
            }
        )
        
        if not created:
            mentor_profile.status = 'approved'
            mentor_profile.approved_at = timezone.now()
            mentor_profile.approved_by = reviewer
            mentor_profile.save(update_fields=['status', 'approved_at', 'approved_by'])
            
        # Add expertise areas
        mentor_profile.expertise.set(self.expertise_areas.all())
        
        return mentor_profile
    
    def reject(self, reviewer, feedback):
        """Reject the mentor application."""
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.feedback = feedback
        self.save(update_fields=['status', 'reviewed_at', 'reviewed_by', 'feedback'])
        return True
