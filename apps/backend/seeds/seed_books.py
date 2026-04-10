from ..db import db
from ..models.book import Book
from ..server import create_app

SAMPLE_BOOKS = [
    {
        "uid": "book-1",
        "title": "Database System Concepts Sixth Edition",
        "author": "Abraham Silberschatz",
        "isbn": "9780073523323",
        "topic": "DBMS",
        "description": "Core database fundamentals covering relational design, SQL, indexing, transactions, and query processing.",
        "cover_image_url": None,
        "published_year": 2010,
    },
    {
        "uid": "book-2",
        "title": "Hadoop in Action",
        "author": "Chuck Lam",
        "isbn": "9781935182191",
        "topic": "Big Data",
        "description": "Practical introduction to Hadoop ecosystems, MapReduce workflows, and distributed processing patterns.",
        "cover_image_url": None,
        "published_year": 2010,
    },
    {
        "uid": "book-3",
        "title": "Artificial Intelligence: A Modern Approach Third Edition",
        "author": "Stuart Russell",
        "isbn": "9780134610993",
        "topic": "Artificial Intelligence",
        "description": "Comprehensive AI reference covering search, planning, uncertainty, machine learning, and intelligent agents.",
        "cover_image_url": None,
        "published_year": 2009,
    },
    {
        "uid": "book-4",
        "title": "Introduction to Algorithms Fourth Edition",
        "author": "Thomas H. Cormen",
        "isbn": "9780262046305",
        "topic": "Algorithms",
        "description": "Algorithm design, complexity analysis, data structures, and proof-driven reasoning for core CS problems.",
        "cover_image_url": None,
        "published_year": 2022,
    },
    {
        "uid": "book-5",
        "title": "Computer Networks Fourth Edition",
        "author": "Andrew Tanenbaum",
        "isbn": "9780130661029",
        "topic": "Networking",
        "description": "Network architectures, protocols, transport systems, and layered communication in modern internets.",
        "cover_image_url": None,
        "published_year": 2003,
    },
    {
        "uid": "book-6",
        "title": "Distributed Systems: Concepts and Design",
        "author": "George Coulouris",
        "isbn": "9780132143011",
        "topic": "Distributed Systems",
        "description": "Foundational distributed systems concepts, middleware design, consistency, fault tolerance, and scalability.",
        "cover_image_url": None,
        "published_year": 2011,
    },
    {
        "uid": "book-7",
        "title": "Java: The Complete Reference Seventh Edition",
        "author": "Herbert Schildt",
        "isbn": "9780072263855",
        "topic": "Programming",
        "description": "Comprehensive Java language reference from fundamentals to advanced APIs and platform concepts.",
        "cover_image_url": None,
        "published_year": 2006,
    },
    {
        "uid": "book-8",
        "title": "Software Engineering: A Practitioner's Approach Seventh Edition",
        "author": "Roger Pressman",
        "isbn": "9780073375977",
        "topic": "Software Engineering",
        "description": "Software process, architecture, quality, testing, and project management practices for production systems.",
        "cover_image_url": None,
        "published_year": 2010,
    },
    {
        "uid": "book-9",
        "title": "Data Mining: Concepts and Techniques Third Edition",
        "author": "Jiawei Han",
        "isbn": "9780123814791",
        "topic": "Data Mining",
        "description": "Data mining concepts, pattern discovery, classification, clustering, and large-scale analytical workflows.",
        "cover_image_url": None,
        "published_year": 2011,
    },
    {
        "uid": "book-10",
        "title": "Human Computer Interaction: Fundamentals and Practice",
        "author": "Gerard Jounghyun Kim",
        "isbn": "9781439898628",
        "topic": "Human Computer Interaction",
        "description": "Human-computer interaction principles, design methods, usability, and interaction models.",
        "cover_image_url": None,
        "published_year": 2015,
    },
]


def seed_books():
    canonical_by_uid = {payload["uid"]: payload for payload in SAMPLE_BOOKS}
    existing_rows = Book.query.all()
    existing_books = {book.uid: book for book in existing_rows}
    existing_by_isbn = {
        book.isbn: book for book in existing_rows if book.isbn
    }

    inserted_count = 0
    updated_count = 0
    deleted_count = 0

    for uid, payload in canonical_by_uid.items():
        existing = existing_books.get(uid)
        if existing is None and payload.get("isbn"):
            existing = existing_by_isbn.get(payload["isbn"])

        if existing is None:
            db.session.add(Book(**payload))
            inserted_count += 1
            continue

        changed = False
        for field_name, field_value in payload.items():
            if getattr(existing, field_name) != field_value:
                setattr(existing, field_name, field_value)
                changed = True

        if changed:
            updated_count += 1

    # Remove prior placeholder rows so library only contains the real local corpus.
    db.session.flush()

    canonical_uids = set(canonical_by_uid.keys())
    for existing in Book.query.all():
        if existing.uid not in canonical_uids and existing.uid.startswith("book-"):
            db.session.delete(existing)
            deleted_count += 1

    db.session.commit()
    return inserted_count, updated_count, deleted_count


def main():
    app = create_app()
    with app.app_context():
        inserted, updated, deleted = seed_books()
        total = db.session.query(Book).count()
        print(
            f"Seed complete. Inserted {inserted}, updated {updated}, deleted {deleted}. Total books: {total}"
        )


if __name__ == "__main__":
    main()
