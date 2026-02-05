from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from membership.models import MembershipPlan
from django.contrib import messages
from login_logout_register.models import UserProfile

def membership_page(request):
    plans = MembershipPlan.objects.all()
    
    email_verified = False
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            email_verified = profile.email_verified
        except UserProfile.DoesNotExist:
            pass
    
    return render(request, "membership.html", {
        "plans": plans,
        "email_verified": email_verified
    })


