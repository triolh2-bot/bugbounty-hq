from pathlib import Path

from flask import Flask

from .auth import register_auth
from .config import build_config, validate_config
from .db import init_db
from .errors import register_error_handlers
from .routes.auth import auth_bp
from .routes.api import api_bp
from .routes.integrations import integrations_bp
from .routes.web import web_bp


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault(
            "Content-Security-Policy", app.config["SECURITY_HEADER_CSP"]
        )
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={app.config['SECURITY_HEADER_HSTS_SECONDS']}; includeSubDomains",
            )
        return response


def create_app(test_config=None):
    root_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(root_dir / "templates"),
        static_folder=None,
    )

    app.config.from_mapping(build_config(test_config))
    validate_config(app.config)

    register_auth(app)
    register_security_headers(app)
    register_error_handlers(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(integrations_bp, url_prefix="/webhook")

    init_db(app)

    return app
