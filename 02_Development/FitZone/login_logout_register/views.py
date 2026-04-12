from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from formtools.wizard.views import SessionWizardView
from django import forms
from django.core.files.storage import default_storage
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
# Multi-step forgot password flow: email → OTP → reset password
def forgot_password(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        email = request.POST.get('email', '').strip()
        
        # Send OTP 
        if action == 'send_otp':
            if not email:
                messages.error(request, "Please enter your email address.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            try:
                user = User.objects.get(email=email)
                profile = UserProfile.objects.get(user=user)
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                messages.error(request, "No account found with that email address.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            # Generate and save OTP
            otp = generate_otp()
            profile.otp = otp
            profile.otp_created_at = timezone.now()
            profile.save()
            
            # Send OTP email
            subject = 'FitZone - Password Reset OTP'
            message = f"""
Hello {user.first_name or user.username},

Your OTP for password reset is: {otp}

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
                    [email],
                    fail_silently=False,
                )
                if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                    messages.success(request, f"✅ OTP Generated: {otp} (Check your terminal/console)")
                else:
                    messages.success(request, f"OTP has been sent to {email}")
            except Exception as e:
                print(f"Forgot password email error: {e}")
                messages.error(request, "Failed to send OTP. Please try again.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            return render(request, 'forgot_password.html', {
                'step': 'verify_otp',
                'email': email,
            })
        
        # OTP verification
        elif action == 'verify_otp':
            entered_otp = request.POST.get('otp', '').strip()
            
            if not email:
                messages.error(request, "Session expired. Please start over.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            try:
                user = User.objects.get(email=email)
                profile = UserProfile.objects.get(user=user)
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                messages.error(request, "Account not found. Please start over.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            # Check OTP exists
            if not profile.otp or not profile.otp_created_at:
                messages.error(request, "No OTP found. Please request a new one.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            # Check if OTP expired (10 minutes)
            time_diff = timezone.now() - profile.otp_created_at
            if time_diff.total_seconds() > 600:
                profile.otp = None
                profile.otp_created_at = None
                profile.save()
                messages.error(request, "OTP has expired. Please request a new one.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            # Verify OTP
            if entered_otp == profile.otp:
                # Clear OTP after successful verification
                profile.otp = None
                profile.otp_created_at = None
                profile.save()
                
                # Store verified state in session
                request.session['forgot_pw_verified_email'] = email
                
                return render(request, 'forgot_password.html', {
                    'step': 'reset_password',
                    'email': email,
                    'found_username': user.username,
                })
            else:
                messages.error(request, "Invalid OTP. Please try again.")
                return render(request, 'forgot_password.html', {
                    'step': 'verify_otp',
                    'email': email,
                })
        
        # Reset Password 
        elif action == 'reset_password':
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            # Verify session
            verified_email = request.session.get('forgot_pw_verified_email')
            if not verified_email or verified_email != email:
                messages.error(request, "Unauthorized. Please start the process again.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "Account not found.")
                return render(request, 'forgot_password.html', {'step': 'email'})
            
            errors = {}
            if len(new_password) < 8:
                errors['new_password'] = "Password must be at least 8 characters long."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."
            
            if errors:
                return render(request, 'forgot_password.html', {
                    'step': 'reset_password',
                    'email': email,
                    'found_username': user.username,
                    'errors': errors,
                })
            
            # Reset password
            user.set_password(new_password)
            user.save()
            
            # Clean up session
            del request.session['forgot_pw_verified_email']
            
            messages.success(request, "Your password has been reset successfully!")
            return render(request, 'forgot_password.html', {
                'step': 'success',
                'found_username': user.username,
            })
    
    # GET request - show email form
    return render(request, 'forgot_password.html', {'step': 'email'})

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

@login_required
def change_password(request):
    context = {'profile': UserProfile.objects.filter(user=request.user).first()}
    
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        errors = {}

        # Validations
        if not request.user.check_password(old_password):
            errors['old_password'] = "The current password you entered does not match."
            
        if len(new_password) < 8:
            errors['new_password'] = "Password must be at least 8 characters long."

        if new_password != confirm_password:
            errors['confirm_password'] = "New passwords do not match."

        # If errors exist, render template with specific error messages
        if errors:
            context['errors'] = errors
            return render(request, 'change_password.html', context)

        # Success - Change Password
        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)  # Keep the user logged in
        context['password_changed'] = True
        return render(request, 'change_password.html', context)
        
    return render(request, 'change_password.html', context)


class GoogleAccountForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(pk=self.initial.get('user_id')).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.initial.setdefault('user_id', user.pk)

    def clean_password(self):
        password = self.cleaned_data['password']
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return password


class GoogleProfileForm(forms.Form):
    age = forms.IntegerField(required=True, min_value=1)
    phone = forms.CharField(max_length=20, required=True)
    gender = forms.ChoiceField(
        required=True,
        choices=(
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ),
    )
    profile_picture = forms.ImageField(required=False)


GOOGLE_PROFILE_FORMS = [
    ('account', GoogleAccountForm),
    ('profile', GoogleProfileForm),
]


class GoogleProfileWizard(SessionWizardView):
    template_name = 'google_profile_wizard.html'
    file_storage = default_storage

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == 'account':
            kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)
        user = self.request.user
        profile = UserProfile.objects.filter(user=user).first()
        if step == 'account':
            initial.update({
                'username': user.username,
            })
        elif step == 'profile' and profile is not None:
            if profile.age is not None:
                initial['age'] = profile.age
            if profile.phone:
                initial['phone'] = profile.phone
            if profile.gender:
                initial['gender'] = profile.gender
        return initial

    def done(self, form_list, **kwargs):
        user = self.request.user
        profile = UserProfile.objects.filter(user=user).first()
        cleaned = {}
        for form in form_list:
            cleaned.update(form.cleaned_data)

        username = cleaned.get('username') or user.username
        password = cleaned.get('password')

        if username and username != user.username:
            user.username = username
        if password:
            user.set_password(password)
        user.save()

        if profile is not None:
            if cleaned.get('age') is not None:
                profile.age = cleaned.get('age')
            if cleaned.get('phone'):
                profile.phone = cleaned.get('phone')
            if cleaned.get('gender'):
                profile.gender = cleaned.get('gender')
            if cleaned.get('profile_picture'):
                profile.profile_picture = cleaned.get('profile_picture')
            profile.email_verified = True
            if not profile.role:
                profile.role = 'member'
            profile.save()

        # Keep the user logged in if password changed
        update_session_auth_hash(self.request, user)

        # After completing profile, send to member dashboard
        return redirect('user_dashboard')


def google_profile_wizard_entry(request):
    if not request.user.is_authenticated:
        return redirect('login')

    # If profile already appears complete, skip the wizard
    profile = UserProfile.objects.filter(user=request.user).first()
    if profile and profile.phone and profile.age and profile.gender:
        # Redirect based on role similar to user_login
        if profile.role == 'trainer':
            return redirect('trainer_dashboard')
        elif profile.role == 'member':
            return redirect('user_dashboard')
        elif profile.role == 'admin':
            return redirect('/admin/')
        return redirect('home')

    view = GoogleProfileWizard.as_view(GOOGLE_PROFILE_FORMS)
    return view(request)