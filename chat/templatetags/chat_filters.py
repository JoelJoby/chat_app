from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def last_seen_display(last_seen):
    """
    Returns a human-readable 'last seen' string relative to now.

    Examples:
        - "Just now"            (< 60 seconds ago)
        - "2 minutes ago"       (< 60 minutes ago)
        - "3 hours ago"         (< 24 hours ago)
        - "Yesterday at 3:45 PM"
        - "Feb 18 at 11:00 AM"
    """
    if not last_seen:
        return "Unknown"

    now = timezone.now()
    diff = now - last_seen
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 172800:
        # Yesterday
        local_dt = last_seen.astimezone(timezone.get_current_timezone())
        time_str = local_dt.strftime("%I:%M %p").lstrip("0")
        return f"Yesterday at {time_str}"
    else:
        local_dt = last_seen.astimezone(timezone.get_current_timezone())
        time_str = local_dt.strftime("%b %d at %I:%M %p").lstrip("0")
        return time_str
