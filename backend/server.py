from flask import Flask
from routes import api_routes


def create_app():
    app = Flask(__name__)

    # Register all API routes
    app.register_blueprint(api_routes)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
