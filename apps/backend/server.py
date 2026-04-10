from flask import Flask
from dotenv import load_dotenv
from pathlib import Path
import sys
import threading

from flask_cors import CORS

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from .config import Config
    from .db import db, migrate
    from .models import Book  # noqa: F401 - imported for metadata registration
    from .recommend_client import get_recommender
    from .routes import api_routes
except ImportError:
    from apps.backend.config import Config
    from apps.backend.db import db, migrate
    from apps.backend.models import Book  # noqa: F401 - imported for metadata registration
    from apps.backend.recommend_client import get_recommender
    from apps.backend.routes import api_routes


# Always load backend-local .env regardless of where flask command is launched.
load_dotenv(Path(__file__).resolve().parent / ".env")


def _load_recommender_background(chroma_path):
    """Load the recommender model in a background thread to avoid deployment timeout."""
    try:
        get_recommender(chroma_path)
    except Exception as exc:
        # Silently fail - first request will trigger lazy-load if needed
        pass


def create_app():
    app = Flask(__name__)
    apLoad recommender in background to avoid blocking startup but have it ready quickly.
    # This runs after app is healthy (not part of the critical 230s deployment timeout).
    chroma_path = app.config.get("BOOK_RECOMMENDER_CHROMA_PATH")
    bg_thread = threading.Thread(
        target=_load_recommender_background,
        args=(chroma_path,),
        daemon=True,
        name="BookRecommenderLoader"
    )
    bg_thread.start()

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
