import logging
import traceback
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from . import cli, filters
from .config import BASE_DIR, Config
from .extensions import db
from .security import RateLimiter, csrf_token


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "frontend" / "templates"),
        static_folder=str(BASE_DIR / "frontend" / "static"),
        instance_path=str(BASE_DIR / "instance"),
    )
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    Path(app.instance_path).mkdir(exist_ok=True)

    if app.config.get("SECRET_KEY_IS_EPHEMERAL") and not app.testing:
        logging.getLogger(__name__).warning(
            "SECRET_KEY não definida: sessões serão invalidadas a cada reinício. Defina no .env."
        )
    if app.config["PROXY_COUNT"] > 0:
        n = app.config["PROXY_COUNT"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n, x_proto=n, x_host=n)

    _init_sentry(app)
    db.init_app(app)
    app.extensions["limiter"] = RateLimiter()
    app.jinja_env.globals["csrf_token"] = csrf_token
    filters.register(app)
    cli.register(app)

    from .routes import admin, monitor, public, support

    app.register_blueprint(public.bp)
    app.register_blueprint(support.bp)
    app.register_blueprint(monitor.bp)
    app.register_blueprint(admin.bp)

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/admin"):
            resp.headers.setdefault("X-Frame-Options", "DENY")
        return resp

    @app.errorhandler(413)
    def _too_large(_):
        return jsonify(error="payload_too_large", message="Requisição grande demais."), 413

    @app.errorhandler(Exception)
    def _unhandled(e):
        """Captura falhas do próprio servidor: registra no monitor (e no Sentry, se ativo)."""
        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Erro não tratado")
        try:
            db.session.rollback()
            from .services.errors import record_error

            record_error(
                None, "backend", type(e).__name__, str(e), stack=traceback.format_exc(),
                page_url=request.base_url, user_agent=request.headers.get("User-Agent"),
            )
        except Exception:  # noqa: BLE001 - o registro nunca pode piorar a falha original
            db.session.rollback()
            app.logger.exception("Falha ao registrar o erro")
        try:
            import sentry_sdk

            sentry_sdk.capture_exception(e)
        except Exception:  # noqa: BLE001
            pass
        if request.path.startswith("/api/"):
            return jsonify(error="server_error", message="Erro interno."), 500
        return render_template("error.html"), 500

    with app.app_context():
        db.create_all()  # Etapa 1: sem migrações. Alembic entra quando migrarmos para PostgreSQL.

    return app


def _init_sentry(app: Flask) -> None:
    dsn = app.config.get("SENTRY_DSN")
    if not dsn or app.testing:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, send_default_pii=False, traces_sample_rate=0.0)
    except ImportError:
        logging.getLogger(__name__).warning("SENTRY_DSN definido, mas sentry-sdk não está instalado.")
