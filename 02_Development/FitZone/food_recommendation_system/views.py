from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import FoodRecommendation, DailyMealPlan
from membership.models import UserMembership
from django.utils import timezone
from .recommendation_engine import get_recommendations

def is_member(user):
    return UserMembership.objects.filter(user=user, is_active=True, end_date__gt=timezone.now()).exists()

@login_required
def recommendation_home(request):
    if not is_member(request.user):
        return render(request, 'food_recommendation_system/membership_required.html')
    
    last_rec = FoodRecommendation.objects.filter(user=request.user).order_by('-created_at').first()
    return render(request, 'food_recommendation_system/home.html', {'last_rec': last_rec})

@login_required
def get_recommendation_input(request):
    if not is_member(request.user):
        return render(request, 'food_recommendation_system/membership_required.html')

    if request.method == 'POST':
        try:
            age = int(request.POST['age'])
            height = float(request.POST['height'])
            current_weight = float(request.POST['current_weight'])
            target_weight = float(request.POST['target_weight'])
            gender = request.POST['gender']
            activity_level = request.POST['activity_level']
            food_pref = request.POST['food_pref']
            cuisine = request.POST.get('cuisine', 'all') or 'all'

            result = get_recommendations(age, height, current_weight, target_weight, gender, activity_level, food_pref, cuisine)

            if "error" in result:
                return render(request, 'food_recommendation_system/input_form.html', {'error': result['error']})

            rec = FoodRecommendation.objects.create(
                user=request.user,
                age=age,
                height=height,
                current_weight=current_weight,
                target_weight=target_weight,
                gender=gender,
                activity_level=activity_level,
                food_pref=food_pref,
                cuisine=cuisine,
                bmi=result['meta']['bmi'],
                bmi_category=result['meta']['bmi_category'],
                target_calories=result['meta']['target_calories'],
                tdee=result['meta']['tdee']
            )

            for day, meals in result['weekly_plan'].items():
                DailyMealPlan.objects.create(
                    recommendations_record=rec,
                    day_of_week=day,
                    breakfast_options=meals['breakfast'],
                    lunch_options=meals['lunch'],
                    dinner_options=meals['dinner']
                )

            return redirect('food_recommendation_system:view_plan', rec_id=rec.id)
        except Exception as e:
            return render(request, 'food_recommendation_system/input_form.html', {'error': str(e)})

    return render(request, 'food_recommendation_system/input_form.html')

@login_required
def view_plan(request, rec_id):
    if not is_member(request.user):
        return render(request, 'food_recommendation_system/membership_required.html')
        
    rec = get_object_or_404(FoodRecommendation, id=rec_id, user=request.user)
    plans = rec.meal_plans.all()
    
    day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    sorted_plans = sorted(plans, key=lambda x: day_order.index(x.day_of_week) if x.day_of_week in day_order else 99)
    
    return render(request, 'food_recommendation_system/view_plan.html', {'rec': rec, 'plans': sorted_plans})

