"""Peças compartilhadas pelas APIs públicas (widget): autenticação por chave, CORS e limites."""
from flask import jsonify, request

from .models import Site
from .security import client_ip, limiter, origin_allowed, origin_is_known


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def authenticate() -> Site:
    key = request.headers.get("X-Lapid-Key", "").strip()
    if not key:
        raise ApiError(401, "missing_key", "Chave do site ausente.")
    site = Site.query.filter_by(api_key=key, is_active=True).first()
    if not site:
        raise ApiError(401, "invalid_key", "Chave do site inválida.")
    origin = request.headers.get("Origin")
    if origin and not origin_allowed(site, origin):
        raise ApiError(403, "origin_not_allowed", "Este site não está autorizado a usar esta chave.")
    return site


def throttle(bucket: str, limit: int, window: int, scope: str | None = None):
    if not limiter().allow(f"{bucket}:{scope or client_ip()}", limit, window):
        raise ApiError(429, "rate_limited", "Muitas solicitações. Tente novamente em alguns minutos.")


def _cors(resp):
    origin = request.headers.get("Origin")
    if origin and origin_is_known(origin):
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Lapid-Key"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Max-Age"] = "600"
    return resp


def register_api_hooks(bp):
    @bp.errorhandler(ApiError)
    def _api_error(e):
        return jsonify(error=e.code, message=e.message), e.status

    bp.after_request(_cors)
