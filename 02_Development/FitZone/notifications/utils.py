
from .models import TrainerNotification, UserNotification


def create_trainer_notification(trainer, notif_type, title, message, booking=None):
    return TrainerNotification.objects.create(
        trainer=trainer,
        booking=booking,
        notif_type=notif_type,
        title=title,
        message=message
    )


def create_user_notification(user, notif_type, title, message, booking=None):
    return UserNotification.objects.create(
        user=user,
        booking=booking,
        notif_type=notif_type,
        title=title,
        message=message
    )


def mark_trainer_notifications_as_read(trainer, notification_ids=None):
    queryset = trainer.notifications.filter(is_read=False)
    if notification_ids:
        queryset = queryset.filter(id__in=notification_ids)
    return queryset.update(is_read=True)


def mark_user_notifications_as_read(user, notification_ids=None):
    queryset = UserNotification.objects.filter(user=user, is_read=False)
    if notification_ids:
        queryset = queryset.filter(id__in=notification_ids)
    return queryset.update(is_read=True)


def get_unread_trainer_notifications(trainer, limit=None):
    queryset = trainer.notifications.filter(is_read=False)
    if limit:
        queryset = queryset[:limit]
    return queryset


def get_unread_user_notifications(user, limit=None):
    queryset = UserNotification.objects.filter(user=user, is_read=False)
    if limit:
        queryset = queryset[:limit]
    return queryset
