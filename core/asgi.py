import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

import chat.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = ProtocolTypeRouter({
    # Standard HTTP traffic
    "http": get_asgi_application(),

    # WebSocket traffic
    # AllowedHostsOriginValidator  → rejects connections whose Origin header
    #   does not match ALLOWED_HOSTS (prevents Cross-Site WebSocket Hijacking).
    # AuthMiddlewareStack          → populates scope['user'] from the Django
    #   session cookie so the consumer can call self.scope['user'].
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
            )
        )
    ),
})
