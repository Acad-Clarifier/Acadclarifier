from flask import Blueprint, jsonify

api_routes = Blueprint("api_routes", __name__)


@api_routes.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "AcadClarifier Backend"
    })
