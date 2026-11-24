"""Alertas administrativos externos (webhook compatível com Slack e Discord)."""
import json
import logging
import threading
import urllib.request
from urllib.parse import urlparse

from flask import current_app, has_request_context, request

log = logging.getLogger(__name__)


def dashboard_link(path: str) -> str:
    return request.url_root.rstrip("/") + path if has_request_context() else path


def notify(text: str) -> None:
    """Envia em segundo plano; nunca bloqueia nem derruba a requisição."""
    url = current_app.config.get("ALERT_WEBHOOK_URL", "")
    if not url or urlparse(url).scheme not in ("http", "https"):
        return

    def _send():
        try:
            body = json.dumps({"text": text, "content": text}).encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=5).read()
        except Exception:  # noqa: BLE001 - alerta é best-effort
            log.warning("Falha ao enviar alerta para o webhook.", exc_info=True)

    threading.Thread(target=_send, daemon=True).start()
