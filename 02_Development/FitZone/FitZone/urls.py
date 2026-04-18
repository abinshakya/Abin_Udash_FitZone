"""
URL configuration for FitZone project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from FitZone import views
from login_logout_register import views as login_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('social-auth/', include('social_django.urls', namespace='social')),
    path('google/profile-complete/', login_views.google_profile_wizard_entry, name='google_profile_complete_entry'),
    path('member/user_dashboard/', views.user_dashboard, name='user_dashboard'),
    path('member/settings/', views.member_settings, name='member_settings'),
    path('ai_chat/', include('Ai_chatbot.urls')),
    path('my-trainer-dashboard/', views.trainer_client_dashboard, name='trainer_client_dashboard'),
    path('my-trainers/', views.trainer_client_my_trainers, name='trainer_client_my_trainers'),
    path('', include('login_logout_register.urls')),
    path('', include('membership.urls')),
    path('', include('payment.urls')),
    path('', include('trainer.urls')),
    path('notifications/', include('notifications.urls')),
    path('', include('chat.urls')),
    path('', include('fitness_plan.urls')),
    path('food-recommendation/', include('food_recommendation_system.urls')),
    path('about/', views.about, name='about'),
    path('contact-us/', views.contact_us, name='contact_us'),
]

# 404 - Page Not Found
handler404 = 'FitZone.views.handler404'

# 500 - Internal Server Error
handler500 = 'FitZone.views.handler500'

# 403 - Forbidden/Permission Denied
handler403 = 'FitZone.views.handler403'

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)