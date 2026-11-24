import hashlib
import hmac
import json
import re

import pytest

from backend.extensions import db
from backend.models import ErrorEvent, ErrorGroup
from backend.services import alerts

from .conftest import headers
from .test_admin import _csrf, _login

ERR = {"type": "TypeError", "message": "Cannot read properties of undefined (reading 'id')",
       "stack": "TypeError: x\n    at cart (https://loja.com/app.js?v=3:10:5)", "page_url": "https://loja.com/carrinho"}


@pytest.fixture()
def sent(monkeypatch):
    msgs = []
    monkeypatch.setattr(alerts, "notify", lambda text: msgs.append(text))
    return msgs


def post_err(client, payload=None, **kw):
    return client.post("/api/monitor/errors", json=payload or ERR, headers=kw.get("h", headers()))


def test_frontend_error_is_grouped(client, sent):
    assert post_err(client).status_code == 202
    assert post_err(client).status_code == 202
    assert ErrorGroup.query.count() == 1
    g = ErrorGroup.query.first()
    assert g.count == 2 and g.source == "frontend" and g.status == "open"
    assert ErrorEvent.query.count() == 2
    assert len(sent) == 1 and "Novo erro" in sent[0]


def test_numbers_in_message_do_not_split_groups(client):
    post_err(client, {**ERR, "message": "Falha ao carregar item 12"})
    post_err(client, {**ERR, "message": "Falha ao carregar item 9876"})
    assert ErrorGroup.query.count() == 1


def test_different_errors_make_different_groups(client):
    post_err(client)
    post_err(client, {**ERR, "message": "Outra falha", "stack": "Error\n    at other (https://loja.com/x.js:1:1)"})
    assert ErrorGroup.query.count() == 2


def test_recurrence_alert_at_threshold(client, sent):
    for _ in range(5):
        post_err(client)
    assert len(sent) == 2 and "recorrente" in sent[1]


def test_resolved_error_reopens(client, sent):
    post_err(client)
    ErrorGroup.query.first().status = "resolved"
    db.session.commit()
    post_err(client)
    assert ErrorGroup.query.first().status == "open"
    assert any("voltou" in m for m in sent)


def test_ingest_requires_valid_key_and_origin(client):
    assert client.post("/api/monitor/errors", json=ERR).status_code == 401
    assert post_err(client, h=headers(origin="https://evil.com")).status_code == 403
    assert ErrorGroup.query.count() == 0


def test_ingest_validation(client):
    assert post_err(client, {"message": ""}).status_code == 422
    assert client.post("/api/monitor/errors", data="x", headers=headers()).status_code == 400


def test_invalid_page_url_is_dropped_not_stored(client):
    post_err(client, {**ERR, "page_url": "javascript:alert(1)"})
    assert ErrorGroup.query.first().last_page_url is None


def test_backend_exception_is_captured(app, sent):
    app.add_url_rule("/boom", "boom", lambda: 1 / 0)
    c = app.test_client()
    r = c.get("/boom")
    assert r.status_code == 500
    g = ErrorGroup.query.first()
    assert g.source == "backend" and g.error_type == "ZeroDivisionError" and g.site_id is None
    assert "ZeroDivisionError" in g.sample_stack


def test_admin_error_pages_and_status(client):
    post_err(client)
    _login(client)
    page = client.get("/admin/errors")
    assert page.status_code == 200 and "Cannot read properties" in page.get_data(as_text=True)
    detail = client.get("/admin/errors/1")
    html = detail.get_data(as_text=True)
    assert "TypeError" in html and "app.js" in html
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert client.post("/admin/errors/1/status", data={"status": "ignored"}).status_code == 400  # sem CSRF
    assert client.post("/admin/errors/1/status", data={"status": "ignored", "csrf_token": token}).status_code == 302
    assert ErrorGroup.query.first().status == "ignored"
    assert "Nenhum erro em aberto" in client.get("/admin/errors").get_data(as_text=True)


def test_admin_errors_require_login(client):
    for path in ("/admin/errors", "/admin/errors/1"):
        assert client.get(path).status_code == 302


def test_stack_is_escaped(client):
    post_err(client, {**ERR, "stack": "<img src=x onerror=alert(1)>"})
    _login(client)
    assert "<img src=x" not in client.get("/admin/errors/1").get_data(as_text=True)


def test_overview_and_sites_render_with_data(client):
    post_err(client)
    client.post("/api/support/complaints", headers=headers(),
                json={"description": "Erro ao finalizar a compra.", "page_url": "https://loja.com/c"})
    _login(client)
    html = client.get("/admin/").get_data(as_text=True)
    assert "dial-bar" in html and "Cannot read properties" in html
    assert "1 erro em aberto" in client.get("/admin/sites").get_data(as_text=True)


# ---------- Sentry ----------
def _signed(app, body: dict, secret="s3cret"):
    raw = json.dumps(body).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return raw, {"Sentry-Hook-Signature": sig, "Content-Type": "application/json"}


def test_sentry_disabled_without_secret(client):
    assert client.post("/api/monitor/sentry", json={}).status_code == 404


def test_sentry_webhook_signature_and_dedup(app, client, sent):
    app.config["SENTRY_WEBHOOK_SECRET"] = "s3cret"
    body = {"action": "created", "data": {"issue": {"id": "77", "title": "KeyError: 'user'", "count": "4",
                                                    "permalink": "https://sentry.io/organizations/x/issues/77/"}}}
    raw, hdrs = _signed(app, body)
    assert client.post("/api/monitor/sentry", data=raw, headers={**hdrs, "Sentry-Hook-Signature": "bad"}).status_code == 401
    assert client.post("/api/monitor/sentry", data=raw, headers=hdrs).status_code == 200
    assert client.post("/api/monitor/sentry", data=raw, headers=hdrs).status_code == 200
    g = ErrorGroup.query.one()
    assert g.source == "sentry" and g.count == 4 and g.external_url.startswith("https://sentry.io/")


def test_sentry_rejects_non_http_permalink(app, client):
    app.config["SENTRY_WEBHOOK_SECRET"] = "s3cret"
    raw, hdrs = _signed(app, {"data": {"issue": {"id": "1", "title": "X", "permalink": "javascript:alert(1)"}}})
    client.post("/api/monitor/sentry", data=raw, headers=hdrs)
    assert ErrorGroup.query.one().external_url is None
