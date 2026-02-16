from django import forms
from .models import (
    ClientFitnessProfile, WorkoutPlan, WorkoutDay, Exercise, DietPlan, Meal
)


# Form for users to submit their fitness data
class ClientFitnessProfileForm(forms.ModelForm):
    class Meta:
        model = ClientFitnessProfile
        fields = [
            'height_cm', 'weight_kg', 'age', 'fitness_goal',
            'activity_level', 'diet_preference', 'medical_conditions', 'allergies'
        ]
        widgets = {
            'height_cm': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 170', 'min': '50', 'max': '300', 'step': '0.1'
            }),
            'weight_kg': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 70', 'min': '20', 'max': '500', 'step': '0.1'
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 25', 'min': '10', 'max': '120'
            }),
            'fitness_goal': forms.Select(attrs={'class': 'form-select'}),
            'activity_level': forms.Select(attrs={'class': 'form-select'}),
            'diet_preference': forms.Select(attrs={'class': 'form-select'}),
            'medical_conditions': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Any injuries, conditions...'
            }),
            'allergies': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Any food allergies...'
            }),
        }


# Form for trainers to create a workout plan
class WorkoutPlanForm(forms.ModelForm):
    class Meta:
        model = WorkoutPlan
        fields = ['title', 'description', 'difficulty', 'duration_weeks', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 4-Week Muscle Building Program'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description of the plan...'
            }),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'duration_weeks': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '1', 'max': '52'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes for the client...'
            }),
        }


# Form for adding a day to a workout plan
class WorkoutDayForm(forms.ModelForm):
    class Meta:
        model = WorkoutDay
        fields = ['day', 'focus_area', 'is_rest_day']
        widgets = {
            'day': forms.Select(attrs={'class': 'form-select'}),
            'focus_area': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., Chest & Triceps'
            }),
            'is_rest_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# Form for adding an exercise to a workout day
class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['name', 'sets', 'reps', 'rest_seconds', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., Bench Press'
            }),
            'sets': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '1', 'max': '20'
            }),
            'reps': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 12, 8-12, 30 sec'
            }),
            'rest_seconds': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'max': '600'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2, 'placeholder': 'Form tips...'
            }),
        }


# Form for trainers to create a diet plan
class DietPlanForm(forms.ModelForm):
    class Meta:
        model = DietPlan
        fields = ['title', 'description', 'daily_calories', 'protein_grams', 'carbs_grams', 'fat_grams', 'duration_weeks', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., High Protein Diet Plan'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description of the diet plan...'
            }),
            'daily_calories': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 2000', 'min': '500', 'max': '10000'
            }),
            'protein_grams': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 150', 'min': '0'
            }),
            'carbs_grams': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 200', 'min': '0'
            }),
            'fat_grams': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 65', 'min': '0'
            }),
            'duration_weeks': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '1', 'max': '52'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'
            }),
        }


# Form for adding a meal to a diet plan
class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ['meal_type', 'title', 'description', 'calories', 'protein', 'carbs', 'fat', 'time']
        widgets = {
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., Oatmeal with Banana'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2, 'placeholder': 'Ingredients & recipe...'
            }),
            'calories': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'kcal', 'min': '0'
            }),
            'protein': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'g', 'min': '0'
            }),
            'carbs': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'g', 'min': '0'
            }),
            'fat': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'g', 'min': '0'
            }),
            'time': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., 7:00 AM'
            }),
        }
