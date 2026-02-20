import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        self.other_user_id = self.scope['url_route']['kwargs']['id']
        
        # Verify other user exists
        is_valid_user = await self.check_user_exists(self.other_user_id)
        if not is_valid_user:
            await self.close()
            return

        # Create unique room name based on sorted user IDs
        # This ensures user A -> user B and user B -> user A land in the same room
        try:
            other_user_id_int = int(self.other_user_id)
            user_ids = sorted([self.user.id, other_user_id_int])
            self.room_group_name = f'chat_{user_ids[0]}_{user_ids[1]}'
        except ValueError:
            await self.close()
            return

        # Add to group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Leave message group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        # Save message to database
        await self.save_message(message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username,
                'sender_id': self.user.id
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']
        sender_id = event.get('sender_id')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
            'sender_id': sender_id
        }))

    @database_sync_to_async
    def check_user_exists(self, user_id):
        return User.objects.filter(id=user_id).exists()

    @database_sync_to_async
    def save_message(self, message):
        other_user = User.objects.get(id=self.other_user_id)
        Message.objects.create(
            sender=self.user,
            receiver=other_user,
            message=message
        )