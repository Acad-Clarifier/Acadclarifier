from sqlalchemy import or_

from ..db import db
from ..models.book import Book


DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _normalize_pagination(page, page_size):
    page = page if isinstance(page, int) and page > 0 else DEFAULT_PAGE

    if not isinstance(page_size, int) or page_size <= 0:
        page_size = DEFAULT_PAGE_SIZE

    page_size = min(page_size, MAX_PAGE_SIZE)
    return page, page_size


def list_books(search=None, page=DEFAULT_PAGE, page_size=DEFAULT_PAGE_SIZE):
    page, page_size = _normalize_pagination(page, page_size)

    query = Book.query
    if search:
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Book.title.ilike(keyword),
                Book.author.ilike(keyword),
                Book.isbn.ilike(keyword),
                Book.topic.ilike(keyword),
            )
        )

    total = query.count()

    items = (
        query.order_by(Book.title.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [book.to_dict() for book in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_book_by_ref(book_ref):
    # Support both UID and integer ID for flexibility in API clients.
    by_uid = Book.query.filter_by(uid=book_ref).first()
    if by_uid:
        return by_uid

    if book_ref.isdigit():
        return db.session.get(Book, int(book_ref))

    return None
