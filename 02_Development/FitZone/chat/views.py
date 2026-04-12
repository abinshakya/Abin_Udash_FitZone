from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Max, Count
from .models import ChatRoom, Message, ChatReport
from trainer.models import TrainerRegistration, TrainerBooking
from login_logout_register.models import UserProfile


def get_profile_picture_url(user):
    try:
        profile = user.userprofile
        if profile.profile_picture:
            return profile.profile_picture.url
    except UserProfile.DoesNotExist:
        pass
    return ''

def _has_chat_access(client_user, trainer_reg):
    now = timezone.now()
    two_days_ago = now - timedelta(days=2)
    
    base_qs = TrainerBooking.objects.filter(
        user=client_user, trainer=trainer_reg, status='confirmed'
    )
    
    has_free = base_qs.filter(payment_status='pending', created_at__gte=two_days_ago).exists()
    has_paid = base_qs.filter(
        payment_status='completed'
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now)).exists()

    return has_free or has_paid

def _handle_session_expiry(room):
    if not _has_chat_access(room.client, room.trainer):
        msg_text = "Your session has ended. Please book again to continue access."
        has_ended_msg = room.messages.filter(message_type='system', content=msg_text).exists()
        
        if not has_ended_msg:
            Message.objects.create(
                room=room,
                sender=room.trainer.user, 
                content=msg_text,
                message_type='system'
            )
            room.updated_at = timezone.now()
            room.save(update_fields=['updated_at'])

@login_required
def trainer_chat(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'trainer':
            return redirect('/')
    except UserProfile.DoesNotExist:
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    if not registration:
        return redirect('trainer_dashboard')

    active_bookings = TrainerBooking.objects.filter(
        trainer=registration,
        status='confirmed',
    ).select_related('user')

    for booking in active_bookings:
        ChatRoom.objects.get_or_create(
            trainer=registration,
            client=booking.user
        )

    chat_rooms = ChatRoom.objects.filter(trainer=registration).select_related(
        'client'
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        )
    ).order_by('-last_message_time')

    active_client_ids = set()
    for booking in active_bookings:
        if _has_chat_access(booking.user, registration):
            active_client_ids.add(booking.user_id)

    room_id = request.GET.get('room')
    active_room = None
    messages_list = []

    if room_id:
        active_room = ChatRoom.objects.filter(id=room_id, trainer=registration).first()

    if active_room:
        _handle_session_expiry(active_room)
        messages_list = active_room.messages.select_related('sender').order_by('created_at').all()
        active_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

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
    active_bookings = TrainerBooking.objects.filter(
        user=request.user,
        status='confirmed',
    ).select_related('trainer__user')

    for booking in active_bookings:
        ChatRoom.objects.get_or_create(
            trainer=booking.trainer,
            client=request.user
        )

    active_trainer_ids = set()
    for booking in active_bookings:
        if _has_chat_access(request.user, booking.trainer):
            active_trainer_ids.add(booking.trainer_id)

    chat_rooms = ChatRoom.objects.filter(client=request.user).select_related(
        'trainer__user'
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        )
    ).order_by('-last_message_time')

    room_id = request.GET.get('room')
    active_room = None
    messages_list = []

    if room_id:
        active_room = ChatRoom.objects.filter(id=room_id, client=request.user).first()

    if active_room:
        _handle_session_expiry(active_room)
        messages_list = active_room.messages.select_related('sender').order_by('created_at').all()
        active_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

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
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user != room.client and request.user != room.trainer.user:
        return JsonResponse({'error': 'Access denied'}, status=403)

    if not _has_chat_access(room.client, room.trainer):
        _handle_session_expiry(room)
        return JsonResponse({'error': 'Booking is no longer active. Book again to access this feature.'}, status=403)

    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')

    if not content and not image:
        return JsonResponse({'error': 'Empty message'}, status=400)

    if image:
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if image.content_type not in allowed_types:
            return JsonResponse({'error': 'Only JPEG, PNG, GIF, and WebP images are allowed.'}, status=400)
        if image.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'Image must be under 5 MB.'}, status=400)

    msg = Message.objects.create(
        room=room,
        sender=request.user,
        content=content,
        image=image,
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
            'image_url': msg.image.url if msg.image else '',
            'message_type': msg.message_type,
            'time': msg.created_at.strftime('%I:%M %p'),
            'is_mine': True,
            'profile_picture': get_profile_picture_url(msg.sender),
        }
    })


@login_required
def fetch_messages(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user != room.client and request.user != room.trainer.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
        
    _handle_session_expiry(room)

    after_id = request.GET.get('after', 0)
    try:
        after_id = int(after_id)
    except (ValueError, TypeError):
        after_id = 0

    new_messages = room.messages.filter(id__gt=after_id).select_related('sender').order_by('created_at')

    new_messages_to_mark = new_messages.filter(is_read=False).exclude(sender=request.user)
    if new_messages_to_mark.exists():
        new_messages_to_mark.update(is_read=True)

    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_name': msg.sender.get_full_name() or msg.sender.username,
            'content': msg.content,
            'image_url': msg.image.url if msg.image else '',
            'message_type': msg.message_type,
            'time': msg.created_at.strftime('%I:%M %p'),
            'is_mine': msg.sender == request.user,
            'profile_picture': get_profile_picture_url(msg.sender),
        })

    return JsonResponse({'messages': messages_data})


@login_required
def delete_room(request, room_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(ChatRoom, id=room_id)

    is_trainer_user = hasattr(room.trainer, 'user') and room.trainer.user == request.user
    is_client_user = room.client == request.user

    if not (is_trainer_user or is_client_user):
        return JsonResponse({'error': 'Access denied'}, status=403)

    room.delete()
    return JsonResponse({'status': 'ok'})


@login_required
def report_room(request, room_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    room = get_object_or_404(ChatRoom, id=room_id)

    is_trainer_user = hasattr(room.trainer, 'user') and room.trainer.user == request.user
    is_client_user = room.client == request.user

    if not (is_trainer_user or is_client_user):
        return JsonResponse({'error': 'Access denied'}, status=403)

    message = request.POST.get('message', '').strip()
    if not message:
        return JsonResponse({'error': 'Please enter a message for the report.'}, status=400)

    ChatReport.objects.create(
        room=room,
        reporter=request.user,
        message=message,
    )

    return JsonResponse({'status': 'ok'})

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
        return redirect('trainer')

    room, _ = ChatRoom.objects.get_or_create(
        trainer=trainer,
        client=request.user
    )

    return redirect(f'/chat/client/?room={room.id}')


from django.utils.timesince import timesince as django_timesince

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
        last_msg = room.messages.order_by('-created_at').first()
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


