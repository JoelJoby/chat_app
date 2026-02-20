from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import UserRegistrationForm, UserLoginForm


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Mark user as online immediately after registration
            user.is_online = True
            user.last_seen = timezone.now()
            user.save(update_fields=['is_online', 'last_seen'])
            login(request, user)
            return redirect('chat:user_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Mark user as online on login
            user.is_online = True
            user.last_seen = timezone.now()
            user.save(update_fields=['is_online', 'last_seen'])
            login(request, user)
            return redirect('chat:user_list')
    else:
        form = UserLoginForm(request)
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    # Mark user as offline and record last_seen before logging out
    if request.user.is_authenticated:
        request.user.is_online = False
        request.user.last_seen = timezone.now()
        request.user.save(update_fields=['is_online', 'last_seen'])
    logout(request)
    return redirect('login')
