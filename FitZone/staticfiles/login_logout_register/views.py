from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile

def register(request):
    if request.method == "POST":
        name = request.POST.get('name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        dob = request.POST.get('dob')
        gender = request.POST.get('gender')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Check password match
        if password != confirm_password:
            messages.error(request, "Registration failed: Passwords do not match")
            return render(request, 'register.html')

        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Registration failed: Username already exists")
            return render(request, 'register.html')

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=name
            )

            # Create profile
            UserProfile.objects.create(
                user=user,
                phone=phone,
                dob=dob,
                gender=gender
            )
            messages.success(request, "Registration successful")
            return render(request, 'login.html')

        except Exception as e:
           
            print(e)  
            messages.error(request, "Registration failed: Please try again")
            return render(request, 'register.html')

    return render(request, 'register.html')
def user_login(request):

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect('/')  
        else:
            messages.error(request, "Invalid username or password")
            return redirect(request, 'login.html')
    return render(request, 'login.html')

