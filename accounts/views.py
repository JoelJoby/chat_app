from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
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


@login_required
def update_profile(request):
    """AJAX endpoint: update username, email and/or profile picture."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = request.user
    errors = {}

    new_username = request.POST.get('username', '').strip()
    new_email    = request.POST.get('email', '').strip()

    if new_username and new_username != user.username:
        from .models import CustomUser
        if CustomUser.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            errors['username'] = 'Username already taken.'
        else:
            user.username = new_username

    if new_email and new_email != user.email:
        from .models import CustomUser
        if CustomUser.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            errors['email'] = 'Email already in use.'
        else:
            user.email = new_email

    if 'profile_picture' in request.FILES:
        user.profile_picture = request.FILES['profile_picture']

    if errors:
        return JsonResponse({'errors': errors}, status=400)

    user.save()

    picture_url = user.profile_picture.url if user.profile_picture else None
    return JsonResponse({
        'ok': True,
        'username': user.username,
        'email': user.email,
        'picture_url': picture_url,
    })
