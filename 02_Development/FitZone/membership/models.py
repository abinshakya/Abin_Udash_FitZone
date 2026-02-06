from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class MembershipPlan(models.Model):
    DURATION_CHOICES = [
        ('1M', '1 Month'),
        ('3M', '3 Months'),
        ('6M', '6 Months'),
        ('1Y', '1 Year'),
    ]

    name = models.CharField(max_length=100, default="AI Trainer Membership")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.CharField(max_length=2, choices=DURATION_CHOICES)

    description = models.TextField(blank=True)

    # AI feature bullet points (short text)
    feature_1 = models.CharField(max_length=80)
    feature_2 = models.CharField(max_length=80)
    feature_3 = models.CharField(max_length=80, blank=True)

    image = models.ImageField(upload_to='images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_duration_display()})"
    
    def get_duration_days(self):
        # Convert duration to days
        duration_map = {
            '1M': 30,
            '3M': 90,
            '6M': 180,
            '1Y': 365,
        }
        return duration_map.get(self.duration, 30)


class UserMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    membership_plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.membership_plan.name}"
    
    @property
    def days_left(self):
        # Calculate days remaining in membership
        if not self.is_active:
            return 0
        remaining = self.end_date - timezone.now()
        return max(0, remaining.days)
    
    @property
    def total_days(self):
        # Total days in membership period
        total = self.end_date - self.start_date
        return total.days
    
    @property
    def progress_percentage(self):
        # Percentage of membership period completed
        if self.total_days == 0:
            return 100
        elapsed = (timezone.now() - self.start_date).days
        return min(100, max(0, (elapsed / self.total_days) * 100))
    
    def save(self, *args, **kwargs):
        # Auto-calculate end_date if not set
        if not self.end_date and self.membership_plan:
            self.end_date = timezone.now() + timedelta(days=self.membership_plan.get_duration_days())
        
        # Check if membership has expired
        if timezone.now() > self.end_date:
            self.is_active = False
            # Change user role back to 'user' when membership expires
            try:
                from login_logout_register.models import UserProfile
                profile = UserProfile.objects.get(user=self.user)
                if profile.role == 'member':
                    profile.role = 'user'
                    profile.save()
            except UserProfile.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
