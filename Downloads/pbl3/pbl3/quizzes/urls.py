from django.urls import path
from . import views

app_name = 'quizzes'

urlpatterns = [
    # Quiz listing and detail views
    path('', views.QuizListView.as_view(), name='quiz_list'),
    path('<int:quiz_id>/', views.QuizDetailView.as_view(), name='quiz_detail'),
    path('course/<slug:course_slug>/', views.CourseQuizzesView.as_view(), name='course_quizzes'),
    path('module/<int:module_id>/', views.ModuleQuizzesView.as_view(), name='module_quizzes'),
    
    # Taking quizzes
    path('<int:quiz_id>/start/', views.StartQuizView.as_view(), name='start_quiz'),
    path('<int:quiz_id>/submit/', views.SubmitQuizView.as_view(), name='submit_quiz'),
    path('<int:quiz_id>/results/<int:attempt_id>/', views.QuizResultsView.as_view(), name='quiz_results'),
    
    # User quiz history
    path('my-quiz-history/', views.UserQuizHistoryView.as_view(), name='my_quiz_history'),
    path('my-quiz-stats/', views.UserQuizStatsView.as_view(), name='my_quiz_stats'),
    
    # Question feedback
    path('question/<int:question_id>/feedback/', views.QuestionFeedbackView.as_view(), name='question_feedback'),
    
    # Practice mode
    path('practice/<slug:topic_slug>/', views.PracticeQuizView.as_view(), name='practice_quiz'),
    path('practice/<slug:topic_slug>/results/', views.PracticeResultsView.as_view(), name='practice_results'),
]
