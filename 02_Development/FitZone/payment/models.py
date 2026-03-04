from django.db import models
from django.conf import settings
from membership.models import MembershipPlan
from trainer.models import TrainerBooking, TrainerRegistration


def qr_upload_path(instance, filename):
    import os
    ext = os.path.splitext(filename)[1]
    return f'payment_qr/{instance.trainer.user.username}_qr{ext}'


def receipt_upload_path(instance, filename):
    import os
    ext = os.path.splitext(filename)[1]
    return f'payment_receipts/{instance.trainer.user.username}_{instance.id}{ext}'


class KhaltiPayment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('membership', 'Membership'),
        ('booking', 'Trainer Booking'),
    )

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
    membership_plan = models.ForeignKey(MembershipPlan, on_delete=models.SET_NULL, null=True, blank=True)
    booking = models.ForeignKey(TrainerBooking, on_delete=models.SET_NULL, null=True, blank=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='membership')
    
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


class TrainerPaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    trainer = models.ForeignKey(TrainerRegistration, on_delete=models.CASCADE, related_name='payment_requests')
    booking = models.ForeignKey(TrainerBooking, on_delete=models.CASCADE, related_name='payment_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Booking amount minus 10% platform fee')

    # Bank details (trainer provides one or both)
    bank_name = models.CharField(max_length=150, blank=True, default='')
    account_holder_name = models.CharField(max_length=200, blank=True, default='')
    account_number = models.CharField(max_length=50, blank=True, default='')
    bank_qr = models.ImageField(upload_to=qr_upload_path, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True, default='')
    receipt = models.ImageField(upload_to=receipt_upload_path, blank=True, null=True, help_text='Admin uploads payment receipt after transfer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.trainer.user.username} - ₹{self.amount} ({self.status})"
