from datetime import timezone
from zoneinfo import ZoneInfo

from flask import current_app

from .models import utcnow


def localtime(value, fmt="%d/%m/%Y %H:%M"):
    if not value:
        return "—"
    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    return value.replace(tzinfo=timezone.utc).astimezone(tz).strftime(fmt)


def ago(value):
    if not value:
        return "—"
    s = int((utcnow() - value).total_seconds())
    if s < 60:
        return "agora"
    if s < 3600:
        return f"há {s // 60} min"
    if s < 86400:
        return f"há {s // 3600} h"
    if s < 86400 * 30:
        return f"há {s // 86400} d"
    return localtime(value, "%d/%m/%Y")


def register(app):
    app.jinja_env.filters["localtime"] = localtime
    app.jinja_env.filters["ago"] = ago
