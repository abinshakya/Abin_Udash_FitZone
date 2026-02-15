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
    def __init__(self, *args, max_files=None, **kwargs):
        self.max_files = max_files
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            if self.max_files and len(data) > self.max_files:
                raise ValidationError(f"You can upload a maximum of {self.max_files} files.")
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


SPECIALIZATION_CHOICES = [
    ('strength_training', 'Strength Training'),
    ('cardio', 'Cardio & Endurance'),
    ('yoga', 'Yoga'),
    ('pilates', 'Pilates'),
    ('crossfit', 'CrossFit'),
    ('bodybuilding', 'Bodybuilding'),
    ('weight_loss', 'Weight Loss'),
    ('nutrition', 'Nutrition & Diet'),
    ('sports_specific', 'Sports-Specific Training'),
    ('rehabilitation', 'Rehabilitation & Recovery'),
    ('senior_fitness', 'Senior Fitness'),
    ('prenatal_postnatal', 'Prenatal/Postnatal'),
    ('hiit', 'HIIT (High-Intensity Interval Training)'),
    ('functional_training', 'Functional Training'),
    ('martial_arts', 'Martial Arts'),
    ('dance_fitness', 'Dance Fitness'),
]

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
    
    specialization = forms.MultipleChoiceField(
        choices=SPECIALIZATION_CHOICES,
        label="Area of Expertise",
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'tag-checkbox'
        }),
        help_text="Select all areas you specialize in"
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
    
    monthly_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="Monthly Training Price (₹)",
        widget=forms.NumberInput(attrs={
            'placeholder': 'e.g. 5000.00',
            'class': 'form-input',
            'step': '0.01'
        }),
        help_text="Your monthly training fee in Rupees (optional)"
    )
    
    available_days_from = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select Day'),
            ('sunday', 'Sunday'),
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
        ],
        label="Available From",
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
        help_text="Starting day of your availability"
    )
    
    available_days_to = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select Day'),
            ('sunday', 'Sunday'),
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
        ],
        label="Available To",
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
        help_text="Ending day of your availability"
    )
    
    available_time_slots = forms.MultipleChoiceField(
        required=False,
        choices=[
            ('6-10', '6 AM - 10 AM'),
            ('10-12', '10 AM - 12 PM'),
            ('12-3', '12 PM - 3 PM'),
            ('3-6', '3 PM - 6 PM'),
            ('6-9', '6 PM - 9 PM'),
            ('9-12', '9 PM - 12 AM'),
        ],
        label="Time Slots",
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'tag-checkbox'
        }),
        help_text="Select your available time slots (optional)"
    )

    def clean_specialization(self):
        spec_list = self.cleaned_data.get("specialization") or []
        if len(spec_list) < 1:
            raise ValidationError("Please select at least one area of expertise.")
        return spec_list


class Step2CertificationForm(forms.Form):
    certification = MultipleFileField(
        label="Certification Documents",
        help_text="Upload your fitness certifications (PDF or images, up to 5 files)",
        required=True,
        max_files=5,
        widget=MultipleFileInput(attrs={
            'accept': 'image/*,application/pdf',
            'class': 'file-input'
        })
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
        help_text="Government-issued ID (License, Passport, etc., up to 5 files)",
        required=True,
        max_files=5,
        widget=MultipleFileInput(attrs={
            'accept': 'image/*,application/pdf',
            'class': 'file-input'
        })
    )
    
    experience_verification = MultipleFileField(
        label="Experience Verification",
        help_text="Previous employment letters or gym certifications (up to 5 files)",
        required=True,
        max_files=5,
        widget=MultipleFileInput(attrs={
            'accept': 'image/*,application/pdf',
            'class': 'file-input'
        })
    )


class TrainerProfileEditForm(forms.Form):
    """Form for editing existing trainer profile"""
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
    
    specialization = forms.MultipleChoiceField(
        choices=SPECIALIZATION_CHOICES,
        label="Area of Expertise",
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'tag-checkbox'
        }),
        help_text="Select all areas you specialize in"
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
    
    monthly_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="Monthly Training Price (₹)",
        widget=forms.NumberInput(attrs={
            'placeholder': 'e.g. 5000.00',
            'class': 'form-input',
            'step': '0.01'
        }),
        help_text="Your monthly training fee in Rupees (optional)"
    )
    
    available_days_from = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select Day'),
            ('sunday', 'Sunday'),
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
        ],
        label="Available From",
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
        help_text="Starting day of your availability"
    )
    
    available_days_to = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select Day'),
            ('sunday', 'Sunday'),
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
        ],
        label="Available To",
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
        help_text="Ending day of your availability"
    )
    
    available_time_slots = forms.MultipleChoiceField(
        required=False,
        choices=[
            ('6-10', '6 AM - 10 AM'),
            ('10-12', '10 AM - 12 PM'),
            ('12-3', '12 PM - 3 PM'),
            ('3-6', '3 PM - 6 PM'),
            ('6-9', '6 PM - 9 PM'),
            ('9-12', '9 PM - 12 AM'),
        ],
        label="Time Slots",
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'tag-checkbox'
        }),
        help_text="Select your available time slots (optional)"
    )

    def clean_specialization(self):
        spec_list = self.cleaned_data.get("specialization") or []
        if len(spec_list) < 1:
            raise ValidationError("Please select at least one area of expertise.")
        return spec_list
