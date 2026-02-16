from django.urls import path
from . import views

urlpatterns = [
    # Membership payment
    path('checkout/<int:plan_id>/', views.checkout, name='checkout'),
    path('initiate/<int:plan_id>/', views.initiate_khalti_payment, name='initiate_payment'),
    path('callback/', views.payment_callback, name='payment_callback'),
    path('verify/<str:pidx>/', views.verify_payment, name='verify_payment'),
    path('failed/<str:pidx>/', views.payment_failed, name='payment_failed'),

    # Trainer booking payment
    path('booking-checkout/<int:booking_id>/', views.booking_checkout, name='booking_checkout'),
    path('booking-initiate/<int:booking_id>/', views.initiate_booking_payment, name='initiate_booking_payment'),
]
