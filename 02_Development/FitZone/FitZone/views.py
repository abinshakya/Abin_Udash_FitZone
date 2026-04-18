
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from datetime import datetime, date
import os

def cancel_overdue_bookings(user):
    from notifications.models import UserNotification, TrainerNotification
    from trainer.models import TrainerBooking

    overdue = TrainerBooking.objects.filter(
        user=user,
        status='confirmed',
        payment_status='pending',
        payment_due_date__lt=timezone.now(),
    ).select_related('trainer__user')

    for booking in overdue:
        booking.status = 'cancelled'
        booking.payment_status = 'overdue'
        booking.cancelled_by = 'system'
        booking.cancellation_reason = 'Payment not completed within the due date.'
        booking.save()
        trainer_name = booking.trainer.user.get_full_name() or booking.trainer.user.username
        user_name = user.get_full_name() or user.username
        booking_date_str = booking.booking_date.strftime("%b %d, %Y")

        # Notify user
        UserNotification.objects.create(
            user=user,
            booking=booking,
            notif_type='general',
            title='Booking Cancelled - Payment Overdue',
            message=f'Your booking with {trainer_name} for {booking_date_str} was cancelled because payment was not completed within 2 days.',
        )

        # Notify trainer
        TrainerNotification.objects.create(
            trainer=booking.trainer,
            booking=booking,
            notif_type='cancellation',
            title='Booking Cancelled - Payment Overdue',
            message=f'{user_name}\'s booking for {booking_date_str} was automatically cancelled due to non-payment.',
        )

        # Email to user
        try:
            send_mail(
                subject='FitZone: Booking Cancelled - Payment Overdue',
                message=(
                    f'Hi {user_name},\n\n'
                    f'Your booking with {trainer_name} for {booking_date_str} has been automatically cancelled '
                    f'because payment was not completed within the due date.\n\n'
                    f'If you\'d like to continue training, please book again and complete payment on time.\n\n'
                    f'Best regards,\nFitZone Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        # Email to trainer
        try:
            send_mail(
                subject=f'FitZone: Booking Cancelled - {user_name} Payment Overdue',
                message=(
                    f'Hi {trainer_name},\n\n'
                    f'{user_name}\'s booking with you for {booking_date_str} has been automatically cancelled '
                    f'because the payment was not completed within 2 days.\n\n'
                    f'No action is required on your end.\n\n'
                    f'Best regards,\nFitZone Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.trainer.user.email],
                fail_silently=True,
            )
        except Exception:
            pass

@cache_control(public=True, max_age=3600)
def home(request):
    from .models import HomeBanner, PremiumService
    from trainer.models import TrainerReview

    banners = HomeBanner.objects.filter(is_active=True)
    services = PremiumService.objects.filter(is_active=True)

    goal_label_map = {
        'weight_loss': 'Weight Loss',
        'muscle_gain': 'Muscle Gain',
        'maintain': 'Maintain Fitness',
        'endurance': 'Improve Endurance',
        'flexibility': 'Improve Flexibility',
        'general': 'General Fitness',
    }

    testimonials = []
    real_reviews = TrainerReview.objects.filter(show_on_homepage=True).select_related('user').order_by('-created_at')[:6]
    for review in real_reviews:
        goal_key = getattr(getattr(review.user, 'fitness_profile', None), 'fitness_goal', 'general')
        testimonials.append({
            'name': review.user.get_full_name() or review.user.username,
            'goal': goal_label_map.get(goal_key, 'Consistency'),
            'quote': review.comment or 'Great coaching and steady progress every week.',
            'rating': review.rating,
            'stars': '★' * int(review.rating),
            'is_beta': False,
        })

    return render(request, 'index.html', {
        'banners': banners,
        'services': services,
        'testimonials': testimonials,
    })

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
    
    # Get active membership
    from membership.models import UserMembership
    membership = UserMembership.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('membership_plan').first()
    
    # Check if user has an active membership plan
    if not membership:
        messages.warning(request, "You don't have an active membership plan. Please purchase a membership to access the dashboard.")
        return redirect('/membership/')

    # Get user notifications
    from notifications.models import UserNotification
    from trainer.models import TrainerBooking
    notifications = UserNotification.objects.filter(user=request.user)[:20]
    unread_count = UserNotification.objects.filter(user=request.user, is_read=False).count()
    bookings = TrainerBooking.objects.filter(user=request.user).select_related('trainer__user').order_by('-created_at')[:20]
    
    # Auto-cancel overdue bookings (unpaid for 2+ days)
    cancel_overdue_bookings(request.user)

    # Get bookings requiring payment
    confirmed_bookings = TrainerBooking.objects.filter(
        user=request.user, 
        status='confirmed',
        payment_status='pending'
    ).select_related('trainer__user').order_by('payment_due_date')

    context = {
        'membership': membership,
        'notifications': notifications,
        'unread_count': unread_count,
        'bookings': bookings,
        'confirmed_bookings': confirmed_bookings,
    }
    
    return render(request, 'member/user_dashboard.html', context)


@login_required
def member_settings(request):
    """Member settings page inside the member panel (profile & security)."""

    # Ensure user is a member with an active membership (same rules as dashboard)
    try:
        profile_obj = request.user.userprofile
        if profile_obj.role != 'member':
            messages.warning(request, "You need to be a member to access settings. Please join our membership!")
            return redirect('/membership/')
    except Exception:
        messages.warning(request, "You need to be a member to access settings. Please join our membership!")
        return redirect('/membership/')

    from membership.models import UserMembership
    membership = UserMembership.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('membership_plan').first()

    if not membership:
        messages.warning(request, "You don't have an active membership plan. Please purchase a membership to access settings.")
        return redirect('/membership/')

    # Notifications for header bell
    from notifications.models import UserNotification
    notifications = UserNotification.objects.filter(user=request.user)[:20]
    unread_count = UserNotification.objects.filter(user=request.user, is_read=False).count()

    # Load or create profile
    from login_logout_register.models import UserProfile
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        # Basic user info
        request.user.first_name = request.POST.get('name', request.user.first_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            if profile.profile_picture:
                old_path = profile.profile_picture.path
                if os.path.isfile(old_path):
                    os.remove(old_path)
            profile.profile_picture = request.FILES['profile_picture']

        # Other profile fields
        profile.phone = request.POST.get('phone', profile.phone)
        profile.gender = request.POST.get('gender', profile.gender)
        age_val = request.POST.get('age')
        if age_val:
            try:
                age_int = int(age_val)
                profile.age = age_int
                current_year = datetime.now().year
                birth_year = current_year - age_int
                profile.dob = date(birth_year, 1, 1)
            except ValueError:
                pass

        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('member_settings')

    context = {
        'membership': membership,
        'notifications': notifications,
        'unread_count': unread_count,
        'profile': profile,
    }

    return render(request, 'member/settings.html', context)

# Dashboard for users who have booked trainers
@login_required
def trainer_client_dashboard(request):
    from notifications.models import UserNotification
    from trainer.models import TrainerBooking
    
    # Get all bookings for this user
    all_bookings = TrainerBooking.objects.filter(user=request.user).select_related('trainer__user').order_by('-created_at')
    
    # Check if user has any bookings
    if not all_bookings.exists():
        messages.info(request, "You haven't booked any trainers yet. Browse our trainers to get started!")
        return redirect('trainer')
    
    # Auto-cancel overdue bookings (unpaid for 2+ days)
    cancel_overdue_bookings(request.user)

    # Get bookings requiring payment
    confirmed_bookings = TrainerBooking.objects.filter(
        user=request.user, 
        status='confirmed',
        payment_status='pending'
    ).select_related('trainer__user').order_by('payment_due_date')
    
    # Get active trainers (confirmed, paid, and still within validity)
    now = timezone.now()
    active_trainers_qs = TrainerBooking.objects.filter(
        user=request.user,
        status='confirmed',
        payment_status='completed'
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now)).select_related('trainer__user').prefetch_related('trainer__documents').order_by('-valid_until')

    # Group by trainer to avoid duplicates on dashboard
    active_trainers = []
    seen_trainers = {} # trainer_id -> booking object
    
    # First pass: find the latest booking and earliest start for each trainer
    for booking in active_trainers_qs:
        if booking.trainer_id not in seen_trainers:
            booking.earliest_start = booking.booking_date
            seen_trainers[booking.trainer_id] = booking
            active_trainers.append(booking)
        else:
            # Update the representative booking's earliest start if this one is earlier
            if booking.booking_date < seen_trainers[booking.trainer_id].earliest_start:
                seen_trainers[booking.trainer_id].earliest_start = booking.booking_date

    # Get notifications
    notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:20]
    unread_count = UserNotification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'all_bookings': all_bookings,
        'confirmed_bookings': confirmed_bookings,
        'active_trainers': active_trainers,
        'notifications': notifications,
        'unread_count': unread_count,
        'today': now,
    }
    
    return render(request, 'trainer_client/dashboard.html', context)


@login_required
def trainer_client_my_trainers(request):
    from trainer.models import TrainerBooking

    bookings = TrainerBooking.objects.filter(user=request.user).select_related('trainer__user').order_by('-created_at')

    if not bookings.exists():
        messages.info(request, "You haven't booked any trainers yet. Browse our trainers to get started!")
        return redirect('trainer')

    now = timezone.now()

    running_trainers_qs = bookings.filter(
        status='confirmed',
        payment_status='completed'
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now)).order_by('-valid_until')

    running_trainers = []
    seen_running = {}
    for b in running_trainers_qs:
        if b.trainer_id not in seen_running:
            b.earliest_start = b.booking_date
            seen_running[b.trainer_id] = b
            running_trainers.append(b)
        else:
            if b.booking_date < seen_running[b.trainer_id].earliest_start:
                seen_running[b.trainer_id].earliest_start = b.booking_date

    pending_trainers = bookings.filter(
        Q(status='pending') | Q(status='confirmed', payment_status='pending')
    )

    completed_trainers = bookings.filter(
        status='confirmed',
        payment_status='completed',
        valid_until__lt=now
    )

    context = {
        'running_trainers': running_trainers,
        'pending_trainers': pending_trainers,
        'completed_trainers': completed_trainers,
    }

    return render(request, 'trainer_client/my_trainers.html', context)

@cache_control(public=True, max_age=3600)
def about(request):
    return render(request, 'about.html')


def contact_us(request):
    from .models import ContactUsSubmission

    if request.method != 'POST':
        return redirect('home')

    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    subject = request.POST.get('subject', '').strip()
    message_body = request.POST.get('message', '').strip()

    if not name or not email or not subject or not message_body:
        messages.error(request, 'Please fill out all contact form fields.')
        return redirect('home')

    ContactUsSubmission.objects.create(
        name=name,
        email=email,
        subject=subject,
        message=message_body,
    )

    full_subject = f"Landing Contact: {subject}"
    full_message = (
        f"Name: {name}\n"
        f"Email: {email}\n\n"
        f"Message:\n{message_body}"
    )

    recipient_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER

    try:
        send_mail(
            subject=full_subject,
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        messages.success(request, 'Thank you for contacting us. We will get back to you soon!')
    except Exception:
        messages.error(request, 'Unable to send your message right now. Please try again later.')

    return redirect('home')

@login_required
def ai_chat(request):
    return render(request, 'member/ai_chat.html')

def handler404(request, exception=None):
    """
    Custom 404 Page Not Found handler.
    
    This view is triggered when a requested page does not exist.
    Returns a friendly error page with navigation options.
    
    Args:
        request: The HTTP request object
        exception: The exception that was raised (optional)
    
    Returns:
        HttpResponse: Rendered 404.html template
    """
    return render(request, '404.html', status=404)


def handler500(request):
    """
    Custom 500 Internal Server Error handler.
    
    This view is triggered when an unhandled exception occurs on the server.
    Returns a friendly error page informing users about the issue.
    
    Note: Django only shows this page when DEBUG = False in production.
    In development (DEBUG = True), the full error traceback is displayed.
    
    Args:
        request: The HTTP request object
    
    Returns:
        HttpResponse: Rendered 500.html template
    """
    return render(request, '500.html', status=500)


def handler403(request, exception=None):
    """
    Custom 403 Forbidden handler.
    
    This view is triggered when a user tries to access a resource they don't have permission for.
    Returns a friendly error page explaining access restrictions.
    
    Args:
        request: The HTTP request object
        exception: The exception that was raised (optional)
    
    Returns:
        HttpResponse: Rendered 403.html template
    """
    return render(request, '403.html', status=403)
