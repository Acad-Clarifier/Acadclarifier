import json
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from sklearn.metrics.pairwise import cosine_similarity


# =========================
# Configuration
# =========================

EMBED_MODEL = "all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

REDUNDANCY_THRESHOLD = 0.9
TOP_K = 6

OUTPUT_DIR = "rerank_outputs"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PARENT = (SCRIPT_DIR / ".." / "outputs" / OUTPUT_DIR).resolve()

_EMBED_MODEL_CACHE = None
_RERANK_MODEL_CACHE = None
_MODEL_LOCK = threading.Lock()


# =========================
# Utilities
# =========================

def load_stage4(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def embed_texts(model: SentenceTransformer, texts: List[str]) -> np.ndarray:
    return model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )


def answer_likeness_penalty(text: str) -> float:

    penalties = [
        # Stack Overflow / Stack Exchange
        "ask question",
        "asked",
        "viewed",
        "votes",
        "score",
        "edited",
        "answered",
        "accepted answer",
        "hot network questions",
        "community wiki",
        "closed as",
        "duplicate of",
        "protected question",
        "improve this question",
        "add a comment",

        # Quora-style
        "what do you think",
        "in your opinion",
        "according to you",
        "share your thoughts",
        "answers",
        "answer requested",
        "request answers",
        "follow question",
        "people also asked",
        "followers",

        # Reddit / Forums
        "posted by",
        "comments",
        "discussion",
        "thread",
        "replies",
        "original poster",
        "this thread",
        "sorted by",
        "top comments",

        # GitHub Issues / Discussions
        "issue",
        "opened by",
        "closed",
        "reopen",
        "this issue",
        "related issue",
        "maintainers",
        "contributors",

        # Blogs / Medium
        "responses",
        "leave a response",
        "published on",
        "updated on",
        "reading time",
        "recommended for you",

        # Generic opinion phrases
        "can anyone",
        "does anyone know",
        "any ideas",
        "any suggestions",
        "please help",
        "help needed",
        "thanks in advance",
        "beginner question",
        "newbie here",
        "quick question",

        # Similarity traps
        "what is the best",
        "which is better",
        "pros and cons",
        "advantages and disadvantages",
        "should i",
        "is it worth",
        "recommend",
        "comparison",
        "vs",
        "versus"
    ]

    text_l = text.lower()
    penalty = 0.0

    for p in penalties:
        if p in text_l:
            penalty += 0.5

    return penalty


# =========================
# Stage 5A — Redundancy pruning
# =========================

def remove_redundant_chunks(chunks: List[Dict]) -> List[Dict]:
    """
    Removes near-duplicate chunks using cosine similarity.
    Keeps the chunk with higher semantic similarity score.
    """
    if len(chunks) <= 1:
        return chunks

    global _EMBED_MODEL_CACHE
    if _EMBED_MODEL_CACHE is None:
        with _MODEL_LOCK:
            if _EMBED_MODEL_CACHE is None:
                _EMBED_MODEL_CACHE = SentenceTransformer(EMBED_MODEL)

    embedder = _EMBED_MODEL_CACHE

    texts = [c["chunk_text"] for c in chunks]
    vectors = embed_texts(embedder, texts)

    keep_flags = [True] * len(chunks)

    for i in range(len(chunks)):
        if not keep_flags[i]:
            continue

        for j in range(i + 1, len(chunks)):
            if not keep_flags[j]:
                continue

            sim = cosine_similarity(
                vectors[i].reshape(1, -1),
                vectors[j].reshape(1, -1)
            )[0][0]

            if sim > REDUNDANCY_THRESHOLD:
                # Keep higher similarity-to-query chunk
                if chunks[i]["similarity"] >= chunks[j]["similarity"]:
                    keep_flags[j] = False
                else:
                    keep_flags[i] = False
                    break

    return [c for c, keep in zip(chunks, keep_flags) if keep]


# =========================
# Stage 5B — Cross-encoder reranking
# =========================

def rerank_chunks(query: str, chunks: List[Dict]) -> List[Dict]:
    """
    Reranks chunks using cross-encoder relevance scoring.
    """
    if not chunks:
        return []

    global _RERANK_MODEL_CACHE
    if _RERANK_MODEL_CACHE is None:
        with _MODEL_LOCK:
            if _RERANK_MODEL_CACHE is None:
                _RERANK_MODEL_CACHE = CrossEncoder(RERANK_MODEL)

    reranker = _RERANK_MODEL_CACHE

    pairs = [(query, c["chunk_text"]) for c in chunks]
    scores = reranker.predict(pairs)

    for c, score in zip(chunks, scores):
        penalty = answer_likeness_penalty(c["chunk_text"])
        c["rerank_score"] = round(float(score - penalty), 4)

    chunks.sort(key=lambda x: x["rerank_score"], reverse=True)

    return chunks


# =========================
# Persistence
# =========================

def save_reranked(query: str, chunks: List[Dict]) -> str:
    OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage5_reranked_{timestamp}.json"
    path = OUTPUT_PARENT / filename

    payload = {
        "query": query,
        "stage": "stage_5_dedup_and_rerank",
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
    Executes Stage 5 deduplication and reranking.

    Parameters:
    - input_path: path to Stage 4 embeddings JSON (required)
    - query: optional override if not present in input JSON
    """

    if not input_path:
        raise ValueError("reranking.run requires input_path")

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    data = load_stage4(str(path))

    if "chunks" not in data:
        raise ValueError("Invalid input: missing 'chunks'")

    resolved_query = data.get("query") or query or ""
    chunks = data["chunks"]

    if not resolved_query or not chunks:
        raise ValueError("Query or chunks missing")

    deduped_chunks = remove_redundant_chunks(chunks)
    reranked_chunks = rerank_chunks(resolved_query, deduped_chunks)
    final_chunks = reranked_chunks[:TOP_K]

    return save_reranked(resolved_query, final_chunks)


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    cli_query = sys.argv[2] if len(sys.argv) > 2 else None

    output_path = run(input_path=input_path, query=cli_query)
    print(output_path)


if __name__ == "__main__":
    main()
