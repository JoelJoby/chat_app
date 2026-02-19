from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url='login')
def room(request, room_name):
    return render(request, "chat/room.html", {
        "room_name": room_name
    })

def landing_page(request):
    return render(request, 'chat/landing.html')
