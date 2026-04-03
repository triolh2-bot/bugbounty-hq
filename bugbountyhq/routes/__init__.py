from .auth import auth_bp
from .api import api_bp
from .integrations import integrations_bp
from .web import web_bp

__all__ = ["api_bp", "auth_bp", "integrations_bp", "web_bp"]
