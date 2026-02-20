from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('users/', views.user_list, name='user_list'),
    path('chat/<int:user_id>/', views.chat_with_user, name='chat_with_user'),
    # path('start_chat/<int:user_id>/', views.start_chat, name='start_chat'), # Deprecated
    # path('<str:room_name>/', views.room, name='room'), # Deprecated
]
