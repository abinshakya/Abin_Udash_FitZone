from django.urls import path
from . import views

urlpatterns = [
    path('membership/', views.membership_page, name='membership'),
    path('membership/my-plans/', views.my_plans_page, name='member_plans'),
   
]
