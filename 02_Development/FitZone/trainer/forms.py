# forms.py
from django import forms
from django.core.exceptions import ValidationError

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


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class Step1BasicInfoForm(forms.Form):
    experience = forms.IntegerField(
        min_value=0,
        max_value=60,
        label="Years of Experience",
        widget=forms.NumberInput(attrs={
            'placeholder': 'e.g. 5',
            'class': 'form-input'
        }),
        help_text="Total years as a professional fitness trainer"
    )
    
    specialization = forms.CharField(
        max_length=500,
        label="Area of Expertise",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Strength Training, Yoga, Cardio',
            'class': 'form-input'
        }),
        help_text="Your main training specialties (comma separated)"
    )
    
    bio = forms.CharField(
        required=False,
        label="Professional Bio",
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Tell clients about your training philosophy, achievements, and what makes you unique...',
            'class': 'form-textarea'
        }),
        help_text="A brief introduction about yourself (optional)"
    )

    def clean_specialization(self):
        spec = (self.cleaned_data.get("specialization") or "").strip()
        if len(spec) < 3:
            raise ValidationError("Please enter at least 3 characters.")
        return spec


class Step2CertificationForm(forms.Form):
    certification = MultipleFileField(
        label="Certification Documents",
        help_text="Upload your fitness certifications (PDF or images)",
        required=True
    )
    
    profile_pic = forms.FileField(
        label="Profile Picture",
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*',
            'class': 'file-input'
        }),
        help_text="Upload your professional profile photo",
        required=True
    )


class Step3DocumentsForm(forms.Form):
    identity_proof = MultipleFileField(
        label="Identity Proof",
        help_text="Government-issued ID (License, Passport, etc.)",
        required=True
    )
    
    experience_verification = MultipleFileField(
        label="Experience Verification",
        help_text="Previous employment letters or gym certifications",
        required=True
    )
