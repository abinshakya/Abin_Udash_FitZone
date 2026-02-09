from django.db import models
from django.conf import settings


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
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.registration.user.username} - {self.doc_type}"


class TrainerPhoto(models.Model):
    """Photos uploaded by trainers for their public gallery"""
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
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainer_bookings')
    trainer = models.ForeignKey(TrainerRegistration, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateField(help_text="Preferred start date")
    message = models.TextField(blank=True, null=True, help_text="Message to the trainer")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} -> {self.trainer.user.username} ({self.status})"


class TrainerNotification(models.Model):
    NOTIF_TYPES = [
        ('booking', 'New Booking'),
        ('cancellation', 'Booking Cancelled'),
        ('approved', 'Registration Approved'),
        ('rejected', 'Registration Rejected'),
        ('general', 'General'),
    ]

    trainer = models.ForeignKey(TrainerRegistration, on_delete=models.CASCADE, related_name='notifications')
    booking = models.ForeignKey(TrainerBooking, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notif_type}] {self.title} -> {self.trainer.user.username}"


class UserNotification(models.Model):
    NOTIF_TYPES = [
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_rejected', 'Booking Rejected'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_notifications')
    booking = models.ForeignKey(TrainerBooking, on_delete=models.CASCADE, null=True, blank=True, related_name='user_notifications')
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notif_type}] {self.title} -> {self.user.username}"
