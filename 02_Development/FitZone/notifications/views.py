from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import TrainerNotification, UserNotification


@login_required
def mark_trainer_notification_read(request, notif_id):
    """Mark a single trainer notification as read."""
    from trainer.models import TrainerRegistration
    
    notif = get_object_or_404(TrainerNotification, id=notif_id)
    if notif.trainer.user != request.user:
        messages.error(request, "Access denied.")
        return redirect('trainer_dashboard')
    notif.is_read = True
    notif.save()
    return redirect('trainer_dashboard')


@login_required
def mark_all_trainer_notifications_read(request):
    """Mark all notifications as read for current trainer."""
    from trainer.models import TrainerRegistration
    
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    if registration:
        registration.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect('trainer_dashboard')


@login_required
def mark_user_notification_read(request, notif_id):
    """Mark a single user notification as read."""
    notif = get_object_or_404(UserNotification, id=notif_id)
    if notif.user != request.user:
        messages.error(request, "Access denied.")
        return redirect('trainer_client_dashboard')
    notif.is_read = True
    notif.save()
    return redirect('trainer_client_dashboard')


@login_required
def mark_all_user_notifications_read(request):
    """Mark all user notifications as read."""
    UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('trainer_client_dashboard')
