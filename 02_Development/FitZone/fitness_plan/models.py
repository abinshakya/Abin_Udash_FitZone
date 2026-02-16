from django.db import models
from django.conf import settings
from trainer.models import TrainerRegistration, TrainerBooking


# Stores user fitness data (height, weight, age, goals, etc.) required before plans can be created
class ClientFitnessProfile(models.Model):
    GOAL_CHOICES = [
        ('weight_loss', 'Weight Loss'),
        ('muscle_gain', 'Muscle Gain'),
        ('maintain', 'Maintain Fitness'),
        ('endurance', 'Improve Endurance'),
        ('flexibility', 'Improve Flexibility'),
        ('general', 'General Fitness'),
    ]

    ACTIVITY_CHOICES = [
        ('sedentary', 'Sedentary (Little or no exercise)'),
        ('light', 'Lightly Active (1-3 days/week)'),
        ('moderate', 'Moderately Active (3-5 days/week)'),
        ('active', 'Very Active (6-7 days/week)'),
        ('extreme', 'Extremely Active (Athlete)'),
    ]

    DIET_PREFERENCE_CHOICES = [
        ('no_preference', 'No Preference'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('non_veg', 'Non-Vegetarian'),
        ('eggetarian', 'Eggetarian'),
        ('keto', 'Keto'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fitness_profile')
    booking = models.ForeignKey(TrainerBooking, on_delete=models.CASCADE, related_name='fitness_profiles', null=True, blank=True)

    # Body measurements
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, help_text="Height in cm")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, help_text="Weight in kg")
    age = models.PositiveIntegerField()

    # Fitness info
    fitness_goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='general')
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='sedentary')
    diet_preference = models.CharField(max_length=20, choices=DIET_PREFERENCE_CHOICES, default='no_preference')

    # Health info
    medical_conditions = models.TextField(blank=True, null=True, help_text="Any medical conditions or injuries")
    allergies = models.TextField(blank=True, null=True, help_text="Any food allergies")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Fitness Profile"

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            height_m = float(self.height_cm) / 100
            return round(float(self.weight_kg) / (height_m ** 2), 1)
        return None

    @property
    def bmi_category(self):
        bmi = self.bmi
        if bmi is None:
            return "Unknown"
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"


# Workout plan created by a trainer for a client
class WorkoutPlan(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    trainer = models.ForeignKey(TrainerRegistration, on_delete=models.CASCADE, related_name='workout_plans')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_plans')
    booking = models.ForeignKey(TrainerBooking, on_delete=models.CASCADE, related_name='workout_plans', null=True, blank=True)

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_CHOICES, default='beginner')
    duration_weeks = models.PositiveIntegerField(default=4, help_text="Plan duration in weeks")
    notes = models.TextField(blank=True, null=True, help_text="Additional trainer notes")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.client.username}"


# A single day within a workout plan
class WorkoutDay(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]

    workout_plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name='days')
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    focus_area = models.CharField(max_length=100, help_text="e.g., Chest & Triceps, Legs, Cardio, Rest")
    is_rest_day = models.BooleanField(default=False)

    class Meta:
        ordering = ['day']
        unique_together = ('workout_plan', 'day')

    def __str__(self):
        return f"{self.get_day_display()} - {self.focus_area}"


# Individual exercise within a workout day
class Exercise(models.Model):
    workout_day = models.ForeignKey(WorkoutDay, on_delete=models.CASCADE, related_name='exercises')
    name = models.CharField(max_length=150)
    sets = models.PositiveIntegerField(default=3)
    reps = models.CharField(max_length=50, help_text="e.g., 12, 8-12, 30 sec")
    rest_seconds = models.PositiveIntegerField(default=60, help_text="Rest time between sets in seconds")
    notes = models.TextField(blank=True, null=True, help_text="Form tips, modifications, etc.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} - {self.sets}x{self.reps}"


# Diet plan created by a trainer for a client
class DietPlan(models.Model):
    trainer = models.ForeignKey(TrainerRegistration, on_delete=models.CASCADE, related_name='diet_plans')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='diet_plans')
    booking = models.ForeignKey(TrainerBooking, on_delete=models.CASCADE, related_name='diet_plans', null=True, blank=True)

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    daily_calories = models.PositiveIntegerField(blank=True, null=True, help_text="Target daily calories")
    protein_grams = models.PositiveIntegerField(blank=True, null=True)
    carbs_grams = models.PositiveIntegerField(blank=True, null=True)
    fat_grams = models.PositiveIntegerField(blank=True, null=True)
    duration_weeks = models.PositiveIntegerField(default=4, help_text="Plan duration in weeks")
    notes = models.TextField(blank=True, null=True, help_text="Additional trainer notes")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.client.username}"


# A meal within a diet plan
class Meal(models.Model):
    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('morning_snack', 'Morning Snack'),
        ('lunch', 'Lunch'),
        ('afternoon_snack', 'Afternoon Snack'),
        ('dinner', 'Dinner'),
        ('evening_snack', 'Evening Snack'),
    ]

    diet_plan = models.ForeignKey(DietPlan, on_delete=models.CASCADE, related_name='meals')
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    title = models.CharField(max_length=200, help_text="e.g., Oatmeal with Fruits")
    description = models.TextField(blank=True, null=True, help_text="Detailed description/recipe")
    calories = models.PositiveIntegerField(blank=True, null=True)
    protein = models.PositiveIntegerField(blank=True, null=True, help_text="Protein in grams")
    carbs = models.PositiveIntegerField(blank=True, null=True, help_text="Carbs in grams")
    fat = models.PositiveIntegerField(blank=True, null=True, help_text="Fat in grams")
    time = models.CharField(max_length=20, blank=True, null=True, help_text="e.g., 7:00 AM")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.get_meal_type_display()} - {self.title}"
