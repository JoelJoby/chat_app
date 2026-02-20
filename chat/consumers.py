"""
consumers.py – Secure WebSocket consumer for private 1-to-1 chat.

Security layers applied
───────────────────────
1. Transport-level  : AllowedHostsOriginValidator in asgi.py rejects
                      connections from foreign origins (stops CSWSH).
2. Authentication   : Unauthenticated scope → 403 close before accept().
3. Self-chat block  : Users cannot open a room with themselves.
4. Participant check: Both the connecting user AND the target user must
                      exist; the connecting user must actually BE one of
                      the two participants whose IDs form the room name.
5. Room isolation   : Room name is derived exclusively from the two sorted
                      participant IDs.  A user can only join a room in
                      which they are a named participant.
6. Input validation : Every incoming payload is validated for type,
                      presence of required keys, and safe value ranges
                      before acting on it.
7. Message length   : Messages are capped at MAX_MESSAGE_LENGTH chars
                      to guard against DoS.
8. Read-ID limit    : read_receipt payloads are capped at MAX_READ_IDS
                      entries to prevent abuse.
9. DB ownership     : mark_messages_read() filters by receiver=self.user
                      so a user can never mark another user's messages read.
10. Delete auth     : delete_message_db() verifies sender=self.user before
                      deleting — the DB layer enforces ownership even if
                      the WS payload is crafted.
"""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from .models import Message

logger = logging.getLogger(__name__)
User = get_user_model()

# ── Tunable limits ────────────────────────────────────────────────────────────
MAX_MESSAGE_LENGTH = 4_000   # characters
MAX_READ_IDS       = 500     # IDs per receipt payload


class ChatConsumer(AsyncWebsocketConsumer):

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    async def connect(self):
        """
        Gate every WS upgrade through multiple security checks.
        We call accept() first (required by the WS spec before sending a close
        frame) then immediately close with a 4xxx code on any violation.
        """
        self.user = self.scope['user']
        self.room_group_name = None   # set only after all checks pass

        # ── 1. Authentication ─────────────────────────────────────────────────
        if not self.user.is_authenticated:
            logger.warning('WS rejected: unauthenticated attempt')
            await self.close(code=4001)
            return

        # ── 2. Parse & validate the target user ID from the URL ───────────────
        raw_id = self.scope['url_route']['kwargs'].get('id', '')
        try:
            other_user_id = int(raw_id)
        except (ValueError, TypeError):
            logger.warning('WS rejected: invalid user-id "%s"', raw_id)
            await self.close(code=4002)
            return

        # ── 3. Block self-chat ────────────────────────────────────────────────
        if other_user_id == self.user.id:
            logger.warning('WS rejected: user %s tried to open self-chat', self.user.id)
            await self.close(code=4003)
            return

        # ── 4. Verify the target user exists ─────────────────────────────────
        if not await self.check_user_exists(other_user_id):
            logger.warning('WS rejected: target user %s does not exist', other_user_id)
            await self.close(code=4004)
            return

        # ── 5. Build room name & confirm participant membership ───────────────
        #   The room is named chat_<lower_id>_<higher_id>.
        #   Only the two users whose IDs appear in that name may join it.
        self.other_user_id = other_user_id
        user_ids = sorted([self.user.id, other_user_id])
        self.room_group_name = f'chat_{user_ids[0]}_{user_ids[1]}'

        # Double-check: the connecting user's ID must be in the pair.
        # (Redundant given the flow above, but explicit for defence-in-depth.)
        if self.user.id not in user_ids:
            logger.error(
                'WS rejected: user %s is not a participant of room %s',
                self.user.id, self.room_group_name
            )
            await self.close(code=4005)
            return

        # ── All checks passed — join the group ────────────────────────────────
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.set_user_online(self.user)
        await self.accept()

        logger.info(
            'WS connected: user=%s room=%s', self.user.username, self.room_group_name
        )

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.set_user_offline(self.user)

        logger.info(
            'WS disconnected: user=%s code=%s',
            getattr(self.user, 'username', '?'), close_code
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Receive (client → server)
    # ──────────────────────────────────────────────────────────────────────────

    async def receive(self, text_data):
        # ── Validate JSON ─────────────────────────────────────────────────────
        try:
            payload = json.loads(text_data)
        except (json.JSONDecodeError, ValueError):
            logger.warning('WS bad payload from %s: not valid JSON', self.user.username)
            return

        if not isinstance(payload, dict):
            return

        msg_type = payload.get('type', 'message')

        # ── Route by type ─────────────────────────────────────────────────────
        if msg_type == 'read_receipt':
            await self._handle_read_receipt(payload)
        elif msg_type == 'delete_message':
            await self._handle_delete_message(payload)
        else:
            await self._handle_chat_message(payload)

    # ──────────────────────────────────────────────────────────────────────────
    # Private payload handlers
    # ──────────────────────────────────────────────────────────────────────────

    async def _handle_chat_message(self, payload):
        """Validate and persist a chat message then broadcast it."""
        message_text = payload.get('message', '')

        # Type and presence check
        if not isinstance(message_text, str) or not message_text.strip():
            return

        # Length cap
        if len(message_text) > MAX_MESSAGE_LENGTH:
            logger.warning(
                'WS message from %s truncated (%d chars)',
                self.user.username, len(message_text)
            )
            message_text = message_text[:MAX_MESSAGE_LENGTH]

        message_id = await self.save_message(message_text.strip())

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text.strip(),
                'sender': self.user.username,
                'sender_id': self.user.id,
                'message_id': message_id,
            }
        )

    async def _handle_read_receipt(self, payload):
        """
        Mark specific messages as read.
        Only integers are accepted as IDs; the DB helper already filters by
        receiver=self.user so a user can only mark messages addressed to them.
        """
        raw_ids = payload.get('read_ids', [])

        # Must be a list
        if not isinstance(raw_ids, list):
            return

        # Cap to prevent abuse
        raw_ids = raw_ids[:MAX_READ_IDS]

        # Coerce to ints, silently drop anything that isn't
        read_ids = []
        for rid in raw_ids:
            try:
                read_ids.append(int(rid))
            except (TypeError, ValueError):
                pass

        if not read_ids:
            return

        await self.mark_messages_read(read_ids)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'messages_read',
                'read_ids': read_ids,
                'reader_id': self.user.id,
            }
        )

    async def _handle_delete_message(self, payload):
        """
        Delete a message by ID.
        Security: the DB helper enforces sender=self.user, so even a
        crafted payload cannot delete another user's message.
        """
        try:
            message_id = int(payload.get('message_id', 0))
        except (TypeError, ValueError):
            return

        if message_id <= 0:
            return

        # Returns True if deleted, False if not found / not owned
        deleted = await self.delete_message_db(message_id)

        if deleted:
            # Broadcast removal to both participants in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'deleted_by': self.user.id,
                }
            )
        else:
            # Silently log — someone tried to delete a msg they don't own
            logger.warning(
                'WS delete rejected: user=%s tried to delete msg=%s',
                self.user.username, message_id
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Group event handlers (channel layer → this WebSocket)
    # ──────────────────────────────────────────────────────────────────────────

    async def chat_message(self, event):
        """Deliver a chat message to the connected client."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'message_id': event['message_id'],
        }))

    async def messages_read(self, event):
        """Notify the sender that specific messages were read."""
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'read_ids': event['read_ids'],
            'reader_id': event['reader_id'],
        }))

    async def message_deleted(self, event):
        """Tell both participants to remove the deleted message bubble."""
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by'],
        }))

    # ──────────────────────────────────────────────────────────────────────────
    # Database helpers  (run in a thread pool via database_sync_to_async)
    # ──────────────────────────────────────────────────────────────────────────

    @database_sync_to_async
    def check_user_exists(self, user_id):
        return User.objects.filter(id=user_id).exists()

    @database_sync_to_async
    def save_message(self, message):
        """Persist a message and return its PK."""
        other_user = User.objects.get(id=self.other_user_id)
        msg = Message.objects.create(
            sender=self.user,
            receiver=other_user,
            message=message,
        )
        return msg.id

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        """
        Mark messages as read.
        The receiver=self.user filter ensures a user can ONLY mark messages
        that were addressed to them — never someone else's conversation.
        """
        Message.objects.filter(
            id__in=message_ids,
            receiver=self.user,
            is_read=False,
        ).update(is_read=True)

    @database_sync_to_async
    def delete_message_db(self, message_id):
        """
        Delete a message only if the current user is the sender.
        Returns True on success, False if the message was not found
        or the user does not own it.
        """
        deleted_count, _ = Message.objects.filter(
            id=message_id,
            sender=self.user,   # ← ownership enforced at DB level
        ).delete()
        return deleted_count > 0

    @database_sync_to_async
    def set_user_online(self, user):
        from django.utils import timezone
        User.objects.filter(pk=user.pk).update(
            is_online=True,
            last_seen=timezone.now(),
        )

    @database_sync_to_async
    def set_user_offline(self, user):
        from django.utils import timezone
        User.objects.filter(pk=user.pk).update(
            is_online=False,
            last_seen=timezone.now(),
        )