from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from threading import Lock
from typing import Any, Dict
from urllib.parse import quote_plus

try:
    from . import sqlite_compat  # noqa: F401
except ImportError:
    import sqlite_compat  # type: ignore # noqa: F401


ALLOWED_FILTERS = {"all", "open_access", "subscription"}
_LOAD_LOCK = Lock()
_SEARCH_PAPERS = None

_RETRIEVAL_JOURNAL_DIR = (
    Path(__file__).resolve().parents[2] / "services" / "retrieval-journal"
)
_RETRIEVAL_JOURNAL_SERVICES_FILE = _RETRIEVAL_JOURNAL_DIR / "services.py"


def _build_source_url(item: Dict[str, Any]) -> str:
    pdf = (item.get("pdf") or "").strip()
    if pdf:
        return pdf

    doi_or_id = (item.get("doi") or "").strip()
    if doi_or_id:
        if doi_or_id.startswith("http://") or doi_or_id.startswith("https://"):
            return doi_or_id

        if doi_or_id.startswith("10."):
            return f"https://doi.org/{quote_plus(doi_or_id)}"

        # Semantic Scholar paperId fallback.
        return f"https://www.semanticscholar.org/paper/{quote_plus(doi_or_id)}"

    title = (item.get("title") or "").strip()
    if title:
        return f"https://scholar.google.com/scholar?q={quote_plus(title)}"

    return ""


class JournalServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _load_search_papers_callable():
    global _SEARCH_PAPERS

    if _SEARCH_PAPERS is not None:
        return _SEARCH_PAPERS

    with _LOAD_LOCK:
        if _SEARCH_PAPERS is not None:
            return _SEARCH_PAPERS

        if not _RETRIEVAL_JOURNAL_SERVICES_FILE.exists():
            raise FileNotFoundError(
                f"Retrieval journal services module not found: {_RETRIEVAL_JOURNAL_SERVICES_FILE}"
            )

        journal_dir = str(_RETRIEVAL_JOURNAL_DIR)
        if journal_dir not in sys.path:
            sys.path.insert(0, journal_dir)

        module_name = "_acadclarifier_retrieval_journal_services"
        spec = importlib.util.spec_from_file_location(
            module_name, _RETRIEVAL_JOURNAL_SERVICES_FILE
        )
        if spec is None or spec.loader is None:
            raise ImportError("Failed to load retrieval journal services spec")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        search_callable = getattr(module, "search_papers", None)
        if not callable(search_callable):
            raise AttributeError(
                "search_papers callable not found in retrieval-journal/services.py")

        _SEARCH_PAPERS = search_callable
        return _SEARCH_PAPERS


def _run_search_papers(query: str, filter_type: str, timeout_seconds: int) -> Dict[str, Any]:
    search_papers = _load_search_papers_callable()

    try:
        return asyncio.run(
            asyncio.wait_for(
                search_papers(query=query, filter_type=filter_type),
                timeout=timeout_seconds,
            )
        )
    except asyncio.TimeoutError as exc:
        raise TimeoutError("Journal service timed out") from exc
    except RuntimeError as exc:
        # Defensive fallback for environments where an event loop is already running.
        if "asyncio.run() cannot be called from a running event loop" not in str(exc):
            raise

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                asyncio.wait_for(
                    search_papers(query=query, filter_type=filter_type),
                    timeout=timeout_seconds,
                )
            )
        except asyncio.TimeoutError as loop_exc:
            raise TimeoutError("Journal service timed out") from loop_exc
        finally:
            loop.close()


def _normalize_item(item: Dict[str, Any], rank: int, max_citations: int) -> Dict[str, Any]:
    citations = int(item.get("citations") or 0)
    score = (citations / max_citations) if max_citations else 0.0
    abstract = (item.get("abstract") or "").strip()

    return {
        "rank": rank,
        "title": item.get("title") or "Untitled",
        "doi": item.get("doi") or "",
        "year": item.get("year"),
        "abstract": abstract,
        "summary": abstract[:320] + ("..." if len(abstract) > 320 else ""),
        "citations": citations,
        "publisher": item.get("publisher") or "",
        "is_oa": bool(item.get("is_oa")),
        "pdf": item.get("pdf"),
        "source_url": _build_source_url(item),
        "similarity_score": round(score, 4),
        "match_percentage": round(score * 100, 2),
    }


def recommend_journals(
    question: str,
    top_k: int = 5,
    filter_type: str = "all",
    service_base_url: str = "",
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    if filter_type not in ALLOWED_FILTERS:
        raise JournalServiceError(
            "filter_type must be one of: all, open_access, subscription", status_code=400
        )

    top_k = max(1, min(int(top_k), 20))
    query = question.strip()

    try:
        _ = service_base_url  # kept for backward-compatible function signature
        payload = _run_search_papers(
            query=query,
            filter_type=filter_type,
            timeout_seconds=timeout_seconds,
        )
    except TimeoutError as exc:
        raise JournalServiceError(
            "Journal service timed out", status_code=504) from exc
    except Exception as exc:  # pragma: no cover - defensive runtime mapping
        raise JournalServiceError(
            f"Journal processing failed: {exc}", status_code=502
        ) from exc

    results = payload.get("results") if isinstance(payload, dict) else []
    if not isinstance(results, list):
        results = []

    if not results:
        return {
            "status": "no_results",
            "query": query,
            "items": [],
            "total": 0,
            "message": "No journals found matching your query.",
        }

    trimmed = results[:top_k]
    max_citations = max((int(item.get("citations") or 0)
                        for item in trimmed), default=1)
    items = [
        _normalize_item(item, rank=index + 1, max_citations=max_citations)
        for index, item in enumerate(trimmed)
    ]

    return {
        "status": "ok",
        "query": query,
        "items": items,
        "total": len(items),
        "message": "Journal recommendations fetched successfully",
    }


def ping_journal_service(service_base_url: str, timeout_seconds: int = 3) -> bool:
    try:
        _ = service_base_url
        _ = timeout_seconds
        _load_search_papers_callable()
        return True
    except Exception:
        return False
