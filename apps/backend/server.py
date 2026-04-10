from flask import Flask
from dotenv import load_dotenv
from pathlib import Path
import sys

from flask_cors import CORS

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from .config import Config
    from .db import db, migrate
    from .models import Book  # noqa: F401 - imported for metadata registration
    from .routes import api_routes
except ImportError:
    from apps.backend.config import Config
    from apps.backend.db import db, migrate
    from apps.backend.models import Book  # noqa: F401 - imported for metadata registration
    from apps.backend.routes import api_routes


# Always load backend-local .env regardless of where flask command is launched.
load_dotenv(Path(__file__).resolve().parent / ".env")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)

    # Register all API routes
    app.register_blueprint(api_routes)

    # NOTE: Recommender is lazy-loaded on first request to avoid deployment timeout.
    # Heavy models (torch, sentence-transformers) load only when needed.

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True,
            use_reloader=False, threaded=True)
