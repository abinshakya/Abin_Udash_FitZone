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
