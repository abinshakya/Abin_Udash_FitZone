from django.db import models
from django.conf import settings
from trainer.models import TrainerRegistration


class ChatRoom(models.Model):
    """A chat room between a trainer and a client."""
    trainer = models.ForeignKey(
        TrainerRegistration,
        on_delete=models.CASCADE,
        related_name='chat_rooms'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_chat_rooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('trainer', 'client')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat: {self.client.username} <-> {self.trainer.user.username}"

    def get_last_message(self):
        return self.messages.order_by('-created_at').first()

    def get_unread_count_for_user(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    MESSAGE_TYPES = [
        ('normal', 'Normal'),
        ('system', 'System'),
        ('cancellation', 'Cancellation'),
    ]

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='normal')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:40]}"
