from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('users/', views.user_list, name='user_list'),
    path('chat/<int:user_id>/', views.chat_with_user, name='chat_with_user'),
    path('chat/<int:user_id>/mark-read/', views.mark_messages_read, name='mark_messages_read'),
    path('messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
]
