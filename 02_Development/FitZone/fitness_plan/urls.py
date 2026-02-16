from django.urls import path
from . import views

urlpatterns = [
    # ── Client URLs ──
    path('fitness/profile/', views.fitness_profile, name='fitness_profile'),
    path('fitness/my-plans/', views.my_plans, name='my_plans'),
    path('fitness/workout/<int:plan_id>/', views.view_workout_plan, name='view_workout_plan'),
    path('fitness/diet/<int:plan_id>/', views.view_diet_plan, name='view_diet_plan'),

    # ── Trainer URLs ──
    path('trainer/clients/plans/', views.trainer_client_list, name='trainer_client_list'),
    path('trainer/client/<int:user_id>/view/', views.trainer_view_client, name='trainer_view_client'),

    # Workout plan management
    path('trainer/client/<int:user_id>/workout/create/', views.create_workout_plan, name='create_workout_plan'),
    path('trainer/workout/<int:plan_id>/edit/', views.edit_workout_plan, name='edit_workout_plan'),
    path('trainer/workout/<int:plan_id>/add-day/', views.add_workout_day, name='add_workout_day'),
    path('trainer/workout/day/<int:day_id>/add-exercise/', views.add_exercise, name='add_exercise'),
    path('trainer/workout/exercise/<int:exercise_id>/delete/', views.delete_exercise, name='delete_exercise'),
    path('trainer/workout/day/<int:day_id>/delete/', views.delete_workout_day, name='delete_workout_day'),
    path('trainer/workout/<int:plan_id>/delete/', views.delete_workout_plan, name='delete_workout_plan'),

    # Diet plan management
    path('trainer/client/<int:user_id>/diet/create/', views.create_diet_plan, name='create_diet_plan'),
    path('trainer/diet/<int:plan_id>/edit/', views.edit_diet_plan, name='edit_diet_plan'),
    path('trainer/diet/<int:plan_id>/add-meal/', views.add_meal, name='add_meal'),
    path('trainer/diet/meal/<int:meal_id>/delete/', views.delete_meal, name='delete_meal'),
    path('trainer/diet/<int:plan_id>/delete/', views.delete_diet_plan, name='delete_diet_plan'),
]
