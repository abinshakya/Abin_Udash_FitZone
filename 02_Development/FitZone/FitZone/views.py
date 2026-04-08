
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q


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


def home(request):
    from .models import HomeBanner, PremiumService
    banners = HomeBanner.objects.filter(is_active=True)
    services = PremiumService.objects.filter(is_active=True)
    return render(request, 'index.html', {
        'banners': banners,
        'services': services
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
    today = timezone.now().date()
    active_trainers = TrainerBooking.objects.filter(
        user=request.user,
        status='confirmed',
        payment_status='completed'
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).select_related('trainer__user').prefetch_related('trainer__documents').order_by('-updated_at')

    # Get notifications
    notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:20]
    unread_count = UserNotification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'all_bookings': all_bookings,
        'confirmed_bookings': confirmed_bookings,
        'active_trainers': active_trainers,
        'notifications': notifications,
        'unread_count': unread_count,
        'today': today,
    }
    
    return render(request, 'trainer_client/dashboard.html', context)

def about(request):
    return render(request, 'about.html')

@login_required
def ai_chat(request):
    return render(request, 'member/ai_chat.html')
