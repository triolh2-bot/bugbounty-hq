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
    register_error_handlers(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(integrations_bp, url_prefix="/webhook")

    init_db(app)

    return app
