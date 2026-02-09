from itertools import chain
from operator import attrgetter

from trainer.models import UserNotification, TrainerNotification, TrainerRegistration


def notification_count(request):
    """Inject unread notification count and recent notifications for the navbar dropdown."""
    context = {
        'user_unread_notif_count': 0,
        'navbar_notifications': [],
    }
    if request.user.is_authenticated:
        user_notifs = list(UserNotification.objects.filter(user=request.user).select_related('booking')[:10])
        user_unread = sum(1 for n in user_notifs if not n.is_read)

        trainer_notifs = []
        trainer_unread = 0
        trainer_reg = TrainerRegistration.objects.filter(user=request.user).first()
        if trainer_reg:
            trainer_notifs = list(TrainerNotification.objects.filter(trainer=trainer_reg).select_related('booking')[:10])
            trainer_unread = sum(1 for n in trainer_notifs if not n.is_read)

        # Merge, sort by created_at desc, take top 8
        merged = sorted(chain(user_notifs, trainer_notifs), key=attrgetter('created_at'), reverse=True)[:8]

        # Tag each notification with its source for URL routing
        for n in merged:
            n.source = 'user' if isinstance(n, UserNotification) else 'trainer'

        context['user_unread_notif_count'] = user_unread + trainer_unread
        context['navbar_notifications'] = merged
    return context
