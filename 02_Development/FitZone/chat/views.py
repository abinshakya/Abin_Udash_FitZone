from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timesince import timesince as django_timesince
from django.db.models import Q, Max, Count, Subquery, OuterRef
from .models import ChatRoom, Message
from trainer.models import TrainerRegistration, TrainerBooking
from login_logout_register.models import UserProfile


def get_profile_picture_url(user):
    """Get profile picture URL for a user, or empty string if none."""
    try:
        profile = user.userprofile
        if profile.profile_picture:
            return profile.profile_picture.url
    except UserProfile.DoesNotExist:
        pass
    return ''


@login_required
def trainer_chat(request):
    """Chat page for trainers — shows all client conversations."""
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'trainer':
            return redirect('/')
    except UserProfile.DoesNotExist:
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    if not registration:
        return redirect('trainer_dashboard')

    # Get or create chat rooms for all confirmed clients
    active_bookings = TrainerBooking.objects.filter(
        trainer=registration,
        status='confirmed',
    ).select_related('user')

    for booking in active_bookings:
        ChatRoom.objects.get_or_create(
            trainer=registration,
            client=booking.user
        )

    # Fetch ALL chat rooms (including past/cancelled) to preserve chat history
    chat_rooms = ChatRoom.objects.filter(trainer=registration).select_related(
        'client'
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        )
    ).order_by('-last_message_time')

    # Determine which clients have active bookings
    active_client_ids = set(
        TrainerBooking.objects.filter(
            trainer=registration,
            status='confirmed',
        ).values_list('user_id', flat=True)
    )

    # Active room
    room_id = request.GET.get('room')
    active_room = None
    messages_list = []

    if room_id:
        active_room = ChatRoom.objects.filter(id=room_id, trainer=registration).first()

    if active_room:
        messages_list = active_room.messages.select_related('sender').all()
        # Mark messages as read
        active_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    # Check if active room's client has an active booking
    active_room_is_active = False
    if active_room and active_room.client_id in active_client_ids:
        active_room_is_active = True

    total_unread = sum(room.unread for room in chat_rooms)

    context = {
        'registration': registration,
        'chat_rooms': chat_rooms,
        'active_room': active_room,
        'messages': messages_list,
        'total_unread': total_unread,
        'user_role': 'trainer',
        'active_client_ids': active_client_ids,
        'active_room_is_active': active_room_is_active,
    }
    return render(request, 'chat/trainer_chat.html', context)


@login_required
def client_chat(request):
    """Chat page for clients — shows all trainer conversations (including past)."""
    # Get active trainer bookings for this user
    active_bookings = TrainerBooking.objects.filter(
        user=request.user,
        status='confirmed',
    ).select_related('trainer__user')

    # Create chat rooms for each active booking
    for booking in active_bookings:
        ChatRoom.objects.get_or_create(
            trainer=booking.trainer,
            client=request.user
        )

    # Determine which trainers have active bookings
    active_trainer_ids = set(
        TrainerBooking.objects.filter(
            user=request.user,
            status='confirmed',
        ).values_list('trainer_id', flat=True)
    )

    # Fetch ALL chat rooms (including past/cancelled) to preserve chat history
    chat_rooms = ChatRoom.objects.filter(client=request.user).select_related(
        'trainer__user'
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        )
    ).order_by('-last_message_time')

    # Active room
    room_id = request.GET.get('room')
    active_room = None
    messages_list = []

    if room_id:
        active_room = ChatRoom.objects.filter(id=room_id, client=request.user).first()

    if active_room:
        messages_list = active_room.messages.select_related('sender').all()
        active_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    # Check if active room's trainer has an active booking
    active_room_is_active = False
    if active_room and active_room.trainer_id in active_trainer_ids:
        active_room_is_active = True

    total_unread = sum(room.unread for room in chat_rooms)

    context = {
        'chat_rooms': chat_rooms,
        'active_room': active_room,
        'messages': messages_list,
        'total_unread': total_unread,
        'user_role': 'client',
        'active_trainer_ids': active_trainer_ids,
        'active_room_is_active': active_room_is_active,
    }
    return render(request, 'chat/client_chat.html', context)


@login_required
def send_message(request, room_id):
    """Send a message in a chat room (AJAX)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(ChatRoom, id=room_id)

    # Verify user is part of this chat
    if request.user != room.client and request.user != room.trainer.user:
        return JsonResponse({'error': 'Access denied'}, status=403)

    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Empty message'}, status=400)

    msg = Message.objects.create(
        room=room,
        sender=request.user,
        content=content
    )
    room.updated_at = timezone.now()
    room.save(update_fields=['updated_at'])

    return JsonResponse({
        'status': 'ok',
        'message': {
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_name': msg.sender.get_full_name() or msg.sender.username,
            'content': msg.content,
            'message_type': msg.message_type,
            'time': msg.created_at.strftime('%I:%M %p'),
            'is_mine': True,
            'profile_picture': get_profile_picture_url(msg.sender),
        }
    })


@login_required
def fetch_messages(request, room_id):
    """Fetch new messages for polling (AJAX)."""
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user != room.client and request.user != room.trainer.user:
        return JsonResponse({'error': 'Access denied'}, status=403)

    after_id = request.GET.get('after', 0)
    try:
        after_id = int(after_id)
    except (ValueError, TypeError):
        after_id = 0

    new_messages = room.messages.filter(id__gt=after_id).select_related('sender')

    # Mark received messages as read
    new_messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_name': msg.sender.get_full_name() or msg.sender.username,
            'content': msg.content,
            'message_type': msg.message_type,
            'time': msg.created_at.strftime('%I:%M %p'),
            'is_mine': msg.sender == request.user,
            'profile_picture': get_profile_picture_url(msg.sender),
        })

    return JsonResponse({'messages': messages_data})


@login_required
def start_chat_with_trainer(request, trainer_id):
    """Start or open a chat with a specific trainer (from client dashboard)."""
    trainer = get_object_or_404(TrainerRegistration, id=trainer_id)

    # Check for any booking (active or past) - allow viewing past chat history
    has_any_booking = TrainerBooking.objects.filter(
        user=request.user,
        trainer=trainer,
    ).exists()

    if not has_any_booking:
        return redirect('trainer_client_dashboard')

    room, _ = ChatRoom.objects.get_or_create(
        trainer=trainer,
        client=request.user
    )

    return redirect(f'/chat/client/?room={room.id}')


def _smart_time_ago(dt):
    if dt is None:
        return ''
    delta = timezone.now() - dt
    if delta.total_seconds() < 60:
        return 'just now'
    return django_timesince(dt) + ' ago'


@login_required
def fetch_chat_list(request):
    role = request.GET.get('role', 'client')
    user = request.user

    if role == 'trainer':
        registration = TrainerRegistration.objects.filter(user=user).first()
        if not registration:
            return JsonResponse({'rooms': [], 'total_unread': 0})

        chat_rooms = ChatRoom.objects.filter(trainer=registration).annotate(
            last_message_time=Max('messages__created_at'),
            unread=Count(
                'messages',
                filter=Q(messages__is_read=False) & ~Q(messages__sender=user)
            )
        ).order_by('-last_message_time')
    else:
        chat_rooms = ChatRoom.objects.filter(client=user).annotate(
            last_message_time=Max('messages__created_at'),
            unread=Count(
                'messages',
                filter=Q(messages__is_read=False) & ~Q(messages__sender=user)
            )
        ).order_by('-last_message_time')

    rooms_data = []
    for room in chat_rooms:
        last_msg = room.get_last_message()
        if last_msg:
            time_display = _smart_time_ago(last_msg.created_at)
            preview = last_msg.content[:35]
            if len(last_msg.content) > 35:
                preview += '...'
        else:
            time_display = ''
            preview = 'No messages yet'

        rooms_data.append({
            'id': room.id,
            'last_message': preview,
            'time': time_display,
            'unread': room.unread,
        })

    total_unread = sum(r['unread'] for r in rooms_data)
    return JsonResponse({'rooms': rooms_data, 'total_unread': total_unread})
