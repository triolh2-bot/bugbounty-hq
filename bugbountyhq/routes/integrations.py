from flask import Blueprint, current_app, jsonify, request

from ..security import enforce_rate_limit, log_security_event


integrations_bp = Blueprint("integrations", __name__)


@integrations_bp.route("/hackerone", methods=["POST"])
def webhook_hackerone():
    enforce_rate_limit(
        "webhook_hackerone",
        current_app.config["RATE_LIMIT_WEBHOOK_REQUESTS"],
        current_app.config["RATE_LIMIT_WINDOW_SECONDS"],
    )
    _ = request.json
    log_security_event("webhook_hackerone", outcome="received")
    return jsonify({"received": True})


@integrations_bp.route("/bugcrowd", methods=["POST"])
def webhook_bugcrowd():
    enforce_rate_limit(
        "webhook_bugcrowd",
        current_app.config["RATE_LIMIT_WEBHOOK_REQUESTS"],
        current_app.config["RATE_LIMIT_WINDOW_SECONDS"],
    )
    _ = request.json
    log_security_event("webhook_bugcrowd", outcome="received")
    return jsonify({"received": True})
