from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from notifications.models import UserNotification
from trainer.models import TrainerBooking


def process_booking_expiry_notifications(user=None):
    """Send expiry warning and completion/review emails for trainer bookings.

    If ``user`` is provided, process only that user's bookings. This function is
    safe to call repeatedly because it guards on boolean flags in the booking model.
    """
    now = timezone.now()
    three_days_later = now + timedelta(days=3)
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

    base_qs = TrainerBooking.objects.filter(
        payment_status='completed',
        valid_until__isnull=False,
    )

    if user is not None:
        base_qs = base_qs.filter(user=user)

    expiring_soon = base_qs.filter(
        status='confirmed',
        valid_until__lte=three_days_later,
        valid_until__gt=now,
        expiry_warning_sent=False,
    ).select_related('user', 'trainer__user')

    expired_bookings = base_qs.exclude(status__in=['cancelled', 'rejected']).filter(
        valid_until__lte=now,
        completion_email_sent=False,
    ).select_related('user', 'trainer__user')

    summary = {
        'expiring_processed': expiring_soon.count(),
        'expired_processed': expired_bookings.count(),
        'warning_sent': 0,
        'completion_sent': 0,
    }

    for booking in expiring_soon:
        booking_user = booking.user
        trainer_name = booking.trainer.user.get_full_name() or booking.trainer.user.username

        if not booking_user.email:
            continue

        subject = f"FitZone: Training with {trainer_name} expires soon!"
        message = (
            f"Hi {booking_user.first_name or booking_user.username},\n\n"
            f"This is a friendly reminder that your training sessions with {trainer_name} "
            f"will expire on {booking.valid_until.strftime('%b %d, %Y')}.\n\n"
            f"Don't let your progress stop! You can renew your booking from your dashboard.\n\n"
            f"Best regards,\nFitZone Team"
        )

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [booking_user.email],
                fail_silently=False,
            )
            booking.expiry_warning_sent = True
            booking.save(update_fields=['expiry_warning_sent'])
            summary['warning_sent'] += 1
        except Exception:
            continue

    for booking in expired_bookings:
        booking_user = booking.user
        trainer_name = booking.trainer.user.get_full_name() or booking.trainer.user.username
        review_link = f"{site_url}{reverse('user_review_trainer', args=[booking.id])}"

        if booking_user.email:
            subject = f"FitZone: Thank you for booking Trainer {trainer_name}!"
            message = (
                f"Hi {booking_user.first_name or booking_user.username},\n\n"
                f"Thank you for choosing {trainer_name} as your trainer on FitZone! We hope you had a productive and inspiring training journey.\n\n"
                f"We would love to hear about your experience. Please take a moment to rate and review your trainer here:\n"
                f"{review_link}\n\n"
                f"Your feedback helps our community and the trainer to grow.\n\n"
                f"Best regards,\nFitZone Team"
            )

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [booking_user.email],
                    fail_silently=False,
                )
            except Exception:
                continue

        UserNotification.objects.create(
            user=booking_user,
            booking=booking,
            notif_type='general',
            title='Rate Your Trainer!',
            message=f'Your training with {trainer_name} is complete. Please rate your experience!',
        )

        booking.status = 'completed'
        booking.completion_email_sent = True
        booking.save(update_fields=['status', 'completion_email_sent'])
        summary['completion_sent'] += 1

    return summary
