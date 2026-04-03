import logging

from flask import jsonify, request


logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not Found", "status": 404}), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error("500: %s", request.path)
        return jsonify({"error": "Internal Server Error", "status": 500}), 500

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad Request", "status": 400}), 400

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden", "status": 403}), 403

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized", "status": 401}), 401

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error("Unhandled: %s", str(e))
        return jsonify({"error": "Internal Server Error", "status": 500}), 500
