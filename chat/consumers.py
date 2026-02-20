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

        # Mark user as online when WebSocket connects
        await self.set_user_online(self.user)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        # Mark user as offline and record last_seen when WebSocket disconnects
        if self.user.is_authenticated:
            await self.set_user_offline(self.user)

    # ──────────────────────────────────────────────
    # Receive message from WebSocket (client → server)
    # ──────────────────────────────────────────────
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        msg_type = text_data_json.get('type', 'message')

        if msg_type == 'read_receipt':
            # Receiver tells us they read messages up to now
            read_ids = text_data_json.get('read_ids', [])
            if read_ids:
                await self.mark_messages_read(read_ids)
                # Broadcast so the sender's window can update ✓ → ✓✓
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'messages_read',
                        'read_ids': read_ids,
                        'reader_id': self.user.id,
                    }
                )
        else:
            # Normal chat message
            message_text = text_data_json['message']

            # Save message to database, get its ID back
            message_id = await self.save_message(message_text)

            # Broadcast to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_text,
                    'sender': self.user.username,
                    'sender_id': self.user.id,
                    'message_id': message_id,
                }
            )

    # ──────────────────────────────────────────────
    # Group event handlers (server → client WebSocket)
    # ──────────────────────────────────────────────

    async def chat_message(self, event):
        """Deliver a new chat message to this WebSocket connection."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'message_id': event['message_id'],
        }))

    async def messages_read(self, event):
        """Tell the sender's client that specific messages were read."""
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'read_ids': event['read_ids'],
            'reader_id': event['reader_id'],
        }))



    # ──────────────────────────────────────────────
    # Database helpers
    # ──────────────────────────────────────────────

    @database_sync_to_async
    def check_user_exists(self, user_id):
        return User.objects.filter(id=user_id).exists()

    @database_sync_to_async
    def save_message(self, message):
        """Save a message and return its primary-key ID."""
        other_user = User.objects.get(id=self.other_user_id)
        msg = Message.objects.create(
            sender=self.user,
            receiver=other_user,
            message=message
        )
        return msg.id

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        """Mark a list of message IDs as read."""
        Message.objects.filter(
            id__in=message_ids,
            receiver=self.user,   # Only the receiver can mark as read
            is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def set_user_online(self, user):
        """Mark the user as online and refresh last_seen."""
        from django.utils import timezone
        User.objects.filter(pk=user.pk).update(
            is_online=True,
            last_seen=timezone.now()
        )

    @database_sync_to_async
    def set_user_offline(self, user):
        """Mark the user as offline and record the time they were last seen."""
        from django.utils import timezone
        User.objects.filter(pk=user.pk).update(
            is_online=False,
            last_seen=timezone.now()
        )