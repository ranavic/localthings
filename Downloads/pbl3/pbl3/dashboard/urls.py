from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard views
    path('', views.DashboardHomeView.as_view(), name='home'),
    path('customize/', views.CustomizeDashboardView.as_view(), name='customize'),
    path('layout/<str:layout_type>/', views.ChangeDashboardLayoutView.as_view(), name='change_layout'),
    
    # Learning analytics
    path('analytics/', views.LearningAnalyticsView.as_view(), name='analytics'),
    path('analytics/progress/', views.LearningProgressView.as_view(), name='learning_progress'),
    path('analytics/activity/', views.ActivityAnalyticsView.as_view(), name='activity_analytics'),
    path('analytics/quiz-performance/', views.QuizPerformanceView.as_view(), name='quiz_performance'),
    
    # Recommendations
    path('recommendations/', views.RecommendationsView.as_view(), name='recommendations'),
    path('recommendations/courses/', views.CourseRecommendationsView.as_view(), name='course_recommendations'),
    path('recommendations/learning-paths/', views.LearningPathRecommendationsView.as_view(), name='learning_path_recommendations'),
    
    # Goals and tracking
    path('goals/', views.LearningGoalsView.as_view(), name='goals'),
    path('goals/create/', views.CreateLearningGoalView.as_view(), name='create_goal'),
    path('goals/<int:goal_id>/', views.LearningGoalDetailView.as_view(), name='goal_detail'),
    path('goals/<int:goal_id>/edit/', views.EditLearningGoalView.as_view(), name='edit_goal'),
    path('goals/<int:goal_id>/delete/', views.DeleteLearningGoalView.as_view(), name='delete_goal'),
    
    # Calendar and schedule
    path('calendar/', views.LearningCalendarView.as_view(), name='calendar'),
    path('schedule/', views.LearningScheduleView.as_view(), name='schedule'),
    path('schedule/create/', views.CreateScheduleEventView.as_view(), name='create_event'),
    path('schedule/<int:event_id>/', views.ScheduleEventDetailView.as_view(), name='event_detail'),
    
    # Notifications
    path('notifications/', views.DashboardNotificationsView.as_view(), name='notifications'),
    path('notifications/settings/', views.NotificationSettingsView.as_view(), name='notification_settings'),
    
    # Widgets management
    path('widgets/', views.WidgetListView.as_view(), name='widget_list'),
    path('widgets/add/<str:widget_type>/', views.AddWidgetView.as_view(), name='add_widget'),
    path('widgets/<int:widget_id>/remove/', views.RemoveWidgetView.as_view(), name='remove_widget'),
    path('widgets/<int:widget_id>/configure/', views.ConfigureWidgetView.as_view(), name='configure_widget'),
    
    # Reports
    path('reports/', views.UserReportsView.as_view(), name='reports'),
    path('reports/generate/', views.GenerateReportView.as_view(), name='generate_report'),
    path('reports/<int:report_id>/', views.ReportDetailView.as_view(), name='report_detail'),
]
