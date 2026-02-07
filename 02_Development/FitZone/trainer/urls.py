
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
    path('trainer/dashboard/', views.trainer_dashboard, name='trainer_dashboard'),
    path('trainer/edit-profile/', views.edit_trainer_profile, name='edit_trainer_profile'),
    path('trainer/upload-photo/', views.upload_trainer_photo, name='upload_trainer_photo'),
    path('trainer/delete-photo/<int:photo_id>/', views.delete_trainer_photo, name='delete_trainer_photo'),
    path('trainerregestration/', TrainerRegistrationWizard.as_view(FORMS), name='trainerregestration'),
    path('trainer/registration-status/', views.trainer_registration_status, name='trainer_registration_status'),
  
]