from django.contrib import admin
from .models import (
    ClientFitnessProfile, WorkoutPlan, WorkoutDay, Exercise, DietPlan, Meal
)


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 0


class WorkoutDayInline(admin.TabularInline):
    model = WorkoutDay
    extra = 0


class MealInline(admin.TabularInline):
    model = Meal
    extra = 0


@admin.register(ClientFitnessProfile)
class ClientFitnessProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'height_cm', 'weight_kg', 'age', 'fitness_goal', 'activity_level', 'created_at']
    list_filter = ['fitness_goal', 'activity_level', 'diet_preference']
    search_fields = ['user__username', 'user__email']


@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'trainer', 'client', 'difficulty', 'duration_weeks', 'is_active', 'created_at']
    list_filter = ['difficulty', 'is_active']
    search_fields = ['title', 'client__username', 'trainer__user__username']
    inlines = [WorkoutDayInline]


@admin.register(WorkoutDay)
class WorkoutDayAdmin(admin.ModelAdmin):
    list_display = ['workout_plan', 'day', 'focus_area', 'is_rest_day']
    inlines = [ExerciseInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['name', 'workout_day', 'sets', 'reps', 'rest_seconds']


@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'trainer', 'client', 'daily_calories', 'duration_weeks', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['title', 'client__username', 'trainer__user__username']
    inlines = [MealInline]


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ['title', 'diet_plan', 'meal_type', 'calories', 'time']
