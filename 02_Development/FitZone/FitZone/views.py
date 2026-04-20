
from django.shortcuts import render, redirect
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Sum, Count
from django.db.models.functions import Coalesce
from datetime import datetime, date, time, timedelta
import calendar
import os
from trainer.booking_notifications import process_booking_expiry_notifications

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
    process_booking_expiry_notifications(user=request.user)

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
    process_booking_expiry_notifications(user=request.user)

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
    process_booking_expiry_notifications(user=request.user)

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


@staff_member_required
def admin_reports(request):
    from django.contrib.auth.models import User
    from membership.models import UserMembership
    from payment.models import KhaltiPayment, TrainerPaymentRequest
    from trainer.models import TrainerBooking, TrainerRegistration

    today = timezone.localdate()
    period = request.GET.get('period', 'monthly').strip().lower()
    selected_year = today.year
    selected_month = today.month
    custom_start = ''
    custom_end = ''

    if period == 'yearly':
        try:
            selected_year = int(request.GET.get('year', today.year))
        except (TypeError, ValueError):
            selected_year = today.year

        start_date = date(selected_year, 1, 1)
        end_date = date(selected_year, 12, 31)
        range_label = f"Yearly Report: {selected_year}"
    elif period == 'custom':
        custom_start = request.GET.get('start_date', '').strip()
        custom_end = request.GET.get('end_date', '').strip()

        try:
            start_date = date.fromisoformat(custom_start) if custom_start else (today - timedelta(days=29))
        except ValueError:
            start_date = today - timedelta(days=29)

        try:
            end_date = date.fromisoformat(custom_end) if custom_end else today
        except ValueError:
            end_date = today

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        range_label = f"Custom Report: {start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
    else:
        period = 'monthly'
        try:
            selected_year = int(request.GET.get('year', today.year))
        except (TypeError, ValueError):
            selected_year = today.year

        try:
            selected_month = int(request.GET.get('month', today.month))
        except (TypeError, ValueError):
            selected_month = today.month

        selected_month = max(1, min(selected_month, 12))
        start_date = date(selected_year, selected_month, 1)
        if selected_month == 12:
            end_date = date(selected_year, 12, 31)
        else:
            end_date = date(selected_year, selected_month + 1, 1) - timedelta(days=1)

        range_label = f"Monthly Report: {start_date.strftime('%B %Y')}"

    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max))

    completed_payments = KhaltiPayment.objects.filter(
        status='Completed',
        created_at__range=(start_dt, end_dt),
    )

    membership_payments = completed_payments.filter(payment_type='membership')
    booking_payments = completed_payments.filter(payment_type='booking')

    membership_revenue_paisa = membership_payments.aggregate(total=Coalesce(Sum('amount'), 0))['total']
    booking_revenue_paisa = booking_payments.aggregate(total=Coalesce(Sum('amount'), 0))['total']
    total_revenue_paisa = membership_revenue_paisa + booking_revenue_paisa

    booking_ids_from_payments = booking_payments.exclude(booking__isnull=True).values_list('booking_id', flat=True)
    bookings_created_in_range = TrainerBooking.objects.filter(created_at__range=(start_dt, end_dt))
    bookings_paid_in_range = TrainerBooking.objects.filter(id__in=booking_ids_from_payments)
    bookings_in_range = (bookings_created_in_range | bookings_paid_in_range).distinct()

    booking_status_map = {key: 0 for key, _ in TrainerBooking.STATUS_CHOICES}
    for row in bookings_in_range.values('status').annotate(total=Count('id')):
        booking_status_map[row['status']] = row['total']

    payout_requests_in_range = TrainerPaymentRequest.objects.filter(created_at__range=(start_dt, end_dt))
    payout_status_map = {key: 0 for key, _ in TrainerPaymentRequest.STATUS_CHOICES}
    for row in payout_requests_in_range.values('status').annotate(total=Count('id')):
        payout_status_map[row['status']] = row['total']

    payment_type_map = {key: 0 for key, _ in KhaltiPayment.PAYMENT_TYPE_CHOICES}
    for row in completed_payments.values('payment_type').annotate(total=Count('id')):
        payment_type_map[row['payment_type']] = row['total']

    available_years = KhaltiPayment.objects.filter(status='Completed').dates('created_at', 'year', order='ASC')
    if available_years:
        year_options = [dt.year for dt in available_years][::-1]
    else:
        year_options = list(range(today.year, today.year - 5, -1))

    month_options = [
        {'value': idx, 'label': month_name}
        for idx, month_name in enumerate(calendar.month_name)
        if idx > 0
    ]

    summary_cards = [
        {
            'label': 'Total Revenue',
            'value': round(total_revenue_paisa / 100, 2),
            'icon': 'fa-wallet',
            'tone': 'subs',
            'is_currency': True,
        },
        {
            'label': 'Membership Revenue',
            'value': round(membership_revenue_paisa / 100, 2),
            'icon': 'fa-id-card',
            'tone': 'users',
            'is_currency': True,
        },
        {
            'label': 'Booking Revenue',
            'value': round(booking_revenue_paisa / 100, 2),
            'icon': 'fa-dumbbell',
            'tone': 'tasks',
            'is_currency': True,
        },
        {
            'label': 'Completed Transactions',
            'value': completed_payments.count(),
            'icon': 'fa-check-circle',
            'tone': 'users',
            'is_currency': False,
        },
    ]

    membership_user_rows = [
        {'label': 'Memberships Sold', 'value': UserMembership.objects.filter(created_at__range=(start_dt, end_dt)).count()},
        {'label': 'Active Memberships', 'value': UserMembership.objects.filter(is_active=True).count()},
        {'label': 'New Users', 'value': User.objects.filter(date_joined__range=(start_dt, end_dt)).count()},
        {'label': 'New Trainers', 'value': TrainerRegistration.objects.filter(submitted_at__range=(start_dt, end_dt)).count()},
    ]

    booking_rows = [
        {'label': 'Total Bookings', 'value': bookings_in_range.count()},
    ] + [
        {'label': label, 'value': booking_status_map.get(key, 0)}
        for key, label in TrainerBooking.STATUS_CHOICES
    ]

    payout_rows = [
        {'label': label, 'value': payout_status_map.get(key, 0)}
        for key, label in TrainerPaymentRequest.STATUS_CHOICES
    ] + [
        {'label': label, 'value': payment_type_map.get(key, 0)}
        for key, label in KhaltiPayment.PAYMENT_TYPE_CHOICES
    ]

    report_context = {
        'period': period,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'start_date_value': custom_start or start_date.isoformat(),
        'end_date_value': custom_end or end_date.isoformat(),
        'range_label': range_label,
        'start_date': start_date,
        'end_date': end_date,
        'year_options': year_options,
        'month_options': month_options,
        'summary_cards': summary_cards,
        'membership_user_rows': membership_user_rows,
        'booking_rows': booking_rows,
        'payout_rows': payout_rows,
        'membership_revenue': round(membership_revenue_paisa / 100, 2),
        'booking_revenue': round(booking_revenue_paisa / 100, 2),
        'total_revenue': round(total_revenue_paisa / 100, 2),
        'membership_payments_count': membership_payments.count(),
        'booking_payments_count': booking_payments.count(),
        'completed_transactions_count': completed_payments.count(),
        'recent_payments': completed_payments.select_related('user', 'membership_plan', 'booking').order_by('-created_at')[:20],
    }

    context = admin.site.each_context(request)
    context.update(report_context)
    context['title'] = 'Project Reports'

    return render(request, 'admin/reports.html', context)
