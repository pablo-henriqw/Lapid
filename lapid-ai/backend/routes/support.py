"""API pública consumida pelo widget (autenticada pela chave do site)."""
from flask import Blueprint, current_app, jsonify, request

from ..api_common import ApiError, authenticate, register_api_hooks, throttle
from ..models import Complaint
from ..services.complaints import create_complaint
from ..validators import validate_complaint

bp = Blueprint("support", __name__, url_prefix="/api/support")
register_api_hooks(bp)


def _serialize(c: Complaint) -> dict:
    return {
        "protocol": c.protocol,
        "status": c.status,
        "status_label": c.status_label,
        "created_at": c.created_at.isoformat() + "Z",
    }


@bp.post("/complaints")
def create():
    site = authenticate()
    throttle("complaint", 5, 600)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "Corpo da requisição inválido.")

    cleaned, errors = validate_complaint(
        data, current_app.config["COMPLAINT_MIN_LEN"], current_app.config["COMPLAINT_MAX_LEN"]
    )
    if errors:
        return jsonify(error="validation_error", fields=errors), 422

    complaint = create_complaint(site, user_agent=request.headers.get("User-Agent"), **cleaned)
    return jsonify(_serialize(complaint)), 201


@bp.get("/complaints/<protocol>")
def status(protocol):
    site = authenticate()
    throttle("status", 60, 60)
    complaint = Complaint.query.filter_by(protocol=protocol[:24], site_id=site.id).first()
    if not complaint:
        raise ApiError(404, "not_found", "Protocolo não encontrado.")
    return jsonify(_serialize(complaint))
