from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # 1. 後台管理路由
    path('admin/', admin.site.urls),
    
    # 2. Django 內建的驗證機制（處理登入、登出、密碼管理等）
    path('accounts/', include('django.contrib.auth.urls')),
    
    # 3. 🎯 核心分流：將所有根路徑、歷史紀錄等大權，直接交給子應用的 urls.py 處理
    path('', include('quiz.urls')), 
]