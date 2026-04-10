import json
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# =========================
# Configuration
# =========================

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.35   # T2 (tune later)
OUTPUT_TOP_K = None          # set to int if you want a cap

OUTPUT_DIR = "embeddings_outputs"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PARENT = (SCRIPT_DIR / ".." / "outputs" / OUTPUT_DIR).resolve()

_EMBEDDING_MODEL = None
_EMBEDDING_MODEL_LOCK = threading.Lock()

# =========================
# Utilities
# =========================


def load_stage3_chunks(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def embed_texts(model: SentenceTransformer, texts: List[str]) -> np.ndarray:
    """
    Batch embedding for efficiency.
    """
    return model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )


# =========================
# Core logic
# =========================

def compute_similarity(
    query: str,
    chunks: List[Dict]
) -> List[Dict]:

    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        with _EMBEDDING_MODEL_LOCK:
            if _EMBEDDING_MODEL is None:
                _EMBEDDING_MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)

    model = _EMBEDDING_MODEL

    # ---- embed query ----
    query_vec = embed_texts(model, [query])[0]

    # ---- embed chunks ----
    chunk_texts = [c["chunk_text"] for c in chunks]
    chunk_vecs = embed_texts(model, chunk_texts)

    # ---- cosine similarity ----
    sims = cosine_similarity(
        query_vec.reshape(1, -1),
        chunk_vecs
    )[0]

    scored_chunks = []

    for chunk, sim in zip(chunks, sims):
        if sim < SIMILARITY_THRESHOLD:
            continue

        scored_chunks.append({
            "chunk_text": chunk["chunk_text"],
            "source": chunk["source"],
            "tavily_score": chunk.get("tavily_score"),
            "similarity": round(float(sim), 4),
            "token_estimate": chunk.get("token_estimate")
        })

    # ---- sort by similarity ----
    scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)

    if OUTPUT_TOP_K:
        scored_chunks = scored_chunks[:OUTPUT_TOP_K]

    return scored_chunks

# ----------------------------------------


def save_embeddings(query: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Saves Stage-4 embedding + similarity results to embeddings_output.
    """
    OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage4_embeddings_{timestamp}.json"
    path = OUTPUT_PARENT / filename

    payload = {
        "query": query,
        "stage": "stage_4_embedding_similarity",
        "timestamp_utc": timestamp,
        "num_chunks": len(chunks),
        "chunks": chunks
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return str(path)

# =========================
# Entry point
# =========================


def run(input_path: str | None, *, query: str | None = None) -> str:
    """
    Executes Stage 4 embedding + similarity scoring.

    Parameters:
    - input_path: path to Stage 3 chunks JSON (required)
    - query: optional override if not present in input JSON
    """

    if not input_path:
        raise ValueError("embeddings.run requires input_path")

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    data = load_stage3_chunks(str(path))

    if "chunks" not in data:
        raise ValueError("Invalid input: missing 'chunks'")

    resolved_query = data.get("query") or query or ""
    chunks = data["chunks"]

    if not resolved_query or not chunks:
        raise ValueError("Query or chunks missing")

    scored_chunks = compute_similarity(resolved_query, chunks)
    return save_embeddings(resolved_query, scored_chunks)


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    cli_query = sys.argv[2] if len(sys.argv) > 2 else None

    output_path = run(input_path=input_path, query=cli_query)
    print(output_path)


if __name__ == "__main__":
    main()
