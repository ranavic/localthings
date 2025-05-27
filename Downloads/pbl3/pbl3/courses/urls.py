from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Course listings
    path('', views.CourseListView.as_view(), name='course_list'),
    path('category/<slug:category_slug>/', views.CourseListByCategoryView.as_view(), name='course_list_by_category'),
    path('tag/<slug:tag_slug>/', views.CourseListByTagView.as_view(), name='course_list_by_tag'),
    path('difficulty/<slug:difficulty_slug>/', views.CourseListByDifficultyView.as_view(), name='course_list_by_difficulty'),
    
    # Course detail and enrollment
    path('<slug:course_slug>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('<slug:course_slug>/enroll/', views.CourseEnrollView.as_view(), name='course_enroll'),
    path('<slug:course_slug>/unenroll/', views.CourseUnenrollView.as_view(), name='course_unenroll'),
    
    # Module and lesson views
    path('<slug:course_slug>/modules/', views.ModuleListView.as_view(), name='module_list'),
    path('<slug:course_slug>/modules/<int:module_id>/', views.ModuleDetailView.as_view(), name='module_detail'),
    path('<slug:course_slug>/modules/<int:module_id>/lessons/<int:lesson_id>/', views.LessonDetailView.as_view(), name='lesson_detail'),
    
    # Course completion and progress
    path('<slug:course_slug>/progress/', views.CourseProgressView.as_view(), name='course_progress'),
    path('<slug:course_slug>/complete/', views.CourseCompleteView.as_view(), name='course_complete'),
    
    # Reviews
    path('<slug:course_slug>/reviews/', views.CourseReviewListView.as_view(), name='course_reviews'),
    path('<slug:course_slug>/reviews/add/', views.CourseReviewCreateView.as_view(), name='add_review'),
    path('<slug:course_slug>/reviews/<int:review_id>/edit/', views.CourseReviewUpdateView.as_view(), name='edit_review'),
    path('<slug:course_slug>/reviews/<int:review_id>/delete/', views.CourseReviewDeleteView.as_view(), name='delete_review'),
    
    # User course management
    path('my-courses/', views.UserCourseListView.as_view(), name='my_courses'),
    path('wishlist/', views.UserWishlistView.as_view(), name='wishlist'),
    path('recommended/', views.RecommendedCoursesView.as_view(), name='recommended_courses'),
]
