from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from membership.models import UserMembership
from login_logout_register.models import UserProfile
from notifications.models import UserNotification


class Command(BaseCommand):
    help = 'Send a 2-day expiry warning and expire memberships that have passed their end date'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        warning_cutoff = now + timedelta(days=2)

        warning_memberships = UserMembership.objects.filter(
            is_active=True,
            expiry_warning_sent=False,
            end_date__gt=now,
            end_date__lte=warning_cutoff,
        ).select_related('user', 'membership_plan')

        for membership in warning_memberships:
            UserNotification.objects.create(
                user=membership.user,
                notif_type='general',
                title='Membership Expiry Reminder',
                message=(
                    f'Your {membership.membership_plan.name} membership will expire on '
                    f'{membership.end_date.strftime("%b %d, %Y")}. Please renew to keep access active.'
                ),
            )

            if membership.user.email:
                subject = f'FitZone membership expires in 2 days: {membership.membership_plan.name}'
                message = (
                    f'Hi {membership.user.first_name or membership.user.username},\n\n'
                    f'Your FitZone membership for {membership.membership_plan.name} will expire on '
                    f'{membership.end_date.strftime("%b %d, %Y")}.\n\n'
                    'Please renew your membership before it expires to keep your access active.\n\n'
                    'Best regards,\nFitZone Team'
                )

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [membership.user.email],
                        fail_silently=False,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Sent 2-day expiry warning email to {membership.user.username} for {membership.membership_plan.name}'
                        )
                    )
                except Exception:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Failed expiry warning email for {membership.user.username}'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipped expiry warning email for {membership.user.username} because no email address is set'
                    )
                )

            membership.expiry_warning_sent = True
            membership.save(update_fields=['expiry_warning_sent'])
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created 2-day expiry notification for {membership.user.username}'
                )
            )

        # Find all active memberships that have expired
        expired_memberships = UserMembership.objects.filter(
            is_active=True,
            end_date__lt=now
        ).select_related('user', 'membership_plan')
        
        count = 0
        for membership in expired_memberships:
            # Mark membership as inactive
            membership.is_active = False
            membership.save()
            
            # Check if user has any other active memberships
            other_active = UserMembership.objects.filter(
                user=membership.user,
                is_active=True
            ).exclude(id=membership.id).exists()
            
            # If no other active memberships, change role back to 'user'
            if not other_active:
                try:
                    profile = UserProfile.objects.get(user=membership.user)
                    if profile.role == 'member':
                        profile.role = 'user'
                        profile.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Changed role for {membership.user.username} from member to user'
                            )
                        )
                except UserProfile.DoesNotExist:
                    pass
            
            count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Expired membership for {membership.user.username} - {membership.membership_plan.name}'
                )
            )
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No memberships to expire'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully expired {count} membership(s)')
            )
