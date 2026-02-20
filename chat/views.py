from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Message

User = get_user_model()

@login_required(login_url='login')
def chat_with_user(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    users = User.objects.exclude(id=request.user.id)
    
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
    # Create a consistent room name based on user IDs
    if request.user.id > other_user.id:
        room_name = f"private_{other_user.id}_{request.user.id}"
    else:
        room_name = f"private_{request.user.id}_{other_user.id}"
    return redirect('chat:room', room_name=room_name)
