from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from membership.models import MembershipPlan

@login_required
def checkout(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    context = {
        'plan': plan,
        'user': request.user
    }
    return render(request, 'checkout.html', context)
