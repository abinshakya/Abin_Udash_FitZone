from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from datetime import datetime

def register(request):
    if request.method == "POST":
        name = request.POST.get('name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')


        # Validate required fields
        if not phone or not phone.strip():
            messages.error(request, "Registration failed: Phone number is required")
            return render(request, 'register.html')

        # Validate password length
        if len(password) < 8:
            messages.error(request, "Registration failed: Password must be at least 8 characters long")
            return render(request, 'register.html')

        # Check password match
        if password != confirm_password:
            messages.error(request, "Registration failed: Passwords do not match")
            return render(request, 'register.html')

        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Registration failed: Username already exists")
            return render(request, 'register.html')
        
        # Check if email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Registration failed: Email already exists")
            return render(request, 'register.html')

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=name
            )

            # Calculate DOB from age
            dob = None
            if age:
                current_year = datetime.now().year
                birth_year = current_year - int(age)
                dob = datetime(birth_year, 1, 1).date()

            # Create profile
            UserProfile.objects.create(
                user=user,
                username=username,
                phone=phone,
                age=int(age) if age else None,
                dob=dob,
                gender=gender,
                
            )
            messages.success(request, "Registration successful! Please login.")
            return redirect('login')

        except Exception as e:
            print(e)  
            messages.error(request, "Registration failed: Please try again")
            return render(request, 'register.html')

    return render(request, 'register.html')

def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Regular user authentication
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            
            # Get user profile and redirect based on role
            try:
                profile = UserProfile.objects.get(user=user)
                
                if profile.role == 'member':
                    messages.success(request, f"Welcome back, {user.first_name}!")
                    return redirect('user_dashboard')  # User Dashboard
                elif profile.role == 'trainer':
                    messages.success(request, f"Welcome back, Trainer {user.first_name}!")
                    return redirect('trainer_dashboard')  # Trainer Dashboard
                elif profile.role == 'admin':
                    messages.success(request, f"Welcome back, Admin!")
                    return redirect('/admin/')  # Admin Dashboard
                else:  # Default user role
                    messages.success(request, f"Welcome, {user.first_name}!")
                    return redirect('/')  # Homepage
                    
            except UserProfile.DoesNotExist:
                # If no profile exists, redirect to homepage
                messages.success(request, f"Welcome, {user.first_name}!")
                return redirect('/')
        else:
            messages.error(request, "Invalid username or password")
            return render(request, 'login.html') 
            
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect('login')

@login_required
def edit_profile(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == "POST":
        # Update user information
        request.user.first_name = request.POST.get('name', request.user.first_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        
        # Update profile information
        profile.phone = request.POST.get('phone', profile.phone)
        profile.gender = request.POST.get('gender', profile.gender)
        age = request.POST.get('age')
        
        if age:
            profile.age = int(age)
            # Update DOB based on age
            current_year = datetime.now().year
            birth_year = current_year - int(age)
            profile.dob = datetime(birth_year, 1, 1).date()
        
        profile.save()
        messages.success(request, "Profile updated successfully!")
        
        # Redirect based on role
        if profile.role == 'member':
            return redirect('userdashboard')
        elif profile.role == 'trainer':
            return redirect('trainer_dashboard')
        elif profile.role == 'admin':
            return redirect('/admin/')
        else:
            return redirect('/')
    
    context = {
        'user': request.user,
        'profile': profile
    }
    return render(request, 'edit_profile.html', context)