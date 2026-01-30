from django.urls import path
from . import views

urlpatterns = [
    path('checkout/<int:plan_id>/', views.checkout, name='checkout'),
]
