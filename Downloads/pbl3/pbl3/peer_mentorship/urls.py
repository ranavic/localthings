from django.urls import path
from . import views

app_name = 'peer_mentorship'

urlpatterns = [
    # Main mentorship views
    path('', views.MentorshipHomeView.as_view(), name='home'),
    path('browse-mentors/', views.BrowseMentorsView.as_view(), name='browse_mentors'),
    path('become-mentor/', views.BecomeMentorView.as_view(), name='become_mentor'),
    
    # Mentor profiles
    path('mentors/<str:username>/', views.MentorProfileView.as_view(), name='mentor_profile'),
    path('my-mentor-profile/', views.MyMentorProfileView.as_view(), name='my_mentor_profile'),
    path('my-mentor-profile/edit/', views.EditMentorProfileView.as_view(), name='edit_mentor_profile'),
    
    # Mentorship relationships
    path('my-mentees/', views.MyMenteesView.as_view(), name='my_mentees'),
    path('my-mentors/', views.MyMentorsView.as_view(), name='my_mentors'),
    path('request-mentorship/<str:username>/', views.RequestMentorshipView.as_view(), name='request_mentorship'),
    path('mentorship-requests/', views.MentorshipRequestsView.as_view(), name='mentorship_requests'),
    path('mentorship-requests/<int:request_id>/accept/', views.AcceptMentorshipRequestView.as_view(), name='accept_request'),
    path('mentorship-requests/<int:request_id>/decline/', views.DeclineMentorshipRequestView.as_view(), name='decline_request'),
    path('end-mentorship/<int:relationship_id>/', views.EndMentorshipView.as_view(), name='end_mentorship'),
    
    # Sessions
    path('sessions/', views.MentorshipSessionListView.as_view(), name='session_list'),
    path('sessions/schedule/', views.ScheduleSessionView.as_view(), name='schedule_session'),
    path('sessions/<int:session_id>/', views.MentorshipSessionDetailView.as_view(), name='session_detail'),
    path('sessions/<int:session_id>/cancel/', views.CancelSessionView.as_view(), name='cancel_session'),
    path('sessions/<int:session_id>/reschedule/', views.RescheduleSessionView.as_view(), name='reschedule_session'),
    path('sessions/<int:session_id>/complete/', views.CompleteSessionView.as_view(), name='complete_session'),
    
    # Feedback
    path('sessions/<int:session_id>/feedback/', views.SessionFeedbackView.as_view(), name='session_feedback'),
    path('mentorship/<int:relationship_id>/feedback/', views.MentorshipFeedbackView.as_view(), name='mentorship_feedback'),
    
    # Resources and materials
    path('resources/', views.MentorshipResourcesView.as_view(), name='resources'),
    path('resources/create/', views.CreateResourceView.as_view(), name='create_resource'),
    path('resources/<int:resource_id>/', views.ResourceDetailView.as_view(), name='resource_detail'),
    
    # Applications for becoming a mentor
    path('applications/', views.MentorApplicationListView.as_view(), name='application_list'),
    path('applications/create/', views.CreateMentorApplicationView.as_view(), name='create_application'),
    path('applications/<int:application_id>/', views.MentorApplicationDetailView.as_view(), name='application_detail'),
]
