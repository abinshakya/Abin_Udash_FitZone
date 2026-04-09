from django.db import models
from django.conf import settings
from django.utils import timezone


class TrainerRegistration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    experience = models.PositiveIntegerField()
    specialization = models.CharField(max_length=255)
    bio = models.TextField(blank=True, null=True)
    
    # Pricing and Availability
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Monthly training price in Rupees")
    available_time = models.TextField(blank=True, null=True, help_text="Available time slots")

    # approval system
    is_verified = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def get_profile_picture(self):
        """Get the profile picture document if it exists"""
        return self.documents.filter(doc_type='profile_pic').first()
        
    def get_avg_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return round(sum(r.rating for r in reviews) / len(reviews), 1)
        return 0.0

    def __str__(self):
        return f"{self.user.username} - Trainer Registration"


class TrainerRegistrationDocument(models.Model):
    DOC_TYPES = (
        ("certification", "Certification"),
        ("profile_pic", "Profile Picture"),
        ("identity_proof", "Identity Proof"),
        ("experience_verification", "Experience Verification"),
    )

    registration = models.ForeignKey(
        TrainerRegistration,
        related_name="documents",
        on_delete=models.CASCADE
    )

    doc_type = models.CharField(max_length=40, choices=DOC_TYPES)
    file = models.FileField(upload_to="trainer_docs/")
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.registration.user.username} - {self.doc_type}"


class TrainerPhoto(models.Model):
    trainer = models.ForeignKey(
        TrainerRegistration,
        related_name="photos",
        on_delete=models.CASCADE
    )
    photo = models.ImageField(upload_to="trainer_gallery/")
    caption = models.CharField(max_length=200, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.trainer.user.username} - Photo {self.id}"


class TrainerBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('not_required', 'Not Required'),
        ('pending', 'Payment Pending'),
        ('completed', 'Payment Completed'),
        ('overdue', 'Payment Overdue'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainer_bookings')
    trainer = models.ForeignKey(TrainerRegistration, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateField(help_text="Preferred start date")
    message = models.TextField(blank=True, null=True, help_text="Message to the trainer")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Payment tracking
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='not_required')
    payment_due_date = models.DateTimeField(blank=True, null=True, help_text="Payment must be made by this date")
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Booking amount")
    
    # Access validity (per paid booking)
    # When payment is completed, this is typically set to 1 month from either
    # today or from the end of any existing active booking with the same trainer.
    # Stored as DateTimeField to allow minute-level expiry.
    valid_until = models.DateTimeField(blank=True, null=True, help_text="Training access valid until this date and time (inclusive)")
    
    # Cancellation
    cancellation_reason = models.TextField(blank=True, null=True, help_text="Reason for cancellation")
    cancelled_by = models.CharField(max_length=10, blank=True, null=True, choices=[('trainer', 'Trainer'), ('user', 'User'), ('system', 'System')])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} -> {self.trainer.user.username} ({self.status})"

    @property
    def days_left(self):
        """Number of days remaining in this booking's validity.

        Returns an integer >= 0 if ``valid_until`` is set, otherwise ``None``.
        """
        if not self.valid_until:
            return None

        now = timezone.now()

        # If already expired, report 0 days left.
        if self.valid_until <= now:
            return 0

        # Convert to dates for a user-friendly day count
        return max((self.valid_until.date() - now.date()).days, 0)

class TrainerReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainer_reviews')
    trainer = models.ForeignKey(TrainerRegistration, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField(TrainerBooking, on_delete=models.SET_NULL, null=True, blank=True, related_name='review')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], help_text="Rating out of 5")
    comment = models.TextField(blank=True, null=True, help_text="Review comment")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'trainer')

    def __str__(self):
        return f"{self.user.username}'s review for {self.trainer.user.username} ({self.rating}/5)"
