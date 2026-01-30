from django.db import models

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
