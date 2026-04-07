"""Serve the static frontend without Streamlit.

Run with:
    python app.py
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os


def run() -> None:
    frontend_dir = Path(__file__).resolve().parent / "apps" / "frontend"
    os.chdir(frontend_dir)

    port = int(os.environ.get("FRONTEND_PORT", "8501"))
    server = ThreadingHTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)

    print(f"Static frontend running at http://localhost:{port}")
    print(f"Serving directory: {frontend_dir}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFrontend server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
