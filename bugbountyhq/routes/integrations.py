from flask import Blueprint, jsonify, request


integrations_bp = Blueprint("integrations", __name__)


@integrations_bp.route("/hackerone", methods=["POST"])
def webhook_hackerone():
    _ = request.json
    return jsonify({"received": True})


@integrations_bp.route("/bugcrowd", methods=["POST"])
def webhook_bugcrowd():
    _ = request.json
    return jsonify({"received": True})
