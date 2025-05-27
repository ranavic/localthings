from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile, UserPreference, LearningStyle

User = get_user_model()

class ProfileForm(forms.ModelForm):
    """Form for editing user profile information"""
    
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'bio', 'headline', 'website', 'location',
            'education', 'work_experience', 'skills', 'interests',
            'social_github', 'social_twitter', 'social_linkedin',
            'is_public'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'headline': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control-file'}),
            'skills': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
            'interests': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
            'social_github': forms.TextInput(attrs={'class': 'form-control'}),
            'social_twitter': forms.TextInput(attrs={'class': 'form-control'}),
            'social_linkedin': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserPreferenceForm(forms.ModelForm):
    """Form for editing user preferences"""
    
    class Meta:
        model = UserPreference
        fields = [
            'theme', 'dashboard_layout', 'language', 'timezone',
            'email_notifications', 'browser_notifications', 'sms_notifications',
            'course_update_notifications', 'achievement_notifications',
            'message_notifications', 'mentor_request_notifications'
        ]
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-control'}),
            'dashboard_layout': forms.Select(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
        }


class LearningStyleForm(forms.ModelForm):
    """Form for editing learning style preferences"""
    
    class Meta:
        model = LearningStyle
        fields = [
            'visual_learner', 'auditory_learner', 'reading_learner', 'kinesthetic_learner',
            'preferred_content_type', 'preferred_session_length', 'learning_pace',
            'preferred_difficulty'
        ]
        widgets = {
            'preferred_content_type': forms.Select(attrs={'class': 'form-control'}),
            'preferred_session_length': forms.Select(attrs={'class': 'form-control'}),
            'learning_pace': forms.Select(attrs={'class': 'form-control'}),
            'preferred_difficulty': forms.Select(attrs={'class': 'form-control'}),
        }
