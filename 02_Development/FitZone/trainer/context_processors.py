from itertools import chain
from operator import attrgetter

from django.db.models import Q, Count

from trainer.models import TrainerRegistration
from notifications.models import UserNotification, TrainerNotification
from chat.models import ChatRoom


def notification_count(request):
    context = {
        'user_unread_notif_count': 0,
        'navbar_notifications': [],
        'chat_unread_count': 0,
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

        # Total unread chat messages across all rooms for this user
        # Rooms where user is a client
        client_unread = ChatRoom.objects.filter(
            client=request.user
        ).aggregate(
            total=Count(
                'messages',
                filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
            )
        )['total'] or 0

        # Rooms where user is a trainer
        trainer_unread_chat = 0
        if trainer_reg:
            trainer_unread_chat = ChatRoom.objects.filter(
                trainer=trainer_reg
            ).aggregate(
                total=Count(
                    'messages',
                    filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
                )
            )['total'] or 0

        context['chat_unread_count'] = client_unread + trainer_unread_chat
    return context
