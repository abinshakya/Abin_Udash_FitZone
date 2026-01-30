
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def home(request):
    return render(request,'index.html')

@login_required
def user_dashboard(request):
    # Check if user is a member
    try:
        profile = request.user.userprofile
        if profile.role != 'member':
            messages.warning(request, "You need to be a member to access the dashboard. Please join our membership!")
            return redirect('/membership/')
    except:
        messages.warning(request, "You need to be a member to access the dashboard. Please join our membership!")
        return redirect('/membership/')
    
    return render(request, 'member/user_dashboard.html')

def trainer(request):
    return render(request,'trainer/trainer.html')

@login_required
def trainer_dashboard(request):
    # Check if user is a trainer
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')
    
    return render(request, 'trainer/trainer_dashboard.html')
