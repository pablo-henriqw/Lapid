"""Ingestão de erros: widget (navegador) e webhook do Sentry."""
import hashlib
import hmac
from urllib.parse import urlparse

from flask import Blueprint, abort, current_app, jsonify, request

from ..api_common import ApiError, authenticate, register_api_hooks, throttle
from ..models import Site
from ..security import limiter
from ..services.errors import record_error
from ..validators import clean_text

bp = Blueprint("monitor", __name__, url_prefix="/api/monitor")
register_api_hooks(bp)


def _http_url(value, max_len=2048):
    value = clean_text(value, max_len)
    p = urlparse(value)
    return value if p.scheme in ("http", "https") and p.netloc else None


@bp.post("/errors")
def frontend_error():
    site = authenticate()
    throttle("err", 30, 60)
    if not limiter().allow(f"errsite:{site.id}", 600, 3600):  # teto por site: protege contra inundação
        raise ApiError(429, "rate_limited", "Limite de erros por hora atingido.")

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "Corpo da requisição inválido.")
    message = clean_text(data.get("message"), 500)
    if not message:
        return jsonify(error="validation_error", fields={"message": "Mensagem obrigatória."}), 422

    record_error(
        site, "frontend",
        clean_text(data.get("type"), 120) or "Error",
        message,
        stack=clean_text(data.get("stack"), 6000),
        page_url=_http_url(data.get("page_url")),
        user_agent=request.headers.get("User-Agent"),
    )
    return jsonify(ok=True), 202


@bp.post("/sentry")
def sentry_webhook():
    """Recebe issues do Sentry (Internal Integration). Assinatura HMAC-SHA256 obrigatória."""
    secret = current_app.config["SENTRY_WEBHOOK_SECRET"]
    if not secret:
        abort(404)
    throttle("sentry", 120, 60)
    expected = hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get("Sentry-Hook-Signature", ""), expected):
        return jsonify(error="invalid_signature"), 401

    payload = request.get_json(silent=True) or {}
    data = payload.get("data") or {}
    issue = data.get("issue") or data.get("error") or {}
    title = clean_text(issue.get("title") or issue.get("message"), 500)
    if not title:
        return jsonify(ok=True, ignored=True), 200

    site = db_site(request.args.get("site_id", type=int))
    issue_id = str(issue.get("id") or issue.get("issue_id") or title)
    count = issue.get("count")
    record_error(
        site, "sentry", "SentryIssue", title,
        external_url=_http_url(issue.get("permalink") or issue.get("web_url"), 500),
        identity=f"sentry:{issue_id}",
        set_count=int(count) if str(count).isdigit() else None,
    )
    return jsonify(ok=True), 200


def db_site(site_id):
    return Site.query.get(site_id) if site_id else None
