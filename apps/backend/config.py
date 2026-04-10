import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/acadclarifier",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BOOK_RECOMMENDER_CHROMA_PATH = os.getenv(
        "BOOK_RECOMMENDER_CHROMA_PATH",
        str(
            Path(__file__).resolve().parents[2]
            / "services"
            / "book-recommender"
            / "chroma_data"
        ),
    )
    RETRIEVAL_LOCAL_EMBEDDINGS_DIR = os.getenv(
        "RETRIEVAL_LOCAL_EMBEDDINGS_DIR",
        str(
            Path(__file__).resolve().parents[2]
            / "services"
            / "retrieval-local"
            / "outputs"
            / "embeddings_output"
        ),
    )
    RETRIEVAL_JOURNAL_CHROMA_PATH = os.getenv(
        "RETRIEVAL_JOURNAL_CHROMA_PATH",
        str(
            Path(__file__).resolve().parents[2]
            / "services"
            / "retrieval-journal"
            / "chroma_db"
        ),
    )
