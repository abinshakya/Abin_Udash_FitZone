from django.urls import path
from . import views

app_name = 'food_recommendation_system'

urlpatterns = [
    path('', views.recommendation_home, name='home'),
    path('input/', views.get_recommendation_input, name='input'),
    path('plan/<int:rec_id>/', views.view_plan, name='view_plan'),
]
