from django.db import models
from django.conf import settings


class TrainerNotification(models.Model):
    NOTIF_TYPES = [
        ('booking', 'New Booking'),
        ('cancellation', 'Booking Cancelled'),
        ('approved', 'Registration Approved'),
        ('rejected', 'Registration Rejected'),
        ('general', 'General'),
    ]

    trainer = models.ForeignKey('trainer.TrainerRegistration', on_delete=models.CASCADE, related_name='notifications')
    booking = models.ForeignKey('trainer.TrainerBooking', on_delete=models.CASCADE, null=True, blank=True, related_name='trainer_notifications')
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Trainer Notification'
        verbose_name_plural = 'Trainer Notifications'

    def __str__(self):
        return f"[{self.notif_type}] {self.title} -> {self.trainer.user.username}"


class UserNotification(models.Model):
    NOTIF_TYPES = [
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_rejected', 'Booking Rejected'),
        ('payment_required', 'Payment Required'),
        ('workout_plan', 'Workout Plan Update'),
        ('diet_plan', 'Diet Plan Update'),
        ('meal_added', 'Meal Added'),
        ('exercise_added', 'Exercise Added'),
        ('plan_deleted', 'Plan Deleted'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_notifications')
    booking = models.ForeignKey('trainer.TrainerBooking', on_delete=models.CASCADE, null=True, blank=True, related_name='user_notifications')
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Notification'
        verbose_name_plural = 'User Notifications'

    def __str__(self):
        return f"[{self.notif_type}] {self.title} -> {self.user.username}"
