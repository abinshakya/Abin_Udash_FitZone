from django.db import models
from django.conf import settings
from membership.models import MembershipPlan


class KhaltiPayment(models.Model):
    STATUS_CHOICES = (
        ('Initiated', 'Initiated'),
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Expired', 'Expired'),
        ('User canceled', 'User canceled'),
        ('Refunded', 'Refunded'),
        ('Partially refunded', 'Partially refunded'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    membership_plan = models.ForeignKey(MembershipPlan, on_delete=models.SET_NULL, null=True)
    
    pidx = models.CharField(max_length=255, unique=True, db_index=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    purchase_order_id = models.CharField(max_length=255, unique=True)
    purchase_order_name = models.CharField(max_length=255)
    
    amount = models.IntegerField(help_text="Amount in paisa")
    total_amount = models.IntegerField(null=True, blank=True)
    fee = models.IntegerField(default=0)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Initiated')
    refunded = models.BooleanField(default=False)
    
    payment_url = models.URLField(max_length=500, null=True, blank=True)
    mobile = models.CharField(max_length=15, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['pidx']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.purchase_order_name} - {self.status}"
    
    @property
    def amount_in_rupees(self):
        return self.amount / 100
