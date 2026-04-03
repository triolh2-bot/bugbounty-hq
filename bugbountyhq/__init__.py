from pathlib import Path

from flask import Flask

from .config import get_config
from .db import init_db
from .errors import register_error_handlers
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

    app.config.from_object(get_config())
    if test_config:
        app.config.update(test_config)

    register_error_handlers(app)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(integrations_bp, url_prefix="/webhook")

    init_db(app)

    return app
