"""Registro, agrupamento e recorrência de erros (frontend, backend e Sentry)."""
import hashlib
import re

from flask import current_app
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import ERROR_SOURCES, ErrorEvent, ErrorGroup, utcnow
from . import alerts
from .activity import log_activity

_HEX = re.compile(r"\b[0-9a-f]{8,}\b", re.I)
_NUM = re.compile(r"\d+")


def _normalize(text: str) -> str:
    return _NUM.sub("N", _HEX.sub("H", text or ""))


def _key_frame(stack: str, source: str) -> str:
    """Frame mais relevante, sem números de linha/coluna nem query string."""
    lines = [l.strip() for l in (stack or "").splitlines() if l.strip()]
    if source == "backend":
        frames = [l for l in lines if l.startswith("File ")]
        frame = frames[-1] if frames else ""
    else:
        frames = [l for l in lines if l.startswith("at ") or "@" in l]
        frame = frames[0] if frames else ""
    return _NUM.sub("N", re.sub(r"[?#][^\s)]*", "", frame))[:200]


def make_fingerprint(site_id, source, error_type, message, stack, identity=None) -> str:
    if identity:
        raw = f"{site_id}|{source}|{identity}"
    else:
        raw = f"{site_id}|{source}|{error_type}|{_normalize(message)}|{_key_frame(stack, source)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def record_error(site, source, error_type, message, stack=None, page_url=None, user_agent=None,
                 external_url=None, identity=None, set_count=None):
    """Registra uma ocorrência. Retorna (grupo, criado). Dispara alertas em: novo, regressão e recorrência."""
    cfg = current_app.config
    error_type = (error_type or "Error")[:120]
    message = (message or error_type)[:500]
    stack = (stack or "")[:6000]
    site_id = site.id if site else None
    site_name = site.name if site else "Lapid.ai"
    fp = make_fingerprint(site_id, source, error_type, message, stack, identity)
    now = utcnow()

    group = ErrorGroup.query.filter_by(fingerprint=fp).first()
    created = False
    if group is None:
        group = ErrorGroup(
            fingerprint=fp, site_id=site_id, source=source, error_type=error_type, message=message,
            count=0, first_seen=now, last_seen=now,
        )
        db.session.add(group)
        try:
            db.session.flush()
            created = True
        except IntegrityError:  # duas ocorrências simultâneas criaram o mesmo grupo
            db.session.rollback()
            group = ErrorGroup.query.filter_by(fingerprint=fp).first()
            if group is None:
                raise

    regressed = group.status == "resolved"
    if regressed:
        group.status = "open"
    group.count = max(group.count, set_count) if set_count else group.count + 1
    group.last_seen = now
    if page_url:
        group.last_page_url = page_url[:2048]
    if stack and not group.sample_stack:
        group.sample_stack = stack
    if external_url:
        group.external_url = external_url[:500]
    db.session.add(ErrorEvent(group_id=group.id, page_url=page_url, user_agent=(user_agent or "")[:300] or None, stack=stack or None))

    label = ERROR_SOURCES.get(source, source)
    summary = f"{label} em {site_name}: {message[:140]}"
    alert = None
    if created:
        log_activity("error.new", "error", group.id, summary, actor="monitor")
        alert = "Novo erro"
    elif regressed:
        log_activity("error.regressed", "error", group.id, f"Voltou a ocorrer. {summary}", actor="monitor")
        alert = "Erro resolvido voltou a ocorrer"
    elif group.count in cfg["ERROR_ALERT_THRESHOLDS"] and group.status == "open":
        log_activity("error.recurring", "error", group.id, f"{group.count} ocorrências. {summary}", actor="monitor")
        alert = f"Erro recorrente ({group.count} ocorrências)"
    db.session.commit()

    if alert:
        alerts.notify(f"[Lapid.ai] {alert}\n{summary}\n{alerts.dashboard_link(f'/admin/errors/{group.id}')}")
    _prune(group.id, cfg["MAX_EVENTS_PER_GROUP"])
    return group, created


def _prune(group_id: int, keep: int) -> None:
    old = [r[0] for r in db.session.query(ErrorEvent.id).filter_by(group_id=group_id)
           .order_by(ErrorEvent.id.desc()).offset(keep).all()]
    if old:
        ErrorEvent.query.filter(ErrorEvent.id.in_(old)).delete(synchronize_session=False)
        db.session.commit()
