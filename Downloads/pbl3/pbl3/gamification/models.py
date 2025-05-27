from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum

class Badge(models.Model):
    """Digital badges for user accomplishments."""
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.ImageField(upload_to='badges/')
    
    # Badge categories
    CATEGORY_CHOICES = [
        ('completion', _('Course Completion')),
        ('skill', _('Skill Mastery')),
        ('engagement', _('Platform Engagement')),
        ('social', _('Social Contribution')),
        ('special', _('Special Achievement')),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Badge rarity/value
    RARITY_CHOICES = [
        ('common', _('Common')),
        ('uncommon', _('Uncommon')),
        ('rare', _('Rare')),
        ('epic', _('Epic')),
        ('legendary', _('Legendary')),
    ]
    rarity = models.CharField(max_length=10, choices=RARITY_CHOICES, default='common')
    
    # XP awarded for earning this badge
    experience_points = models.PositiveIntegerField(default=0)
    
    # Badge visibility
    is_hidden = models.BooleanField(default=False, help_text=_("Hidden badges are secret achievements"))
    
    # Creation metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'rarity']
    
    def __str__(self):
        return self.name


class Achievement(models.Model):
    """Achievements that users can earn on the platform."""
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Achievement requirements
    requirement_type = models.CharField(max_length=50, help_text=_("Type of action required"))
    requirement_value = models.PositiveIntegerField(help_text=_("Value to reach for the achievement"))
    
    # Associated badge
    badge = models.OneToOneField(Badge, on_delete=models.CASCADE, related_name='achievement')
    
    # Achievement series (for tiered achievements)
    series_name = models.CharField(max_length=100, blank=True)
    tier = models.PositiveSmallIntegerField(default=1)
    
    # Whether progress is tracked and shown to user
    show_progress = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['series_name', 'tier']
        unique_together = ['series_name', 'tier']
    
    def __str__(self):
        if self.series_name:
            return f"{self.series_name} - Tier {self.tier}: {self.name}"
        return self.name
    
    def check_user_progress(self, user):
        """Check a user's progress toward this achievement."""
        progress = UserAchievementProgress.objects.filter(
            user=user,
            achievement=self
        ).first()
        
        if not progress:
            # Create a new progress record
            progress = UserAchievementProgress.objects.create(
                user=user,
                achievement=self,
                current_value=0
            )
        
        return progress


class Leaderboard(models.Model):
    """Configurable leaderboards for different competitive aspects."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Leaderboard type
    TYPE_CHOICES = [
        ('xp', _('Experience Points')),
        ('course_completions', _('Course Completions')),
        ('streak', _('Daily Streak')),
        ('badges', _('Badges Earned')),
        ('quiz_scores', _('Quiz Scores')),
        ('custom', _('Custom Score')),
    ]
    leaderboard_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='xp')
    
    # For course-specific leaderboards
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Leaderboard timeframe
    TIMEFRAME_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('all_time', _('All Time')),
    ]
    timeframe = models.CharField(max_length=10, choices=TIMEFRAME_CHOICES, default='weekly')
    
    # Leaderboard scope
    is_global = models.BooleanField(default=True, help_text=_("If false, only for a specific course or group"))
    
    # Visibility and status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Reset information
    last_reset = models.DateTimeField(auto_now_add=True)
    next_reset = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-is_featured', 'name']
    
    def __str__(self):
        return self.name
    
    def get_leaders(self, limit=10):
        """Get the top users for this leaderboard."""
        if self.leaderboard_type == 'xp':
            # Order by XP
            from users.models import CustomUser
            return CustomUser.objects.order_by('-experience_points')[:limit]
        
        elif self.leaderboard_type == 'course_completions':
            # Order by course completions
            from django.db.models import Count
            from courses.models import Enrollment
            return settings.AUTH_USER_MODEL.objects.annotate(
                completions=Count('enrollments', filter=models.Q(enrollments__completed=True))
            ).order_by('-completions')[:limit]
        
        elif self.leaderboard_type == 'streak':
            # Order by streak
            return settings.AUTH_USER_MODEL.objects.order_by('-streak_days')[:limit]
        
        elif self.leaderboard_type == 'badges':
            # Order by badge count
            from django.db.models import Count
            return settings.AUTH_USER_MODEL.objects.annotate(
                badge_count=Count('badges')
            ).order_by('-badge_count')[:limit]
        
        elif self.leaderboard_type == 'quiz_scores':
            # Order by quiz scores if course specified
            if self.course:
                from django.db.models import Avg
                from quizzes.models import QuizAttempt
                return settings.AUTH_USER_MODEL.objects.annotate(
                    avg_score=Avg('quiz_attempts__score_percent', 
                              filter=models.Q(quiz_attempts__quiz__lesson__module__course=self.course))
                ).order_by('-avg_score')[:limit]
            
        # Default fallback
        return settings.AUTH_USER_MODEL.objects.none()
        
    def reset_if_needed(self):
        """Reset the leaderboard if the timeframe has elapsed."""
        if not self.next_reset or timezone.now() >= self.next_reset:
            self.reset_leaderboard()
    
    def reset_leaderboard(self):
        """Reset the leaderboard based on its timeframe."""
        now = timezone.now()
        self.last_reset = now
        
        # Set next reset time based on timeframe
        if self.timeframe == 'daily':
            self.next_reset = now + timezone.timedelta(days=1)
        elif self.timeframe == 'weekly':
            self.next_reset = now + timezone.timedelta(weeks=1)
        elif self.timeframe == 'monthly':
            # Approximate month as 30 days
            self.next_reset = now + timezone.timedelta(days=30)
        else:
            # All time leaderboards don't reset
            self.next_reset = None
            
        self.save(update_fields=['last_reset', 'next_reset'])
        
        # Clear the LeaderboardEntry records if needed
        if self.timeframe != 'all_time':
            LeaderboardEntry.objects.filter(leaderboard=self).delete()


class LeaderboardEntry(models.Model):
    """Individual entries on a leaderboard."""
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Score and rank
    score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    
    # Progress tracking
    previous_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    previous_rank = models.PositiveIntegerField(null=True, blank=True)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['leaderboard', 'user']
        ordering = ['-score']
    
    def __str__(self):
        return f"{self.user.username} - {self.leaderboard.name} - {self.score}"
    
    def save(self, *args, **kwargs):
        # Save previous state before updating
        if self.pk:
            old_entry = LeaderboardEntry.objects.get(pk=self.pk)
            self.previous_score = old_entry.score
            self.previous_rank = old_entry.rank
        
        super().save(*args, **kwargs)
        
        # Update ranks for all users in this leaderboard
        # This is not very efficient but works for small to medium platforms
        entries = LeaderboardEntry.objects.filter(leaderboard=self.leaderboard).order_by('-score')
        for i, entry in enumerate(entries, 1):
            if entry.rank != i:
                entry.rank = i
                entry.save(update_fields=['rank'])


class Streak(models.Model):
    """Daily login/engagement streak tracking."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='streak_record')
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(default=timezone.now)
    
    class Meta:
        verbose_name_plural = _('Streaks')
    
    def __str__(self):
        return f"{self.user.username} - {self.current_streak} days"
    
    def update_streak(self):
        """Update the user's streak based on their last activity."""
        today = timezone.now().date()
        yesterday = today - timezone.timedelta(days=1)
        
        if self.last_activity_date == yesterday:
            # User was active yesterday, extend streak
            self.current_streak += 1
        elif self.last_activity_date != today:
            # User wasn't active yesterday or today yet, reset streak
            self.current_streak = 1
        # else: User already active today, do nothing
        
        self.last_activity_date = today
        
        # Update longest streak if current streak is longer
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
            
        self.save()
        
        # Check for streak-based achievements
        self.check_streak_achievements()
        
        return self.current_streak
    
    def check_streak_achievements(self):
        """Check if user has earned any streak-based achievements."""
        from users.models import UserAchievement
        
        # Find all streak-related achievements
        streak_achievements = Achievement.objects.filter(
            requirement_type='streak_days'
        ).order_by('requirement_value')
        
        for achievement in streak_achievements:
            if self.current_streak >= achievement.requirement_value:
                # Check if the user already has this achievement
                if not UserAchievement.objects.filter(
                    user=self.user, 
                    achievement=achievement
                ).exists():
                    # Award the achievement
                    UserAchievement.objects.create(
                        user=self.user,
                        achievement=achievement,
                        date_earned=timezone.now()
                    )
                    
                    # Award XP
                    self.user.award_experience_points(achievement.badge.experience_points)


class UserAchievementProgress(models.Model):
    """Track a user's progress toward earning an achievement."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievement_progress')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    
    # Progress tracking
    current_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Status
    completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
    
    def __str__(self):
        percentage = self.get_percentage()
        return f"{self.user.username} - {self.achievement.name} - {percentage}%"
    
    def get_percentage(self):
        """Calculate percentage completion."""
        if self.achievement.requirement_value == 0:
            return 100 if self.completed else 0
            
        percentage = (self.current_value / self.achievement.requirement_value) * 100
        return min(100, round(percentage, 1))
    
    def update_progress(self, new_value):
        """Update progress and check for completion."""
        self.current_value = new_value
        
        # Check if achievement is completed
        if not self.completed and self.current_value >= self.achievement.requirement_value:
            self.completed = True
            self.completion_date = timezone.now()
            
            # Create UserAchievement record
            from users.models import UserAchievement
            UserAchievement.objects.create(
                user=self.user,
                achievement=self.achievement,
                date_earned=self.completion_date
            )
            
            # Award XP
            self.user.award_experience_points(self.achievement.badge.experience_points)
            
        self.save()
        return self.completed


class PointTransaction(models.Model):
    """Log of experience points earned/spent by users."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='point_transactions')
    
    # Points
    points = models.IntegerField(help_text=_("Positive for earned, negative for spent"))
    
    # Transaction metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=100, help_text=_("Where the points came from or went to"))
    
    # Linked objects
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Notes
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        action = "earned" if self.points > 0 else "spent"
        return f"{self.user.username} {action} {abs(self.points)} points from {self.source}"
    
    @classmethod
    def get_user_points_this_week(cls, user):
        """Get total points earned by user in the current week."""
        one_week_ago = timezone.now() - timezone.timedelta(days=7)
        return cls.objects.filter(
            user=user,
            timestamp__gte=one_week_ago,
            points__gt=0  # Only count earned points
        ).aggregate(total=Sum('points'))['total'] or 0
