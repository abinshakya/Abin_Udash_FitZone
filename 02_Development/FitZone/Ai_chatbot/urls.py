from django.urls import path
from . import views

app_name = 'Ai_chatbot'

urlpatterns = [
    path('', views.ai_chat, name='ai_chat'),
]
