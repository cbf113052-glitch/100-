from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 🎯 1. 登入與首頁
    path('', auth_views.LoginView.as_view(), name='login'),
    path('login/', auth_views.LoginView.as_view(), name='login'),

    # 🎯 2. 主畫面控制台
    path('dashboard/', views.dashboard, name='dashboard'),

    # 🎯 3. 歷史紀錄與分析頁面
    path('dashboard/history/', views.quiz_history_view, name='quiz_history'),
    path('dashboard/history/<int:history_id>/', views.quiz_detail_view, name='quiz_detail'),

    # 🎯 4. 學生註冊與登出
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # 🎯 5. 測驗功能核心 (準備入口、線上作答)
    path('quiz/ready/', views.quiz_ready_view, name='quiz_ready'),
    path('quiz/', views.quiz_view, name='quiz_view'),

    # 🎯 6. 題庫網頁總覽
    path('bank/', views.bank_view, name='bank_page'),

    # 🎯 7. 智慧錯題專區 (統計面板、單題重新挑戰)
    path('wrong-questions/', views.wrong_questions_summary_view, name='wrong_questions'),
    path('retry-question/<int:question_id>/', views.retry_single_question_view, name='retry_single_question'),
]