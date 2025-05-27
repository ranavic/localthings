from django.urls import path
from . import views

app_name = 'ai_tutor'

urlpatterns = [
    # AI Tutor main views
    path('', views.AiTutorHomeView.as_view(), name='home'),
    path('chat/', views.AiTutorChatView.as_view(), name='chat'),
    path('chat/<int:session_id>/', views.AiTutorChatView.as_view(), name='chat_session'),
    
    # Explanations and concept clarification
    path('explain/', views.ExplainConceptView.as_view(), name='explain_concept'),
    
    # Problem solving and practice
    path('practice/', views.PracticeProblemsView.as_view(), name='practice_problems'),
    path('practice/submit/', views.SubmitSolutionView.as_view(), name='submit_solution'),
]
