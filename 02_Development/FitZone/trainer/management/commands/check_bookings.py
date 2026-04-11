from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from trainer.models import TrainerBooking
from notifications.models import UserNotification

class Command(BaseCommand):
    help = 'Checks for expiring or expired trainer bookings and sends notification emails.'

    def handle(self, *args, **options):
        now = timezone.now()
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

        self.stdout.write(f"Checking bookings at {now}...")

        # 1. Check for bookings expiring in 3 days
        three_days_later = now + timedelta(days=3)
        expiring_soon = TrainerBooking.objects.filter(
            status='confirmed',
            payment_status='completed',
            valid_until__lte=three_days_later,
            valid_until__gt=now,
            expiry_warning_sent=False
        )

        self.stdout.write(f"Found {expiring_soon.count()} bookings expiring soon.")

        for booking in expiring_soon:
            user = booking.user
            trainer_reg = booking.trainer
            trainer_name = trainer_reg.user.get_full_name() or trainer_reg.user.username
            
            subject = f"FitZone: Training with {trainer_name} expires soon!"
            message = (
                f"Hi {user.first_name or user.username},\n\n"
                f"This is a friendly reminder that your training sessions with {trainer_name} will expire on {booking.valid_until.strftime('%b %d, %Y')}.\n\n"
                f"Don't let your progress stop! You can renew your booking from your dashboard.\n\n"
                f"Best regards,\nFitZone Team"
            )
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                booking.expiry_warning_sent = True
                booking.save(update_fields=['expiry_warning_sent'])
                self.stdout.write(self.style.SUCCESS(f"Sent expiry warning to {user.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send expiry warning to {user.email}: {e}"))

        # 2. Check for expired bookings
        expired_bookings = TrainerBooking.objects.filter(
            status='confirmed',
            payment_status='completed',
            valid_until__lte=now,
            completion_email_sent=False
        )

        self.stdout.write(f"Found {expired_bookings.count()} expired bookings.")

        for booking in expired_bookings:
            user = booking.user
            trainer_reg = booking.trainer
            trainer_name = trainer_reg.user.get_full_name() or trainer_reg.user.username
            
            # Update status to completed
            booking.status = 'completed'
            
            review_link = f"{site_url}{reverse('user_review_trainer', args=[booking.id])}"
            
            subject = f"FitZone: Thank you for booking Trainer {trainer_name}!"
            message = (
                f"Hi {user.first_name or user.username},\n\n"
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
                    [user.email],
                    fail_silently=False,
                )
                
                # Also create a notification
                UserNotification.objects.create(
                    user=user,
                    booking=booking,
                    notif_type='general',
                    title='Rate Your Trainer!',
                    message=f'Your training with {trainer_name} is complete. Please rate your experience!'
                )
                
                booking.completion_email_sent = True
                booking.save(update_fields=['status', 'completion_email_sent'])
                self.stdout.write(self.style.SUCCESS(f"Sent completion email to {user.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send completion email to {user.email}: {e}"))
