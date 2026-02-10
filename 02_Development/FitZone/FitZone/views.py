
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
def trainer_client_dashboard(request):
    """Dashboard for users who have booked trainers"""
    from notifications.models import UserNotification
    from trainer.models import TrainerBooking
    
    # Get all bookings for this user
    all_bookings = TrainerBooking.objects.filter(user=request.user).select_related('trainer__user').order_by('-created_at')
    
    # Check if user has any bookings
    if not all_bookings.exists():
        messages.info(request, "You haven't booked any trainers yet. Browse our trainers to get started!")
        return redirect('trainer')
    
    # Get bookings requiring payment
    confirmed_bookings = TrainerBooking.objects.filter(
        user=request.user, 
        status='confirmed',
        payment_status='pending'
    ).select_related('trainer__user').order_by('payment_due_date')
    
    # Get active trainers (confirmed and paid)
    active_trainers = TrainerBooking.objects.filter(
        user=request.user,
        status='confirmed',
        payment_status='completed'
    ).select_related('trainer__user').order_by('-updated_at')
    
    # Get notifications
    notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:20]
    unread_count = UserNotification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'all_bookings': all_bookings,
        'confirmed_bookings': confirmed_bookings,
        'active_trainers': active_trainers,
        'notifications': notifications,
        'unread_count': unread_count,
    }
    
    return render(request, 'trainer_client/dashboard.html', context)