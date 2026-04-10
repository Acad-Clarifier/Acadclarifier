import concurrent.futures
import time

from flask import Blueprint, current_app, jsonify, request

try:
    from .journal_client import JournalServiceError, recommend_journals
    from .recommend_client import recommend_books
    from .repositories import get_book_by_ref, list_books
    from .session import get_active_book, set_active_book
    from .local_retrieval_bridge import run_local_retrieval_pipeline
    from .web_pipeline import run_web_pipeline
except ImportError:
    from journal_client import JournalServiceError, recommend_journals
    from recommend_client import recommend_books
    from repositories import get_book_by_ref, list_books
    from session import get_active_book, set_active_book
    from local_retrieval_bridge import run_local_retrieval_pipeline
    from web_pipeline import run_web_pipeline

api_routes = Blueprint("api_routes", __name__)

# Increased timeouts to handle model warmup + request processing on first call
# Background thread loads recommender ~2-5s after app starts
ASK_TIMEOUT_SECONDS = 120  # Local: includes potential first-time model load
WEB_ASK_TIMEOUT_SECONDS = 120  # Web: includes potential first-time model load
JOURNAL_TIMEOUT_SECONDS = 90


def _map_chroma_error_to_http(message: str, error_code: str = ""):
    lowered = (message or "").lower()
    code = (error_code or "").lower()

    if "unsupported version of sqlite3" in lowered or code == "chroma_sqlite_incompatible":
        return 503, "chroma/sqlite compatibility issue"

    if "collection expecting embedding with dimension" in lowered or code == "chroma_embedding_dimension_mismatch":
        return 422, "embedding dimension mismatch"

    if code in {"embeddings_missing", "chroma_storage_corrupt"}:
        return 503, "local embeddings store unavailable"

    return 500, "retrieval failed"


def _run_with_timeout(func, *, timeout_seconds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        return future.result(timeout=timeout_seconds)


@api_routes.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "AcadClarifier Backend"
    })


@api_routes.route("/library", methods=["GET"])
def library_list():
    search = request.args.get("q", default=None, type=str)
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=20, type=int)

    data = list_books(search=search, page=page, page_size=page_size)
    return jsonify(data)


@api_routes.route("/library/<string:book_ref>", methods=["GET"])
def library_get_book(book_ref):
    book = get_book_by_ref(book_ref)
    if not book:
        return jsonify({"error": "Book not found", "book_ref": book_ref}), 404

    return jsonify(book.to_dict())


@api_routes.route("/session", methods=["GET"])
def session_get():
    return jsonify({"active_book": get_active_book()})


@api_routes.route("/rfid/update", methods=["POST"])
def rfid_update():
    payload = request.get_json(silent=True) or {}
    uid = payload.get("uid")
    if not uid:
        return jsonify({"error": "uid is required"}), 400

    set_active_book(uid)
    return jsonify({"status": "ok", "active_book": uid})


@api_routes.route("/ask", methods=["POST"])
def ask_question():
    started = time.perf_counter()
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    book_ref = (
        payload.get("book_ref")
        or payload.get("book_uid")
        or payload.get("uid")
        or get_active_book()
    )
    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        result = _run_with_timeout(
            lambda: run_local_retrieval_pipeline(
                query_text=question,
                book_ref=book_ref,
                query_id=payload.get("query_id"),
                request_metadata={
                    "route": "/ask",
                    "book_ref_source": "payload_or_session",
                },
            ),
            timeout_seconds=ASK_TIMEOUT_SECONDS,
        )
    except concurrent.futures.TimeoutError:
        current_app.logger.warning(
            "/ask timed out after %ss", ASK_TIMEOUT_SECONDS)
        return jsonify({"status": "error", "error": "request timed out"}), 504
    except Exception as exc:
        current_app.logger.exception("/ask failed: %s", exc)
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        current_app.logger.info("/ask completed in %sms", elapsed)

    if result.get("status") != "success":
        error_message = result.get("error", "retrieval failed")
        error_code = result.get("error_code", "")
        status_code, summary = _map_chroma_error_to_http(
            error_message, error_code)
        payload = dict(result)
        payload.setdefault("error_summary", summary)
        return jsonify(payload), status_code

    return jsonify(result)


@api_routes.route("/web/ask", methods=["POST"])
def ask_web_question():
    started = time.perf_counter()
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        result = _run_with_timeout(
            lambda: run_web_pipeline(question),
            timeout_seconds=WEB_ASK_TIMEOUT_SECONDS,
        )
    except concurrent.futures.TimeoutError:
        current_app.logger.warning(
            "/web/ask timed out after %ss", WEB_ASK_TIMEOUT_SECONDS)
        return jsonify({"error": "request timed out"}), 504
    except Exception as exc:
        current_app.logger.exception("/web/ask failed: %s", exc)
        return jsonify({"error": str(exc)}), 500
    finally:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        current_app.logger.info("/web/ask completed in %sms", elapsed)

    return jsonify(result)


@api_routes.route("/recommend", methods=["POST"])
def recommend_route():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or payload.get("query") or "").strip()
    top_k = payload.get("top_k", 5)

    if not question:
        return jsonify({"error": "question is required"}), 400

    if not isinstance(top_k, int):
        return jsonify({"error": "top_k must be an integer"}), 400

    try:
        result = recommend_books(
            question=question,
            top_k=top_k,
            chroma_path=current_app.config.get("BOOK_RECOMMENDER_CHROMA_PATH"),
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    if result.get("status") == "error":
        return jsonify(result), 500

    return jsonify(result)


@api_routes.route("/journal/recommend", methods=["POST"])
def recommend_journal_route():
    started = time.perf_counter()
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or payload.get("query") or "").strip()
    top_k = payload.get("top_k", 10)
    filter_type = (payload.get("filter_type") or "all").strip().lower()

    if not question:
        return jsonify({"error": "question is required"}), 400

    if not isinstance(top_k, int):
        return jsonify({"error": "top_k must be an integer"}), 400

    try:
        result = _run_with_timeout(
            lambda: recommend_journals(
                question=question,
                top_k=top_k,
                filter_type=filter_type,
                timeout_seconds=JOURNAL_TIMEOUT_SECONDS,
            ),
            timeout_seconds=JOURNAL_TIMEOUT_SECONDS + 2,
        )
    except concurrent.futures.TimeoutError:
        current_app.logger.warning(
            "/journal/recommend timed out after %ss", JOURNAL_TIMEOUT_SECONDS)
        return jsonify({"error": "request timed out", "status": "error", "items": []}), 504
    except JournalServiceError as exc:
        status_code, summary = _map_chroma_error_to_http(str(exc))
        final_status = exc.status_code if status_code == 500 else status_code
        return jsonify({
            "error": str(exc),
            "error_summary": summary,
            "status": "error",
            "items": []
        }), final_status
    except Exception as exc:
        current_app.logger.exception("/journal/recommend failed: %s", exc)
        return jsonify({"error": str(exc), "status": "error", "items": []}), 500
    finally:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        current_app.logger.info(
            "/journal/recommend completed in %sms", elapsed)

    if result.get("status") == "error":
        return jsonify(result), 500

    return jsonify(result)
