from django.core.management.base import BaseCommand
from django.utils import timezone
from trainer.booking_notifications import process_booking_expiry_notifications

class Command(BaseCommand):
    help = 'Checks for expiring or expired trainer bookings and sends notification emails.'

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"Checking bookings at {now}...")

        summary = process_booking_expiry_notifications()

        self.stdout.write(f"Found {summary['expiring_processed']} bookings expiring soon.")
        self.stdout.write(f"Found {summary['expired_processed']} expired bookings.")
        self.stdout.write(self.style.SUCCESS(f"Sent {summary['warning_sent']} expiry warning email(s)."))
        self.stdout.write(self.style.SUCCESS(f"Sent {summary['completion_sent']} completion email(s)."))
