import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SECRET_KEY_IS_EPHEMERAL = not os.environ.get("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'instance' / 'lapid.db').as_posix()}"
    )

    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "America/Sao_Paulo")
    ENABLE_DEMO = _bool("ENABLE_DEMO", False)
    PROXY_COUNT = int(os.environ.get("PROXY_COUNT", "0"))

    # Etapa 2: monitoramento
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    SENTRY_WEBHOOK_SECRET = os.environ.get("SENTRY_WEBHOOK_SECRET", "")
    ALERT_WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL", "")  # Slack/Discord/qualquer POST JSON
    ERROR_ALERT_THRESHOLDS = (5, 25, 100, 500)  # alerta quando um erro atinge estas ocorrências
    MAX_EVENTS_PER_GROUP = 50

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    MAX_CONTENT_LENGTH = 32 * 1024  # 32 KB por requisição
    COMPLAINT_MIN_LEN = 10
    COMPLAINT_MAX_LEN = 2000
