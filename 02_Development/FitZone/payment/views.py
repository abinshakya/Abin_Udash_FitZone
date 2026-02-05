from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from membership.models import MembershipPlan
from django.contrib import messages
from login_logout_register.models import UserProfile

@login_required
def checkout(request, plan_id):
    try:
        profile = UserProfile.objects.get(user=request.user)
        
        if not profile.email_verified:
            messages.error(request, "Please verify your email address before purchasing a membership.")
            return redirect('verify_otp')
    except UserProfile.DoesNotExist:
        messages.error(request, "Profile not found. Please complete your registration.")
        return redirect('register')
    
    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    context = {
        'plan': plan,
        'user': request.user
    }
    return render(request, 'checkout.html', context)
