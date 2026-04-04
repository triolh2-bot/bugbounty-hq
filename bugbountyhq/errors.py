import logging

from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .validation import ValidationError


logger = logging.getLogger(__name__)


def _prefers_json() -> bool:
    return request.path.startswith("/api/") or request.path.startswith("/webhook/")


def _error_response(status_code: int, title: str, message: str):
    if _prefers_json():
        return jsonify({"error": title, "message": message, "status": status_code}), status_code
    return (
        render_template(
            "error.html",
            status_code=status_code,
            title=title,
            message=message,
        ),
        status_code,
    )


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return _error_response(404, "Not Found", "The requested resource was not found.")

    @app.errorhandler(500)
    def internal_error(e):
        logger.error("500: %s", request.path)
        return _error_response(500, "Internal Server Error", "Something went wrong.")

    @app.errorhandler(400)
    def bad_request(e):
        return _error_response(400, "Bad Request", "The request could not be processed.")

    @app.errorhandler(403)
    def forbidden(e):
        return _error_response(403, "Forbidden", "You do not have access to this resource.")

    @app.errorhandler(401)
    def unauthorized(e):
        return _error_response(401, "Unauthorized", "Authentication is required.")

    @app.errorhandler(ValidationError)
    def validation_error(e: ValidationError):
        return _error_response(e.status_code, "Bad Request", e.message)

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return _error_response(e.code or 500, e.name, e.description)
        logger.error("Unhandled: %s", str(e))
        return _error_response(500, "Internal Server Error", "Something went wrong.")
