from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import uuid
import random

class Quiz(models.Model):
    """Main quiz model for assessments."""
    
    DIFFICULTY_CHOICES = [
        ('beginner', _('Beginner')),
        ('intermediate', _('Intermediate')),
        ('advanced', _('Advanced')),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    
    # Quiz settings
    time_limit_minutes = models.PositiveSmallIntegerField(default=0, help_text=_("0 means no time limit"))
    passing_score = models.PositiveSmallIntegerField(default=70, help_text=_("Percentage required to pass"))
    max_attempts = models.PositiveSmallIntegerField(default=0, help_text=_("0 means unlimited attempts"))
    randomize_questions = models.BooleanField(default=True)
    show_correct_answers = models.BooleanField(default=False, help_text=_("Show correct answers after submission"))
    
    # Quiz metadata
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_quizzes')
    
    # Quiz categorization
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_CHOICES, default='intermediate')
    tags = models.ManyToManyField('courses.Tag', blank=True, related_name='quizzes')
    
    # Gamification
    experience_points = models.PositiveIntegerField(default=50, help_text=_("XP awarded for passing"))
    
    class Meta:
        verbose_name = _('Quiz')
        verbose_name_plural = _('Quizzes')
        ordering = ['-created']
    
    def __str__(self):
        return self.title
    
    @property
    def total_questions(self):
        """Get the total number of questions in this quiz."""
        return self.questions.count()
    
    @property
    def total_points(self):
        """Calculate the total points possible for this quiz."""
        return sum(question.points for question in self.questions.all())
    
    def get_questions(self):
        """Get questions, randomize if set."""
        questions = list(self.questions.all())
        if self.randomize_questions:
            random.shuffle(questions)
        return questions


class Question(models.Model):
    """Question model for quizzes."""
    
    TYPE_CHOICES = [
        ('multiple_choice', _('Multiple Choice')),
        ('true_false', _('True/False')),
        ('short_answer', _('Short Answer')),
        ('essay', _('Essay')),
        ('matching', _('Matching')),
        ('fill_blank', _('Fill in the Blank')),
        ('code', _('Code Question')),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    explanation = models.TextField(blank=True, help_text=_("Explanation shown after answering"))
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='multiple_choice')
    points = models.PositiveSmallIntegerField(default=10)
    order = models.PositiveIntegerField(default=0)
    
    # For code questions
    code_snippet = models.TextField(blank=True, help_text=_("Optional code snippet for this question"))
    code_language = models.CharField(max_length=50, blank=True, help_text=_("Programming language for the code"))
    
    # For matching questions
    matching_item_count = models.PositiveSmallIntegerField(default=0, help_text=_("Number of matching pairs"))
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - {self.text[:50]}"
    
    @property
    def has_correct_answer(self):
        """Check if this question type has a defined correct answer."""
        return self.question_type not in ['essay']
    
    @property
    def is_auto_gradable(self):
        """Check if this question can be automatically graded."""
        return self.question_type not in ['essay', 'short_answer']


class Answer(models.Model):
    """Answer model for quiz questions."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    explanation = models.TextField(blank=True)
    
    # For matching questions
    matching_pair_id = models.PositiveSmallIntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.question.text[:30]} - {self.text[:30]}"


class MatchingItem(models.Model):
    """Items for matching questions."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='matching_items')
    left_text = models.CharField(max_length=255)
    right_text = models.CharField(max_length=255)
    pair_id = models.PositiveSmallIntegerField()
    
    class Meta:
        unique_together = ['question', 'pair_id']
    
    def __str__(self):
        return f"{self.question.text[:30]} - Pair {self.pair_id}"


class QuizAttempt(models.Model):
    """Track student attempts at quizzes."""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    
    # Attempt metadata
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(null=True, blank=True)
    
    # Results
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    score_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    
    # Attempt status
    STATUS_CHOICES = [
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('timed_out', _('Timed Out')),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress')
    
    # Attempt identifier
    attempt_code = models.CharField(max_length=10, unique=True, editable=False)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} - {self.started_at}"
    
    def save(self, *args, **kwargs):
        # Generate unique attempt code if not present
        if not self.attempt_code:
            self.attempt_code = self.generate_attempt_code()
        super().save(*args, **kwargs)
    
    def generate_attempt_code(self):
        """Generate a unique attempt code."""
        return str(uuid.uuid4()).upper()[:8]
    
    def complete_attempt(self):
        """Mark the attempt as completed and calculate the score."""
        if self.status != 'completed':
            self.completed_at = timezone.now()
            self.time_taken_seconds = (self.completed_at - self.started_at).total_seconds()
            self.status = 'completed'
            
            # Calculate score
            answered_questions = self.answers.count()
            total_possible_points = sum(a.question.points for a in self.answers.all())
            
            if total_possible_points > 0:
                earned_points = sum(a.earned_points for a in self.answers.all())
                self.score = earned_points
                self.score_percent = (earned_points / total_possible_points) * 100
                self.passed = self.score_percent >= self.quiz.passing_score
            else:
                self.score = 0
                self.score_percent = 0
                self.passed = False
            
            self.save()
            
            # Award XP if passed
            if self.passed:
                self.student.award_experience_points(self.quiz.experience_points)
            
            return True
        return False


class QuestionResponse(models.Model):
    """Student's response to a question within a quiz attempt."""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    # For multiple choice, true/false
    selected_answers = models.ManyToManyField(Answer, blank=True, related_name='responses')
    
    # For text/essay answers
    text_response = models.TextField(blank=True)
    
    # For code questions
    code_response = models.TextField(blank=True)
    
    # For matching questions
    # Stored as JSON: [{"left_id": 1, "right_id": 3}, ...]
    matching_response = models.JSONField(default=dict, blank=True)
    
    # Grading
    is_correct = models.BooleanField(null=True, blank=True)
    earned_points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    feedback = models.TextField(blank=True)
    
    # Timestamps
    answered_at = models.DateTimeField(auto_now=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='graded_responses'
    )
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt.student.username} - {self.question.text[:30]}"
    
    def grade_response(self):
        """Auto-grade the response if possible."""
        if not self.question.is_auto_gradable:
            return False
            
        if self.question.question_type == 'multiple_choice':
            correct_answers = self.question.answers.filter(is_correct=True)
            selected_answers = self.selected_answers.all()
            
            # Check if selected answers match correct answers exactly
            if set(correct_answers) == set(selected_answers):
                self.is_correct = True
                self.earned_points = self.question.points
            else:
                self.is_correct = False
                self.earned_points = 0
                
        elif self.question.question_type == 'true_false':
            # For true/false, there should be one selected answer
            if self.selected_answers.filter(is_correct=True).exists():
                self.is_correct = True
                self.earned_points = self.question.points
            else:
                self.is_correct = False
                self.earned_points = 0
                
        elif self.question.question_type == 'matching':
            # Compare matching responses with correct pairs
            correct_matches = {item.pair_id: item for item in self.question.matching_items.all()}
            user_matches = self.matching_response.get('matches', [])
            
            correct_count = 0
            for match in user_matches:
                pair_id = match.get('pair_id')
                if pair_id in correct_matches:
                    correct_count += 1
            
            # Calculate partial credit
            if user_matches:
                self.is_correct = correct_count == len(correct_matches)
                self.earned_points = (correct_count / len(correct_matches)) * self.question.points
            else:
                self.is_correct = False
                self.earned_points = 0
        
        self.graded_at = timezone.now()
        self.save()
        return True
        
    def manual_grade(self, points, feedback, grader):
        """Manually grade a response (for essay/short answer)."""
        self.earned_points = min(points, self.question.points)  # Can't exceed max points
        self.feedback = feedback
        self.is_correct = self.earned_points == self.question.points
        self.graded_at = timezone.now()
        self.graded_by = grader
        self.save()
        return True
