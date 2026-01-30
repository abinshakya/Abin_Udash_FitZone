from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('member', 'Member'),
        ('trainer', 'Trainer'),
       
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, default='')
    dob = models.DateField(blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ],
        blank=True,
        null=True
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user'
    )
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
