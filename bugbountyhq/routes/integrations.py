from flask import Blueprint, current_app, jsonify

from ..integration_webhooks import verify_incoming_webhook
from ..security import enforce_rate_limit


integrations_bp = Blueprint("integrations", __name__)


@integrations_bp.route("/hackerone", methods=["POST"])
def webhook_hackerone():
    enforce_rate_limit(
        "webhook_hackerone",
        current_app.config["RATE_LIMIT_WEBHOOK_REQUESTS"],
        current_app.config["RATE_LIMIT_WINDOW_SECONDS"],
    )
    result = verify_incoming_webhook("hackerone")
    return jsonify(result), 202


@integrations_bp.route("/bugcrowd", methods=["POST"])
def webhook_bugcrowd():
    enforce_rate_limit(
        "webhook_bugcrowd",
        current_app.config["RATE_LIMIT_WEBHOOK_REQUESTS"],
        current_app.config["RATE_LIMIT_WINDOW_SECONDS"],
    )
    result = verify_incoming_webhook("bugcrowd")
    return jsonify(result), 202


@integrations_bp.route("/<provider>", methods=["POST"])
def webhook_provider(provider: str):
    enforce_rate_limit(
        f"webhook_{provider}",
        current_app.config["RATE_LIMIT_WEBHOOK_REQUESTS"],
        current_app.config["RATE_LIMIT_WINDOW_SECONDS"],
    )
    result = verify_incoming_webhook(provider)
    return jsonify(result), 202
