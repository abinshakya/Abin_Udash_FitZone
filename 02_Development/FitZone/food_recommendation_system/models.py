from django.db import models
from django.contrib.auth.models import User

class FoodRecommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    age = models.IntegerField()
    height = models.FloatField()
    current_weight = models.FloatField()
    target_weight = models.FloatField()
    gender = models.CharField(max_length=1)
    activity_level = models.CharField(max_length=20)
    food_pref = models.CharField(max_length=10)
    cuisine = models.CharField(max_length=50)
    
    bmi = models.FloatField()
    bmi_category = models.CharField(max_length=20)
    target_calories = models.FloatField()
    tdee = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation for {self.user.username} on {self.created_at.date()}"

class DailyMealPlan(models.Model):
    recommendations_record = models.ForeignKey(FoodRecommendation, related_name='meal_plans', on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=10) # Sunday, Monday, etc.
    
    breakfast_options = models.JSONField()
    lunch_options = models.JSONField()
    dinner_options = models.JSONField()

    def __str__(self):
        return f"{self.day_of_week} Plan for {self.recommendations_record.user.username}"

