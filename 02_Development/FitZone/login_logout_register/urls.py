from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('auth/google/', views.google_oauth_begin, name='google_oauth_begin'),
    path('logout/', views.user_logout, name='logout'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('send-verification-otp/', views.send_verification_otp, name='send_verification_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
]
