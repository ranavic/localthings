from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
import uuid

class Category(models.Model):
    """Category model for organizing courses by subject."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('courses:category_detail', args=[self.slug])


class Difficulty(models.Model):
    """Difficulty level model for courses."""
    name = models.CharField(max_length=20)
    level = models.PositiveSmallIntegerField(unique=True)
    
    class Meta:
        verbose_name = _('Difficulty')
        verbose_name_plural = _('Difficulties')
        ordering = ['level']
    
    def __str__(self):
        return self.name


class Course(models.Model):
    """Main course model for the platform."""
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('published', _('Published')),
        ('archived', _('Archived')),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    overview = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    
    # Course details
    description = models.TextField()
    learning_outcomes = models.TextField(help_text=_("What students will learn from this course"))
    prerequisites = models.TextField(blank=True, help_text=_("Required skills or courses"))
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True)
    featured_video = models.URLField(blank=True, help_text=_("YouTube or Vimeo URL for course intro"))
    duration_hours = models.PositiveSmallIntegerField(default=0, help_text=_("Estimated hours to complete"))
    
    # Categorization
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    difficulty = models.ForeignKey(Difficulty, on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField('Tag', blank=True, related_name='courses')
    
    # Instructor
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_created')
    
    # Course pricing and enrollment
    is_free = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    discount_price = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    enrollment_limit = models.PositiveIntegerField(null=True, blank=True)
    
    # Gamification
    experience_points = models.PositiveIntegerField(default=100)
    
    # Multi-language support
    LANGUAGE_CHOICES = [
        ('en', _('English')),
        ('hi', _('Hindi')),
        ('kn', _('Kannada')),
    ]
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    
    # Certificate
    certificate_available = models.BooleanField(default=True)
    
    # Course code for enrollment
    course_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    
    class Meta:
        ordering = ['-created']
        
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('courses:course_detail', args=[self.slug])
    
    def save(self, *args, **kwargs):
        if not self.course_code:
            self.course_code = self.generate_course_code()
        super().save(*args, **kwargs)
    
    def generate_course_code(self):
        """Generate a unique course code."""
        return str(uuid.uuid4()).upper()[:8]
    
    @property
    def rating(self):
        """Calculate the average rating for this course."""
        reviews = self.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0
    
    @property
    def total_students(self):
        """Get the total number of enrolled students."""
        return self.enrollments.count()
    
    @property
    def completion_rate(self):
        """Calculate the percentage of students who completed the course."""
        total = self.enrollments.count()
        if total:
            completed = self.enrollments.filter(completed=True).count()
            return (completed / total) * 100
        return 0


class Module(models.Model):
    """Module within a course."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    """Lesson within a module."""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    
    # Lesson types
    TYPE_CHOICES = [
        ('video', _('Video')),
        ('text', _('Text')),
        ('quiz', _('Quiz')),
        ('assignment', _('Assignment')),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text')
    
    # Video lesson specifics
    video_url = models.URLField(blank=True, null=True)
    video_duration = models.PositiveIntegerField(blank=True, null=True, help_text=_("Duration in seconds"))
    
    # Assignment specifics
    assignment_due_date = models.DateTimeField(blank=True, null=True)
    assignment_points = models.PositiveIntegerField(default=0)
    
    # Quiz connection
    quiz = models.ForeignKey('quizzes.Quiz', on_delete=models.SET_NULL, blank=True, null=True)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.module.course.title} - {self.module.title} - {self.title}"


class Tag(models.Model):
    """Tags for courses."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name


class CourseReview(models.Model):
    """Course reviews and ratings."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['course', 'user']
        ordering = ['-created']
        
    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.rating}"


class Enrollment(models.Model):
    """Track student enrollments in courses."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    
    # Enrollment status
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('dropped', _('Dropped')),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    # Course progress
    completed = models.BooleanField(default=False)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    
    # Certificate related
    certificate_issued = models.BooleanField(default=False)
    certificate_issued_date = models.DateTimeField(null=True, blank=True)
    certificate_blockchain_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        unique_together = ['course', 'student']
        
    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"
    
    def issue_certificate(self):
        """Issue a certificate after course completion."""
        if self.completed and not self.certificate_issued:
            self.certificate_issued = True
            self.certificate_issued_date = timezone.now()
            self.save(update_fields=['certificate_issued', 'certificate_issued_date'])
            
            # Here we would generate the blockchain certificate in a real implementation
            # self.certificate_blockchain_id = blockchain_service.generate_certificate(self)
            
            return True
        return False


class LessonProgress(models.Model):
    """Track student progress on individual lessons."""
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(auto_now=True)
    time_spent = models.PositiveIntegerField(default=0, help_text=_("Time spent in seconds"))
    
    class Meta:
        unique_together = ['enrollment', 'lesson']
        
    def __str__(self):
        return f"{self.enrollment.student.username} progress on {self.lesson.title}"


class CourseResource(models.Model):
    """Additional resources for courses."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='course_resources/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    @property
    def is_external(self):
        """Check if this is an external resource."""
        return bool(self.url) and not bool(self.file)
