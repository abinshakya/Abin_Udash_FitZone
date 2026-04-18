from django.test import TestCase
from django.contrib.auth.models import User

from .forms import RegistrationForm


class RegistrationFormTests(TestCase):
    def get_valid_payload(self):
        return {
            'name': 'Api L Paudel',
            'username': 'apil123',
            'email': 'apil@sd.com',
            'phone': '9812345678',
            'age': 25,
            'gender': 'male',
            'password': 'Pass1234',
            'confirm_password': 'Pass1234',
        }

    def test_valid_form(self):
        form = RegistrationForm(data=self.get_valid_payload())
        self.assertTrue(form.is_valid())

    def test_rejects_non_sd_domain_email(self):
        data = self.get_valid_payload()
        data['email'] = 'user@gmail.com'
        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_rejects_non_10_digit_phone(self):
        data = self.get_valid_payload()
        data['phone'] = '980123'
        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_rejects_password_without_number(self):
        data = self.get_valid_payload()
        data['password'] = 'Password'
        data['confirm_password'] = 'Password'
        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

    def test_rejects_password_mismatch(self):
        data = self.get_valid_payload()
        data['confirm_password'] = 'Pass9999'
        form = RegistrationForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('confirm_password', form.errors)

    def test_rejects_duplicate_username_and_email(self):
        User.objects.create_user(username='apil123', email='apil@sd.com', password='Pass1234')

        form = RegistrationForm(data=self.get_valid_payload())
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)
