from django import forms
from .models import TrainerPaymentRequest


class TrainerPaymentRequestForm(forms.ModelForm):
    class Meta:
        model = TrainerPaymentRequest
        fields = ['bank_name', 'account_holder_name', 'account_number', 'bank_qr']
        widgets = {
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Nepal Bank Ltd, NIC Asia, etc.',
            }),
            'account_holder_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name as on bank account',
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank account number',
            }),
            'bank_qr': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        bank_name = cleaned_data.get('bank_name', '').strip()
        account_number = cleaned_data.get('account_number', '').strip()
        bank_qr = cleaned_data.get('bank_qr')

        has_bank = bank_name and account_number
        has_qr = bank_qr

        if not has_bank and not has_qr:
            raise forms.ValidationError(
                'Please provide either bank details (bank name + account number) or upload a bank QR code.'
            )
        return cleaned_data
