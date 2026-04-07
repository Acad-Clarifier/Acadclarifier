from sqlalchemy import Index

from ..db import db


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(64), nullable=False, unique=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(32), nullable=True, unique=True)
    topic = db.Column(db.String(128), nullable=True)
    description = db.Column(db.Text, nullable=True)
    cover_image_url = db.Column(db.String(512), nullable=True)
    published_year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    __table_args__ = (
        Index("ix_books_title", "title"),
        Index("ix_books_author", "author"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "uid": self.uid,
            "title": self.title,
            "author": self.author,
            "isbn": self.isbn,
            "topic": self.topic,
            "description": self.description,
            "coverImageUrl": self.cover_image_url,
            "publishedYear": self.published_year,
        }
