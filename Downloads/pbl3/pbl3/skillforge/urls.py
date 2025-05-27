"""
skillforge URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from users import views as user_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Direct template rendering for simplified demo
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard/dashboard.html'), name='dashboard'),
    path('courses/', TemplateView.as_view(template_name='courses/courses.html'), name='courses'),
    
    # User management (using class-based view)
    path('users/', user_views.ProfileView.as_view(), name='users_profile'),
    
    # Authentication URLs using Django's built-in views with names matching what templates expect
    path('accounts/login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='account_login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='account_logout'),
    path('accounts/signup/', user_views.signup_view, name='account_signup'),
    path('accounts/profile/', RedirectView.as_view(url='/users/', permanent=False), name='account_profile'),
    
    # AI Tutor app URLs
    path('ai-tutor/', include('ai_tutor.urls')),  # Note: URL uses hyphen but app name uses underscore
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
