from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),
    path('auth/', include('accounts.urls')),
    path('', lambda request: redirect('auth/login/')), # Redirect root to login
]
