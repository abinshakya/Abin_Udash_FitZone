from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from membership.models import MembershipPlan

def membership_page(request):
    plans = MembershipPlan.objects.all()   
    return render(request, "membership.html", {"plans": plans})


