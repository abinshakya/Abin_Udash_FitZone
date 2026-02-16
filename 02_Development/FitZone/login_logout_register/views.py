from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import random
import string
import os

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

            # Create profile (do not pass username, only valid fields)
            UserProfile.objects.create(
                user=user,
                phone=phone,
                age=int(age) if age else None,
                dob=dob,
                gender=gender,
                email_verified=False  
            )
            messages.success(request, "Registration successful! Please login and verify your email.")
            return redirect('login')

        except Exception as e:
            print("Registration error:", e) 
            messages.error(request, f"Registration failed: {e}")
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
    list(messages.get_messages(request))
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
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            # Delete old profile picture file if it exists
            if profile.profile_picture:
                old_path = profile.profile_picture.path
                if os.path.isfile(old_path):
                    os.remove(old_path)
            profile.profile_picture = request.FILES['profile_picture']
        
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
        
        # Redirect back to edit profile page
        return redirect('edit_profile')
    
    context = {
        'user': request.user,
        'profile': profile
    }
    return render(request, 'edit_profile.html', context)

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(user_email, otp):
    subject = 'FitZone - Email Verification OTP'
    message = f"""
    Hello,
    
    Your OTP for email verification is: {otp}
    
    This OTP will expire in 10 minutes.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    FitZone Team
    """
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"============ EMAIL ERROR ============")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {str(e)}")
        print(f"From: {settings.EMAIL_HOST_USER}")
        print(f"To: {user_email}")
        print(f"SMTP Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        print(f"====================================")
        return False

@login_required
def send_verification_otp(request):
    return redirect('verify_otp')

@login_required
def verify_otp_view(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        
        if profile.email_verified:
            messages.info(request, "Your email is already verified!")
            return redirect('edit_profile')
        
        # Handle otp sending (when user clicks "Send OTP" button)
        if request.method == "POST" and 'send_otp' in request.POST:
            # Generate otp
            otp = generate_otp()
            
            # Save otp to profile
            profile.otp = otp
            profile.otp_created_at = timezone.now()
            profile.save()
            
            # Send otp email
            if send_otp_email(request.user.email, otp):
                # Check if using console backend
                if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                    messages.success(request, f"✅ OTP Generated: {otp} (Check your terminal/console for the full email)")
                else:
                    messages.success(request, f"OTP has been sent to {request.user.email}")
            else:
                messages.error(request, "Failed to send OTP. Check terminal for details.")
            
            return render(request, 'verify_otp.html', {'otp_sent': True})
        
        # Handle otp verification (when user submits otp)
        if request.method == "POST" and 'verify_otp' in request.POST:
            entered_otp = request.POST.get('otp')
            
            if not profile.otp or not profile.otp_created_at:
                messages.error(request, "No OTP found. Please request a new one.")
                return render(request, 'verify_otp.html')
            
            # Check if otp is expired (10 minutes)
            time_diff = timezone.now() - profile.otp_created_at
            if time_diff.total_seconds() > 600:  # 10 minutes
                messages.error(request, "OTP has expired. Please request a new one.")
                profile.otp = None
                profile.otp_created_at = None
                profile.save()
                return render(request, 'verify_otp.html')
            
            # Verify OTP
            if entered_otp == profile.otp:
                profile.email_verified = True
                profile.otp = None
                profile.otp_created_at = None
                profile.save()
                messages.success(request, "Email verified successfully!")
                return redirect('edit_profile')
            else:
                messages.error(request, "Invalid OTP. Please try again.")
                return render(request, 'verify_otp.html', {'otp_sent': True})
        
        # Check if OTP was already sent (to show the input field)
        otp_sent = profile.otp is not None and profile.otp_created_at is not None
        if otp_sent:
            # Check if OTP expired
            time_diff = timezone.now() - profile.otp_created_at
            if time_diff.total_seconds() > 600:
                otp_sent = False
                profile.otp = None
                profile.otp_created_at = None
                profile.save()
        
        return render(request, 'verify_otp.html', {'otp_sent': otp_sent})
        
    except UserProfile.DoesNotExist:
        messages.error(request, "Profile not found!")
        return redirect('/')