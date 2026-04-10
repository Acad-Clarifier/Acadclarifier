"""WSGI entrypoint for production servers (Gunicorn/Render)."""

from apps.backend.server import create_app

app = create_app()
