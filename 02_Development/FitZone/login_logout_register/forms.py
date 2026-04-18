from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class RegistrationForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        min_length=2,
        strip=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z ]+$',
                message='Full name can contain only letters and spaces.',
            )
        ],
    )
    username = forms.CharField(
        max_length=30,
        min_length=3,
        strip=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9_]+$',
                message='Username can contain only letters, numbers, and underscore.',
            )
        ],
    )
    email = forms.EmailField(max_length=254)
    phone = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='Phone number must be exactly 10 digits.',
            )
        ]
    )
    age = forms.IntegerField(min_value=13, max_value=120)
    gender = forms.ChoiceField(
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ]
    )
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    confirm_password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def clean_name(self):
        name = self.cleaned_data['name']
        normalized_name = ' '.join(name.split())
        if len(normalized_name) < 2:
            raise forms.ValidationError('Full name must be at least 2 characters.')
        return normalized_name

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email.endswith('@sd.com'):
            raise forms.ValidationError('Email must end with @sd.com.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
            raise forms.ValidationError('Password must include both letters and numbers.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')

        return cleaned_data