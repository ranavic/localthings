from django.urls import path
from . import views

app_name = 'gamification'

urlpatterns = [
    # Badge and achievement views
    path('badges/', views.BadgeListView.as_view(), name='badge_list'),
    path('badges/<slug:badge_slug>/', views.BadgeDetailView.as_view(), name='badge_detail'),
    path('achievements/', views.AchievementListView.as_view(), name='achievement_list'),
    path('achievements/<slug:achievement_slug>/', views.AchievementDetailView.as_view(), name='achievement_detail'),
    
    # User achievements
    path('my-badges/', views.UserBadgeListView.as_view(), name='my_badges'),
    path('my-achievements/', views.UserAchievementListView.as_view(), name='my_achievements'),
    
    # Leaderboards
    path('leaderboards/', views.LeaderboardListView.as_view(), name='leaderboard_list'),
    path('leaderboards/<slug:leaderboard_slug>/', views.LeaderboardDetailView.as_view(), name='leaderboard_detail'),
    path('leaderboards/course/<slug:course_slug>/', views.CourseLeaderboardView.as_view(), name='course_leaderboard'),
    
    # Streaks
    path('streaks/', views.UserStreakView.as_view(), name='my_streaks'),
    path('streaks/daily/', views.DailyStreakView.as_view(), name='daily_streak'),
    
    # Challenges
    path('challenges/', views.ChallengeListView.as_view(), name='challenge_list'),
    path('challenges/<slug:challenge_slug>/', views.ChallengeDetailView.as_view(), name='challenge_detail'),
    path('challenges/active/', views.ActiveChallengesView.as_view(), name='active_challenges'),
    path('challenges/completed/', views.CompletedChallengesView.as_view(), name='completed_challenges'),
    
    # Points and rewards
    path('points/', views.PointsHistoryView.as_view(), name='points_history'),
    path('rewards/', views.RewardListView.as_view(), name='reward_list'),
    path('rewards/<slug:reward_slug>/', views.RewardDetailView.as_view(), name='reward_detail'),
    path('rewards/redeem/<slug:reward_slug>/', views.RedeemRewardView.as_view(), name='redeem_reward'),
    
    # Quests
    path('quests/', views.QuestListView.as_view(), name='quest_list'),
    path('quests/<slug:quest_slug>/', views.QuestDetailView.as_view(), name='quest_detail'),
    path('quests/my-progress/', views.UserQuestProgressView.as_view(), name='quest_progress'),
]
