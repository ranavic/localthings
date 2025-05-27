from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Chat room management
    path('', views.ChatHomeView.as_view(), name='home'),
    path('rooms/', views.ChatRoomListView.as_view(), name='room_list'),
    path('rooms/create/', views.CreateChatRoomView.as_view(), name='create_room'),
    path('rooms/<str:room_id>/', views.ChatRoomView.as_view(), name='room'),
    path('rooms/<str:room_id>/settings/', views.ChatRoomSettingsView.as_view(), name='room_settings'),
    path('rooms/<str:room_id>/leave/', views.LeaveChatRoomView.as_view(), name='leave_room'),
    
    # Direct messaging
    path('direct/', views.DirectMessageListView.as_view(), name='direct_messages'),
    path('direct/<str:username>/', views.DirectMessageView.as_view(), name='direct_message'),
    
    # Course and group chats
    path('course/<slug:course_slug>/', views.CourseDiscussionView.as_view(), name='course_discussion'),
    path('group/<int:group_id>/', views.GroupChatView.as_view(), name='group_chat'),
    
    # Message management
    path('messages/unread/', views.UnreadMessagesView.as_view(), name='unread_messages'),
    path('messages/<int:message_id>/delete/', views.DeleteMessageView.as_view(), name='delete_message'),
    path('messages/<int:message_id>/report/', views.ReportMessageView.as_view(), name='report_message'),
    
    # Attachments
    path('attachments/upload/', views.UploadAttachmentView.as_view(), name='upload_attachment'),
    path('attachments/<int:attachment_id>/', views.AttachmentView.as_view(), name='view_attachment'),
    
    # Reactions
    path('messages/<int:message_id>/reactions/', views.MessageReactionsView.as_view(), name='message_reactions'),
    path('messages/<int:message_id>/reactions/add/', views.AddReactionView.as_view(), name='add_reaction'),
    
    # Status
    path('status/update/', views.UpdateStatusView.as_view(), name='update_status'),
    path('status/<str:username>/', views.UserStatusView.as_view(), name='user_status'),
]
