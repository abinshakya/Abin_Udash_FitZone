from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from membership.models import MembershipPlan, UserMembership
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


@login_required
def my_plans_page(request):
    try:
        profile = request.user.userprofile
        if profile.role != 'member':
            messages.warning(request, "Membership required to access this page.")
            return redirect('/membership/')
    except UserProfile.DoesNotExist:
        messages.warning(request, "Membership required to access this page.")
        return redirect('/membership/')

    membership = UserMembership.objects.filter(
        user=request.user
    ).select_related('membership_plan').order_by('-created_at').first()

    plan = membership.membership_plan if membership else None

    return render(request, "member/my_plans.html", {
        "membership": membership,
        "plan": plan,
    })


