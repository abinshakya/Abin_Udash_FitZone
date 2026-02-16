from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User

from trainer.models import TrainerRegistration, TrainerBooking
from .models import (
    ClientFitnessProfile, WorkoutPlan, WorkoutDay, Exercise, DietPlan, Meal
)
from .forms import (
    ClientFitnessProfileForm, WorkoutPlanForm, WorkoutDayForm,
    ExerciseForm, DietPlanForm, MealForm
)


# ─── Helper: Check if user has paid booking with a given trainer ───
# Return True if the user has a confirmed+paid booking with this trainer
def has_paid_booking(user, trainer_reg):
    return TrainerBooking.objects.filter(
        user=user,
        trainer=trainer_reg,
        status='confirmed',
        payment_status='completed',
    ).exists()


# Return the confirmed+paid booking between user and trainer
def get_paid_booking(user, trainer_reg):
    return TrainerBooking.objects.filter(
        user=user,
        trainer=trainer_reg,
        status='confirmed',
        payment_status='completed',
    ).first()


# ════════════════════════════════════════════════════════
#  CLIENT FITNESS PROFILE  (User fills out their data)
# ════════════════════════════════════════════════════════

@login_required
# View/edit the user's fitness profile. Only accessible with a paid booking
def fitness_profile(request):
    # Check for at least one paid booking
    paid_booking = TrainerBooking.objects.filter(
        user=request.user,
        status='confirmed',
        payment_status='completed',
    ).first()

    if not paid_booking:
        messages.warning(request, "You need an active paid trainer booking to access fitness plans. Please book and pay a trainer first.")
        return redirect('trainer')

    profile = ClientFitnessProfile.objects.filter(user=request.user).first()

    if request.method == 'POST':
        form = ClientFitnessProfileForm(request.POST, instance=profile)
        if form.is_valid():
            fp = form.save(commit=False)
            fp.user = request.user
            fp.booking = paid_booking
            fp.save()
            messages.success(request, "Fitness profile saved successfully!")
            return redirect('fitness_profile')
    else:
        form = ClientFitnessProfileForm(instance=profile)

    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'fitness_plan/fitness_profile.html', context)


# ════════════════════════════════════════════════════════
#  VIEW MY PLANS (Client views plans assigned to them)
# ════════════════════════════════════════════════════════

@login_required
# Client views their workout and diet plans
def my_plans(request):
    paid_booking = TrainerBooking.objects.filter(
        user=request.user,
        status='confirmed',
        payment_status='completed',
    ).first()

    if not paid_booking:
        messages.warning(request, "You need an active paid trainer booking to access fitness plans.")
        return redirect('trainer')

    workout_plans = WorkoutPlan.objects.filter(client=request.user, is_active=True).prefetch_related('days__exercises')
    diet_plans = DietPlan.objects.filter(client=request.user, is_active=True).prefetch_related('meals')
    fitness_profile_obj = ClientFitnessProfile.objects.filter(user=request.user).first()

    context = {
        'workout_plans': workout_plans,
        'diet_plans': diet_plans,
        'fitness_profile': fitness_profile_obj,
        'has_fitness_profile': fitness_profile_obj is not None,
    }
    return render(request, 'fitness_plan/my_plans.html', context)


@login_required
# Client views a specific workout plan
def view_workout_plan(request, plan_id):
    plan = get_object_or_404(WorkoutPlan, id=plan_id, client=request.user)
    days = plan.days.prefetch_related('exercises').all()

    context = {
        'plan': plan,
        'days': days,
    }
    return render(request, 'fitness_plan/view_workout_plan.html', context)


@login_required
# Client views a specific diet plan
def view_diet_plan(request, plan_id):
    plan = get_object_or_404(DietPlan, id=plan_id, client=request.user)
    meals = plan.meals.all()

    context = {
        'plan': plan,
        'meals': meals,
    }
    return render(request, 'fitness_plan/view_diet_plan.html', context)


# ════════════════════════════════════════════════════════
#  TRAINER: CLIENT LIST (all paid clients)
# ════════════════════════════════════════════════════════

@login_required
# Trainer sees all clients who have paid bookings
def trainer_client_list(request):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied.")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    if not registration:
        messages.error(request, "Trainer registration not found.")
        return redirect('/')

    # Get all paid bookings
    paid_bookings = TrainerBooking.objects.filter(
        trainer=registration,
        status='confirmed',
        payment_status='completed',
    ).select_related('user').order_by('-updated_at')

    clients_data = []
    for booking in paid_bookings:
        fp = ClientFitnessProfile.objects.filter(user=booking.user).first()
        workout_count = WorkoutPlan.objects.filter(trainer=registration, client=booking.user, is_active=True).count()
        diet_count = DietPlan.objects.filter(trainer=registration, client=booking.user, is_active=True).count()
        clients_data.append({
            'booking': booking,
            'user': booking.user,
            'fitness_profile': fp,
            'workout_count': workout_count,
            'diet_count': diet_count,
        })

    context = {
        'clients_data': clients_data,
        'registration': registration,
    }
    return render(request, 'fitness_plan/trainer_client_list.html', context)


# ════════════════════════════════════════════════════════
#  TRAINER: VIEW CLIENT PROFILE
# ════════════════════════════════════════════════════════

@login_required
# Trainer views a client's fitness profile and existing plans
def trainer_view_client(request, user_id):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied.")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    client = get_object_or_404(User, id=user_id)

    # Verify paid booking exists
    if not has_paid_booking(client, registration):
        messages.error(request, "This client doesn't have a paid booking with you.")
        return redirect('trainer_client_list')

    fitness_profile_obj = ClientFitnessProfile.objects.filter(user=client).first()
    workout_plans = WorkoutPlan.objects.filter(trainer=registration, client=client).prefetch_related('days__exercises')
    diet_plans = DietPlan.objects.filter(trainer=registration, client=client).prefetch_related('meals')

    context = {
        'client': client,
        'fitness_profile': fitness_profile_obj,
        'workout_plans': workout_plans,
        'diet_plans': diet_plans,
        'registration': registration,
    }
    return render(request, 'fitness_plan/trainer_view_client.html', context)


# ════════════════════════════════════════════════════════
#  TRAINER: CREATE WORKOUT PLAN
# ════════════════════════════════════════════════════════

@login_required
# Trainer creates a workout plan for a specific client
def create_workout_plan(request, user_id):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied.")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    client = get_object_or_404(User, id=user_id)
    booking = get_paid_booking(client, registration)

    if not booking:
        messages.error(request, "This client doesn't have a paid booking with you.")
        return redirect('trainer_client_list')

    # Check if client has fitness profile
    fitness_profile_obj = ClientFitnessProfile.objects.filter(user=client).first()
    if not fitness_profile_obj:
        messages.warning(request, "This client hasn't filled out their fitness profile yet. Please ask them to complete it first.")
        return redirect('trainer_view_client', user_id=user_id)

    if request.method == 'POST':
        form = WorkoutPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.trainer = registration
            plan.client = client
            plan.booking = booking
            plan.save()
            messages.success(request, f"Workout plan '{plan.title}' created! Now add workout days.")
            return redirect('edit_workout_plan', plan_id=plan.id)
    else:
        form = WorkoutPlanForm()

    context = {
        'form': form,
        'client': client,
        'fitness_profile': fitness_profile_obj,
    }
    return render(request, 'fitness_plan/create_workout_plan.html', context)


@login_required
# Trainer edits/manages workout plan days and exercises
def edit_workout_plan(request, plan_id):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied.")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    plan = get_object_or_404(WorkoutPlan, id=plan_id, trainer=registration)
    days = plan.days.prefetch_related('exercises').all()
    day_form = WorkoutDayForm()
    exercise_form = ExerciseForm()

    context = {
        'plan': plan,
        'days': days,
        'day_form': day_form,
        'exercise_form': exercise_form,
        'client': plan.client,
    }
    return render(request, 'fitness_plan/edit_workout_plan.html', context)


@login_required
# Add a day to a workout plan
def add_workout_day(request, plan_id):
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    plan = get_object_or_404(WorkoutPlan, id=plan_id, trainer=registration)

    if request.method == 'POST':
        form = WorkoutDayForm(request.POST)
        if form.is_valid():
            day = form.save(commit=False)
            day.workout_plan = plan
            try:
                day.save()
                messages.success(request, f"{day.get_day_display()} added!")
            except Exception:
                messages.error(request, "This day already exists in the plan.")
        else:
            messages.error(request, "Invalid data. Please check the form.")

    return redirect('edit_workout_plan', plan_id=plan.id)


@login_required
# Add an exercise to a workout day
def add_exercise(request, day_id):
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    day = get_object_or_404(WorkoutDay, id=day_id, workout_plan__trainer=registration)

    if request.method == 'POST':
        form = ExerciseForm(request.POST)
        if form.is_valid():
            exercise = form.save(commit=False)
            exercise.workout_day = day
            exercise.order = day.exercises.count() + 1
            exercise.save()
            messages.success(request, f"Exercise '{exercise.name}' added!")
        else:
            messages.error(request, "Invalid data.")

    return redirect('edit_workout_plan', plan_id=day.workout_plan.id)


@login_required
# Delete an exercise
def delete_exercise(request, exercise_id):
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    exercise = get_object_or_404(Exercise, id=exercise_id, workout_day__workout_plan__trainer=registration)
    plan_id = exercise.workout_day.workout_plan.id
    exercise.delete()
    messages.success(request, "Exercise removed.")
    return redirect('edit_workout_plan', plan_id=plan_id)


@login_required
# Delete a workout day and all its exercises
def delete_workout_day(request, day_id):
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    day = get_object_or_404(WorkoutDay, id=day_id, workout_plan__trainer=registration)
    plan_id = day.workout_plan.id
    day.delete()
    messages.success(request, "Workout day removed.")
    return redirect('edit_workout_plan', plan_id=plan_id)


@login_required
# Delete a workout plan
def delete_workout_plan(request, plan_id):
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    plan = get_object_or_404(WorkoutPlan, id=plan_id, trainer=registration)
    user_id = plan.client.id
    plan.delete()
    messages.success(request, "Workout plan deleted.")
    return redirect('trainer_view_client', user_id=user_id)


# ════════════════════════════════════════════════════════
#  TRAINER: CREATE DIET PLAN
# ════════════════════════════════════════════════════════

@login_required
# Trainer creates a diet plan for a specific client
def create_diet_plan(request, user_id):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied.")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    client = get_object_or_404(User, id=user_id)
    booking = get_paid_booking(client, registration)

    if not booking:
        messages.error(request, "This client doesn't have a paid booking with you.")
        return redirect('trainer_client_list')

    fitness_profile_obj = ClientFitnessProfile.objects.filter(user=client).first()
    if not fitness_profile_obj:
        messages.warning(request, "This client hasn't filled out their fitness profile yet. Please ask them to complete it first.")
        return redirect('trainer_view_client', user_id=user_id)

    if request.method == 'POST':
        form = DietPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.trainer = registration
            plan.client = client
            plan.booking = booking
            plan.save()
            messages.success(request, f"Diet plan '{plan.title}' created! Now add meals.")
            return redirect('edit_diet_plan', plan_id=plan.id)
    else:
        form = DietPlanForm()

    context = {
        'form': form,
        'client': client,
        'fitness_profile': fitness_profile_obj,
    }
    return render(request, 'fitness_plan/create_diet_plan.html', context)


@login_required
# Trainer edits/manages diet plan meals
def edit_diet_plan(request, plan_id):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied.")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    plan = get_object_or_404(DietPlan, id=plan_id, trainer=registration)
    meals = plan.meals.all()
    meal_form = MealForm()

    context = {
        'plan': plan,
        'meals': meals,
        'meal_form': meal_form,
        'client': plan.client,
    }
    return render(request, 'fitness_plan/edit_diet_plan.html', context)


@login_required
# Add a meal to a diet plan
def add_meal(request, plan_id):
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    plan = get_object_or_404(DietPlan, id=plan_id, trainer=registration)

    if request.method == 'POST':
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.diet_plan = plan
            meal.order = plan.meals.count() + 1
            meal.save()
            messages.success(request, f"Meal '{meal.title}' added!")
        else:
            messages.error(request, "Invalid data.")

    return redirect('edit_diet_plan', plan_id=plan.id)


@login_required
# Delete a meal
def delete_meal(request, meal_id):
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    meal = get_object_or_404(Meal, id=meal_id, diet_plan__trainer=registration)
    plan_id = meal.diet_plan.id
    meal.delete()
    messages.success(request, "Meal removed.")
    return redirect('edit_diet_plan', plan_id=plan_id)


@login_required
# Delete a diet plan
def delete_diet_plan(request, plan_id):
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    plan = get_object_or_404(DietPlan, id=plan_id, trainer=registration)
    user_id = plan.client.id
    plan.delete()
    messages.success(request, "Diet plan deleted.")
    return redirect('trainer_view_client', user_id=user_id)
