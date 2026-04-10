from __future__ import annotations

from .local_retrieval_bridge import run_local_retrieval_pipeline


def query_ml(
    question: str,
    book_uid: str | None,
    requested_book_uid: str | None = None,
):
    """Compatibility wrapper for callers that still expect answer/confidence tuples."""
    result = run_local_retrieval_pipeline(
        query_text=question,
        book_ref=requested_book_uid or book_uid,
        save_artifacts=False,
    )

    if result.get("status") != "success":
        return result.get("error", "Local retrieval failed."), 0.0

    return result.get("answer", ""), result.get("confidence", 0.0)
