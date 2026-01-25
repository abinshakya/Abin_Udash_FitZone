from django.urls import path
from . import views

urlpatterns = [
    path('membership/', views.membership_page, name='membership'),
   
]
