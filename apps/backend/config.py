import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


def _resolve_modal_first_path(env_name: str, modal_default: str, local_default: Path) -> str:
    configured_path = os.getenv(env_name)
    if configured_path:
        return configured_path

    modal_path = Path(modal_default)
    if modal_path.exists():
        return str(modal_path)

    return str(local_default)


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/acadclarifier",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOCAL_CHROMA_PATH = _resolve_modal_first_path(
        "LOCAL_CHROMA_PATH",
        "/modal/vol/data/extracted",
        Path(__file__).resolve().parents[2]
        / "services"
        / "retrieval-local"
        / "outputs"
        / "embeddings_output",
    )

    BOOK_RECOMMENDER_CHROMA_PATH = _resolve_modal_first_path(
        "BOOK_RECOMMENDER_CHROMA_PATH",
        "/modal/vol/book_recommendation",
        Path(__file__).resolve().parents[2]
        / "services"
        / "book-recommender"
        / "src"
        / "chroma_data",
    )
