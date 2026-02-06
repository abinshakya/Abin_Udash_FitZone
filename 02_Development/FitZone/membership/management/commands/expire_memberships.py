from django.core.management.base import BaseCommand
from django.utils import timezone
from membership.models import UserMembership
from login_logout_register.models import UserProfile


class Command(BaseCommand):
    help = 'Expire memberships that have passed their end date'

    def handle(self, *args, **kwargs):
        # Find all active memberships that have expired
        expired_memberships = UserMembership.objects.filter(
            is_active=True,
            end_date__lt=timezone.now()
        )
        
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
