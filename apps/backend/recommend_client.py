from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict


_RECOMMENDER_INSTANCE = None
_RECOMMENDER_IMPORT_ERROR = None


def _load_recommender_class():
    """Load BookRecommender from services/book-recommender/src."""
    recommender_src = (
        Path(__file__).resolve().parents[2]
        / "services"
        / "book-recommender"
        / "src"
    )

    if not recommender_src.exists():
        raise FileNotFoundError(
            f"Recommender source path not found: {recommender_src}"
        )

    src_str = str(recommender_src)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

    from user_library_query import BookRecommender  # pylint: disable=import-error

    return BookRecommender


def _get_default_chroma_path() -> Path:
    return Path(__file__).resolve().parents[2] / "services" / "book-recommender" / "chroma_data"


def get_recommender(chroma_path: str | None = None):
    global _RECOMMENDER_INSTANCE
    global _RECOMMENDER_IMPORT_ERROR

    if _RECOMMENDER_INSTANCE is None:
        try:
            book_recommender_cls = _load_recommender_class()
            _RECOMMENDER_INSTANCE = book_recommender_cls(
                chroma_persist_dir=chroma_path or str(
                    _get_default_chroma_path())
            )
        except Exception as exc:  # pragma: no cover - runtime fallback
            _RECOMMENDER_IMPORT_ERROR = str(exc)
            _RECOMMENDER_INSTANCE = None

    return _RECOMMENDER_INSTANCE


def _fallback_library_db_path() -> Path:
    return Path(__file__).resolve().parents[2] / "services" / "book-recommender" / "src" / "library.db"


def _score_row(query_terms: set[str], row: sqlite3.Row) -> int:
    text = " ".join(
        [
            str(row["title"] or ""),
            str(row["author"] or ""),
            str(row["category"] or ""),
            str(row["summary"] or ""),
        ]
    ).lower()
    return sum(1 for term in query_terms if term and term in text)


def _fallback_recommend(question: str, top_k: int) -> Dict[str, Any]:
    db_path = _fallback_library_db_path()
    if not db_path.exists():
        return {
            "status": "error",
            "query": question,
            "items": [],
            "total": 0,
            "message": "Fallback DB not found and Chroma recommender is unavailable",
        }

    query_terms = {part.strip().lower()
                   for part in question.split() if part.strip()}
    if not query_terms:
        return {
            "status": "no_results",
            "query": question,
            "items": [],
            "total": 0,
            "message": "Please provide a meaningful query.",
        }

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT book_id, title, author, category, summary FROM books")
    rows = cur.fetchall()
    conn.close()

    ranked = []
    for row in rows:
        score = _score_row(query_terms, row)
        if score > 0:
            ranked.append((score, row))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = ranked[: max(1, min(top_k, 20))]

    if not selected:
        return {
            "status": "no_results",
            "query": question,
            "items": [],
            "total": 0,
            "message": "No books found matching your query.",
        }

    max_score = selected[0][0] or 1
    items = []
    for idx, (score, row) in enumerate(selected, 1):
        similarity = round(score / max_score, 4)
        items.append(
            {
                "rank": idx,
                "book_id": row["book_id"],
                "title": row["title"],
                "author": row["author"],
                "category": row["category"],
                "summary": row["summary"],
                "similarity_score": similarity,
                "match_percentage": round(similarity * 100, 2),
            }
        )

    return {
        "status": "ok",
        "query": question,
        "items": items,
        "total": len(items),
        "message": "Recommendations fetched successfully (fallback mode)",
    }


def recommend_books(question: str, top_k: int = 5, chroma_path: str | None = None) -> Dict[str, Any]:
    recommender = get_recommender(chroma_path=chroma_path)
    if recommender is None:
        return _fallback_recommend(question, top_k)

    results = recommender.query(question, top_k=top_k)

    if not results:
        return {
            "status": "ok",
            "query": question,
            "items": [],
            "total": 0,
            "message": "No recommendations found",
        }

    first = results[0]
    if first.get("status") == "failed":
        return {
            "status": "error",
            "query": question,
            "items": [],
            "total": 0,
            "message": first.get("message", "Recommendation failed"),
        }

    if first.get("status") == "no_results":
        return {
            "status": "no_results",
            "query": question,
            "items": [],
            "total": 0,
            "message": first.get("message", "No recommendations found"),
        }

    return {
        "status": "ok",
        "query": question,
        "items": results,
        "total": len(results),
        "message": "Recommendations fetched successfully",
    }
