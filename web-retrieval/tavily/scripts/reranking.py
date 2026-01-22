import json
import sys
import os
import numpy as np
from typing import List, Dict
from datetime import datetime

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

    embedder = SentenceTransformer(EMBED_MODEL)

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

    reranker = CrossEncoder(RERANK_MODEL)

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
    output_parent = os.path.join("..", "outputs", OUTPUT_DIR)
    os.makedirs(output_parent, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage5_reranked_{timestamp}.json"
    path = os.path.join(output_parent, filename)

    payload = {
        "query": query,
        "stage": "stage_5_dedup_and_rerank",
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
        print("Usage: python stage5_dedup_and_rerank.py <stage4_embeddings.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    data = load_stage4(input_path)

    if "chunks" not in data:
        raise ValueError("Invalid input: missing 'chunks'")

    query = data["query"]
    chunks = data["chunks"]

    # ---- Step A: redundancy pruning ----
    deduped_chunks = remove_redundant_chunks(chunks)

    # ---- Step B: reranking ----
    reranked_chunks = rerank_chunks(query, deduped_chunks)

    # ---- keep top K ----
    final_chunks = reranked_chunks[:TOP_K]

    output_path = save_reranked(query, final_chunks)

    print("[STAGE 5 COMPLETE]")
    print(f"Input chunks      : {len(chunks)}")
    print(f"After dedup       : {len(deduped_chunks)}")
    print(f"Final kept chunks : {len(final_chunks)}")
    print(f"Output saved      : {output_path}")


if __name__ == "__main__":
    main()
