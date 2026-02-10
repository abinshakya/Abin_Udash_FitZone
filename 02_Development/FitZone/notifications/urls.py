from django.urls import path
from . import views

urlpatterns = [
    # Trainer Notifications (keeping old URL names for compatibility)
    path('trainer/<int:notif_id>/read/', views.mark_trainer_notification_read, name='mark_notification_read'),
    path('trainer/read-all/', views.mark_all_trainer_notifications_read, name='mark_all_notifications_read'),
    
    # User Notifications (keeping old URL names for compatibility)
    path('user/<int:notif_id>/read/', views.mark_user_notification_read, name='user_mark_notification_read'),
    path('user/read-all/', views.mark_all_user_notifications_read, name='user_mark_all_notifications_read'),
]
