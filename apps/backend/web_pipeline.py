from __future__ import annotations

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve(
).parents[2] / "services" / "retrieval-web" / "scripts"


def _ensure_script_path() -> None:
    script_path = str(SCRIPT_DIR)
    if script_path not in sys.path:
        sys.path.insert(0, script_path)


def run_web_pipeline(query: str) -> dict:
    if not query or not query.strip():
        raise ValueError("query is required")

    _ensure_script_path()

    import pipeline  # type: ignore

    final_output_path = pipeline.run_pipeline(query=query.strip())
    final_path = Path(final_output_path)

    if not final_path.exists():
        raise FileNotFoundError(f"Final output not found: {final_output_path}")

    answer_text = final_path.read_text(encoding="utf-8").strip()

    return {
        "answer": answer_text,
        "confidence": None,
        "final_output_path": str(final_path),
        "mode": "web",
    }
