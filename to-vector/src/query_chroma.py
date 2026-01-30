import os
import json
from datetime import datetime
from typing import List, Dict

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


# ===============================
# CONFIGURATION
# ===============================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "academic_textbook_chunks"
TOP_K = 15

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "..", "chroma_store")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "outputs/DBMS_queries")


# ===============================
# QUERY → TOPIC HINTS
# ===============================

TOPIC_HINTS = {
    "acid": ["transaction", "recovery", "concurrency"],
    "transaction": ["transaction"],
    "serializability": ["concurrency"],
    "deadlock": ["concurrency"],
    "locking": ["concurrency"],
    "recovery": ["recovery"],
}


def infer_topic_filters(query: str) -> List[str]:
    """
    Infer high-level topic filters from the query.
    """
    q = query.lower()
    for key, topics in TOPIC_HINTS.items():
        if key in q:
            return topics
    return []


# ===============================
# LOAD MODEL & CHROMA
# ===============================

def load_embedding_model():
    return SentenceTransformer(MODEL_NAME)


def load_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection(name=COLLECTION_NAME)


# ===============================
# QUERY CHROMA
# ===============================

def query_chroma(query: str, model, collection) -> List[Dict]:
    query_embedding = model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    # 🔹 Intent-aware topic filtering
    topic_filters = infer_topic_filters(query)

    where_clause = None
    if topic_filters:
        where_clause = {
            "topic": {"$in": topic_filters}
        }

    # 🔹 First attempt (with filters)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        where=where_clause,
        include=["documents", "metadatas", "distances"]
    )

    # 🔹 Fallback if filtering is too strict
    if not results["documents"] or not results["documents"][0]:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_K,
            include=["documents", "metadatas", "distances"]
        )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    output = []
    for rank, (doc, meta, dist) in enumerate(
        zip(documents, metadatas, distances), start=1
    ):
        output.append({
            "rank": rank,
            "distance": round(float(dist), 4),
            "chapter": meta.get("chapter"),
            "section": meta.get("section"),
            "page_start": meta.get("page_start"),
            "page_end": meta.get("page_end"),
            "topic": meta.get("topic"),
            "query_context": doc[:700]
        })

    return output


# ===============================
# SAVE OUTPUTS
# ===============================

def save_results(all_results: Dict):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"query_results_{timestamp}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Results saved to: {path}")


# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    queries = [
        "What is concurrency control?",
        "Explain ACID properties in DBMS",
        "What is serializability?",
        "Explain deadlock and deadlock prevention",
    ]

    print("🔹 Loading model and ChromaDB...")
    model = load_embedding_model()
    collection = load_chroma_collection()

    all_results = {
        "stage": "local_chroma_retrieval",
        "num_queries": len(queries),
        "queries": []
    }

    for q in queries:
        print(f"\n🔎 QUERY: {q}")
        print("=" * 80)

        results = query_chroma(q, model, collection)

        for r in results[:5]:
            print(f"Rank {r['rank']} | Distance {r['distance']}")
            print(f"Chapter: {r['chapter']}")
            print(f"Section: {r['section']}")
            print(r["text_preview"].replace("\n", " "))
            print("-" * 80)

        all_results["queries"].append({
            "query": q,
            "results": results
        })

    save_results(all_results)
