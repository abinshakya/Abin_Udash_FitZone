# forms.py
from django import forms
from django.core.exceptions import ValidationError

from .models import TrainerRegistration  # change if your model name differs


MAX_FILE_MB = 5
MAX_FILE_SIZE = MAX_FILE_MB * 1024 * 1024

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_DOC_TYPES = ALLOWED_IMAGE_TYPES | {"application/pdf"}


def validate_file_size(file):
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(f"File too large (max {MAX_FILE_MB}MB).")


def validate_content_type(file, allowed_types):
    ctype = getattr(file, "content_type", None)
    if ctype and ctype not in allowed_types:
        raise ValidationError("Invalid file type. Please upload a valid file.")


class TrainerRegistrationForm(forms.ModelForm):
    class Meta:
        model = TrainerRegistration
        fields = ["experience", "specialization", "bio"]  # keep only DB fields here

        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
        }

        error_messages = {
            "experience": {
                "required": "Please enter your experience in years.",
                "invalid": "Please enter a valid number.",
            },
            "specialization": {
                "required": "Please enter your specialization.",
            },
        }

    def clean_experience(self):
        exp = self.cleaned_data.get("experience")
        if exp is None:
            return exp
        if exp < 0:
            raise ValidationError("Experience cannot be negative.")
        if exp > 60:
            raise ValidationError("Experience seems too high. Please enter a realistic value.")
        return exp

    def clean_specialization(self):
        spec = (self.cleaned_data.get("specialization") or "").strip()
        if len(spec) < 3:
            raise ValidationError("Specialization must be at least 3 characters.")
        return spec
