
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import TrainerRegistrationWizard, FORMS

urlpatterns = [
    path('trainer/', views.trainer, name='trainer'),
    path('trainer/dashboard/', views.trainer_dashboard, name='trainer_dashboard'),
    path('trainerregestration/', TrainerRegistrationWizard.as_view(FORMS), name='trainerregestration'),
    path('trainer/registration-status/', views.trainer_registration_status, name='trainer_registration_status'),
  
]