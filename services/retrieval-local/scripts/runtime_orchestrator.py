from __future__ import annotations
import user_query
import local_simplifier

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


logger = logging.getLogger(__name__)


def _normalize_query(query_text: Any) -> str:
    if not isinstance(query_text, str):
        return ""
    return query_text.strip()


def _normalize_book_ref(book_ref: Any) -> Optional[str]:
    if not isinstance(book_ref, str):
        return None
    cleaned = book_ref.strip()
    return cleaned or None


def run_local_retrieval_pipeline(
    *,
    query_text: Any,
    book_ref: Any,
    query_id: Optional[str] = None,
    request_metadata: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    save_artifacts: bool = True,
) -> Dict[str, Any]:
    """Run the live local retrieval pipeline for backend API requests."""
    normalized_query = _normalize_query(query_text)
    normalized_book_ref = _normalize_book_ref(book_ref)

    if not normalized_query:
        return {
            "status": "error",
            "error": "malformed input: query_text must be a non-empty string",
            "answer": None,
            "confidence": 0.0,
            "query_id": query_id,
            "book": normalized_book_ref,
            "source_path": None,
        }

    if not normalized_book_ref:
        return {
            "status": "error",
            "error": "missing book selection",
            "answer": None,
            "confidence": 0.0,
            "query_id": query_id,
            "book": None,
            "source_path": None,
        }

    retrieval_result = user_query.run_retrieval_request(
        normalized_query,
        normalized_book_ref,
        query_id=query_id,
        save_output_file=save_artifacts,
    )

    if retrieval_result.get("status") != "success":
        error_message = retrieval_result.get("error", "retrieval failed")
        logger.error("Local retrieval failed: %s", error_message)
        return {
            "status": "error",
            "error": error_message,
            "answer": None,
            "confidence": retrieval_result.get("confidence", 0.0),
            "query_id": retrieval_result.get("query_id", query_id),
            "book": retrieval_result.get("book", normalized_book_ref),
            "source_path": retrieval_result.get("retrieval_source_path"),
            "retrieval": retrieval_result,
            "request_metadata": request_metadata or {},
        }

    simplification_result = local_simplifier.simplify_retrieval_payload(
        retrieval_result,
        api_key=api_key,
        save_output_file=save_artifacts,
    )

    if simplification_result.get("status") != "success":
        error_message = simplification_result.get(
            "error", "simplification failed")
        logger.error("Local simplification failed: %s", error_message)
        return {
            "status": "error",
            "error": error_message,
            "answer": None,
            "confidence": retrieval_result.get("confidence", 0.0),
            "query_id": retrieval_result.get("query_id", query_id),
            "book": retrieval_result.get("book", normalized_book_ref),
            "source_path": simplification_result.get("source_path"),
            "retrieval": retrieval_result,
            "request_metadata": request_metadata or {},
        }

    return {
        "status": "success",
        "answer": simplification_result.get("answer", ""),
        "confidence": simplification_result.get(
            "confidence", retrieval_result.get("confidence", 0.0)
        ),
        "query_id": simplification_result.get("query_id", retrieval_result.get("query_id", query_id)),
        "book": simplification_result.get("book", retrieval_result.get("book", normalized_book_ref)),
        "source_path": simplification_result.get("source_path"),
        "retrieval": retrieval_result,
        "request_metadata": request_metadata or {},
    }
