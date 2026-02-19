from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from chat.views import landing_page


urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),
    path('auth/', include('accounts.urls')),
    path('', landing_page, name='landing'),

]
