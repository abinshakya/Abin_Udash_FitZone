from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('send-verification-otp/', views.send_verification_otp, name='send_verification_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
]
