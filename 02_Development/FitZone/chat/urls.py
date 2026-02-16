from django.urls import path
from . import views

urlpatterns = [
    path('chat/trainer/', views.trainer_chat, name='trainer_chat'),
    path('chat/client/', views.client_chat, name='client_chat'),
    path('chat/send/<int:room_id>/', views.send_message, name='send_message'),
    path('chat/fetch/<int:room_id>/', views.fetch_messages, name='fetch_messages'),
    path('chat/fetch-list/', views.fetch_chat_list, name='fetch_chat_list'),
    path('chat/start/<int:trainer_id>/', views.start_chat_with_trainer, name='start_chat_with_trainer'),
]
