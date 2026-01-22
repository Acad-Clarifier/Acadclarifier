import json
import sys
import numpy as np
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from typing import List, Dict, Any
from datetime import datetime
import os
import json


# =========================
# Configuration
# =========================

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.35   # T2 (tune later)
OUTPUT_TOP_K = None          # set to int if you want a cap

OUTPUT_DIR = "embeddings_outputs"

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

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

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

    output_parent = os.path.join("..", "outputs", OUTPUT_DIR)
    os.makedirs(output_parent, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage4_embeddings_{timestamp}.json"
    path = os.path.join(output_parent, filename)

    payload = {
        "query": query,
        "stage": "stage_4_embedding_similarity",
        "timestamp_utc": timestamp,
        "num_chunks": len(chunks),
        "chunks": chunks
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return path

# =========================
# Entry point
# =========================


def main():
    if len(sys.argv) < 2:
        print("Usage: python stage4_embed_and_score.py <stage3_chunks.json>")
        sys.exit(1)

    input_path = sys.argv[1]

    data = load_stage3_chunks(input_path)

    if "chunks" not in data:
        raise ValueError("Invalid input: missing 'chunks'")

    query = data.get("query", "")
    chunks = data["chunks"]

    if not query or not chunks:
        raise ValueError("Query or chunks missing")

    scored_chunks = compute_similarity(query, chunks)

    output = {
        "query": query,
        "stage": "stage_4_embedding_similarity",
        "num_input_chunks": len(chunks),
        "num_kept_chunks": len(scored_chunks),
        "chunks": scored_chunks
    }

    output_path = save_embeddings(query, scored_chunks)

    print("[STAGE 4 COMPLETE]")
    print(f"Input chunks : {len(chunks)}")
    print(f"Kept chunks  : {len(scored_chunks)}")
    print(f"Output saved: {output_path}")


if __name__ == "__main__":
    main()
