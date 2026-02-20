from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Message

User = get_user_model()

@login_required(login_url='login')
def chat_with_user(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    users = User.objects.exclude(id=request.user.id)

    # Mark all unread messages sent by other_user to this user as read
    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    # Get message history
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')

    return render(request, 'chat/chat.html', {
        'users': users,
        'other_user': other_user,
        'messages': messages
    })


@login_required(login_url='login')
@require_POST
def mark_messages_read(request, user_id):
    """
    AJAX endpoint: mark all messages from user_id -> request.user as read.
    Called via fetch() when the receiver has the chat window open.
    Returns a JSON list of message IDs that were just marked read,
    so the sender's JS can update the ✓ → ✓✓ icon in real-time via WS.
    """
    other_user = get_object_or_404(User, id=user_id)
    updated_ids = list(
        Message.objects.filter(
            sender=other_user,
            receiver=request.user,
            is_read=False
        ).values_list('id', flat=True)
    )
    Message.objects.filter(id__in=updated_ids).update(is_read=True)
    return JsonResponse({'read_ids': updated_ids})


@login_required(login_url='login')
def room(request, room_name):
    return render(request, "chat/room.html", {
        "room_name": room_name
    })


def landing_page(request):
    return render(request, 'chat/landing.html')


@login_required(login_url='login')
def user_list(request):
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'chat/user_list.html', {'users': users})


@login_required(login_url='login')
def start_chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if request.user.id > other_user.id:
        room_name = f"private_{other_user.id}_{request.user.id}"
    else:
        room_name = f"private_{request.user.id}_{other_user.id}"
    return redirect('chat:room', room_name=room_name)
