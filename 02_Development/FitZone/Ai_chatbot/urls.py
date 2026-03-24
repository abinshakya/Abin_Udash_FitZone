from django.urls import path
from . import views

app_name = 'Ai_chatbot'

urlpatterns = [
    path('', views.ai_chat, name='ai_chat'),
    path('get_response/', views.get_ai_response, name='get_ai_response'),
]
