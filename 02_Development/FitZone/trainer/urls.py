
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import TrainerRegistrationWizard, FORMS

urlpatterns = [
    path('trainer/', views.trainer, name='trainer'),
    path('trainer/<int:trainer_id>/profile/', views.trainer_profile_detail, name='trainer_profile_detail'),
    path('trainer/<int:trainer_id>/booking/', views.trainer_booking_modal, name='trainer_booking_modal'),
    path('trainer/<int:trainer_id>/book/', views.book_trainer, name='book_trainer'),
    path('trainer/dashboard/', views.trainer_dashboard, name='trainer_dashboard'),
    path('trainer/edit-profile/', views.edit_trainer_profile, name='edit_trainer_profile'),
    path('trainer/upload-photo/', views.upload_trainer_photo, name='upload_trainer_photo'),
    path('trainer/delete-photo/<int:photo_id>/', views.delete_trainer_photo, name='delete_trainer_photo'),
    path('trainer/booking/<int:booking_id>/update/', views.update_booking_status, name='update_booking_status'),
    path('trainer/notification/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('trainer/notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('user/notification/<int:notif_id>/read/', views.user_mark_notification_read, name='user_mark_notification_read'),
    path('user/notifications/read-all/', views.user_mark_all_notifications_read, name='user_mark_all_notifications_read'),
    path('user/booking/<int:booking_id>/cancel/', views.user_cancel_booking, name='user_cancel_booking'),
    path('trainerregestration/', TrainerRegistrationWizard.as_view(FORMS), name='trainerregestration'),
    path('trainer/registration-status/', views.trainer_registration_status, name='trainer_registration_status'),
  
]