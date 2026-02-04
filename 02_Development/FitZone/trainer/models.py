from django.db import models
from django.conf import settings


class TrainerRegistration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    experience = models.PositiveIntegerField()
    specialization = models.CharField(max_length=255)
    bio = models.TextField(blank=True, null=True)

    # approval system
    is_verified = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

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
