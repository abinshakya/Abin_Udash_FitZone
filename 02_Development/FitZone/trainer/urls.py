
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('trainer/', views.trainer),
    path('trainer/dashboard/', views.trainer_dashboard, name='trainer_dashboard'),
    path('trainerregestration/', views.trainerregestration, name='trainerregestration'),  
  
]