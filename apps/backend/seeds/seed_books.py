from ..db import db
from ..models.book import Book
from ..server import create_app

SAMPLE_BOOKS = [
    {
        "uid": "book-dbms-001",
        "title": "Database System Concepts",
        "author": "Abraham Silberschatz",
        "isbn": "9780073523323",
        "topic": "DBMS",
        "description": "Comprehensive fundamentals of database systems, SQL, and transaction management.",
        "cover_image_url": None,
        "published_year": 2010,
    },
    {
        "uid": "book-ml-002",
        "title": "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow",
        "author": "Aurelien Geron",
        "isbn": "9781492032649",
        "topic": "Machine Learning",
        "description": "Practical machine learning workflows with modern Python libraries.",
        "cover_image_url": None,
        "published_year": 2019,
    },
    {
        "uid": "book-ai-003",
        "title": "Artificial Intelligence: A Modern Approach",
        "author": "Stuart Russell",
        "isbn": "9780134610993",
        "topic": "Artificial Intelligence",
        "description": "Core AI theory, search, planning, uncertainty, and learning.",
        "cover_image_url": None,
        "published_year": 2020,
    },
    {
        "uid": "book-cn-004",
        "title": "Computer Networking: A Top-Down Approach",
        "author": "James Kurose",
        "isbn": "9780136681557",
        "topic": "Networking",
        "description": "Networking architecture, protocols, and internet systems from application down.",
        "cover_image_url": None,
        "published_year": 2021,
    },
    {
        "uid": "book-os-005",
        "title": "Operating System Concepts",
        "author": "Abraham Silberschatz",
        "isbn": "9781119456339",
        "topic": "Operating Systems",
        "description": "Processes, memory, file systems, and modern OS design principles.",
        "cover_image_url": None,
        "published_year": 2018,
    },
    {
        "uid": "book-se-006",
        "title": "Software Engineering",
        "author": "Ian Sommerville",
        "isbn": "9780137035151",
        "topic": "Software Engineering",
        "description": "Software lifecycle, architecture, requirements, and quality practices.",
        "cover_image_url": None,
        "published_year": 2015,
    },
    {
        "uid": "book-ds-007",
        "title": "Introduction to Algorithms",
        "author": "Thomas H. Cormen",
        "isbn": "9780262046305",
        "topic": "Algorithms",
        "description": "Algorithmic analysis and data structures with rigorous foundations.",
        "cover_image_url": None,
        "published_year": 2022,
    },
    {
        "uid": "book-cc-008",
        "title": "Cloud Computing: Concepts, Technology and Architecture",
        "author": "Thomas Erl",
        "isbn": "9780133387520",
        "topic": "Cloud Computing",
        "description": "Cloud models, architecture patterns, and enterprise adoption guidance.",
        "cover_image_url": None,
        "published_year": 2013,
    },
    {
        "uid": "book-nlp-009",
        "title": "Speech and Language Processing",
        "author": "Daniel Jurafsky",
        "isbn": "9780131873216",
        "topic": "NLP",
        "description": "Statistical and neural methods for natural language processing tasks.",
        "cover_image_url": None,
        "published_year": 2008,
    },
    {
        "uid": "book-cv-010",
        "title": "Deep Learning for Computer Vision",
        "author": "Rajalingappaa Shanmugamani",
        "isbn": "9781788295628",
        "topic": "Computer Vision",
        "description": "Computer vision pipelines using deep neural networks and transfer learning.",
        "cover_image_url": None,
        "published_year": 2018,
    },
]


def seed_books():
    existing_uids = {
        row[0] for row in db.session.query(Book.uid).filter(Book.uid.in_([b["uid"] for b in SAMPLE_BOOKS])).all()
    }

    new_books = [Book(**payload)
                 for payload in SAMPLE_BOOKS if payload["uid"] not in existing_uids]

    if new_books:
        db.session.add_all(new_books)
        db.session.commit()

    return len(new_books)


def main():
    app = create_app()
    with app.app_context():
        inserted = seed_books()
        total = db.session.query(Book).count()
        print(
            f"Seed complete. Inserted {inserted} new books. Total books: {total}")


if __name__ == "__main__":
    main()
