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

    result = run_local_retrieval_pipeline(
        query_text=question,
        book_ref=book_ref,
        query_id=payload.get("query_id"),
        request_metadata={
            "route": "/ask",
            "book_ref_source": "payload_or_session",
        },
    )

    if result.get("status") != "success":
        return jsonify(result), 400

    return jsonify(result)


@api_routes.route("/web/ask", methods=["POST"])
def ask_web_question():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        result = run_web_pipeline(question)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

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
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or payload.get("query") or "").strip()
    top_k = payload.get("top_k", 10)
    filter_type = (payload.get("filter_type") or "all").strip().lower()

    if not question:
        return jsonify({"error": "question is required"}), 400

    if not isinstance(top_k, int):
        return jsonify({"error": "top_k must be an integer"}), 400

    try:
        result = recommend_journals(
            question=question,
            top_k=top_k,
            filter_type=filter_type,
        )
    except JournalServiceError as exc:
        return jsonify({"error": str(exc), "status": "error", "items": []}), exc.status_code
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "error", "items": []}), 500

    if result.get("status") == "error":
        return jsonify(result), 500

    return jsonify(result)
