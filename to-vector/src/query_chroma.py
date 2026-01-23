import os
import json
from datetime import datetime
import chromadb
from sentence_transformers import SentenceTransformer
from rerank_results import rerank


# ===============================
# CONFIGURATION
# ===============================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "academic_textbook_chunks"
TOP_K = 15

# ===============================
# QUERY INTENT → TOPIC HINTS
# ===============================

TOPIC_HINTS = {
    "acid": ["transaction", "recovery", "concurrency"],
    "transaction": ["transaction"],
    "deadlock": ["concurrency"],
    "serializability": ["concurrency"],
    "locking": ["concurrency"],
    "recovery": ["recovery"],
}

# ===============================
# PATHS
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CHROMA_DIR = os.path.join(BASE_DIR, "..", "chroma_store")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===============================
# LOAD MODEL
# ===============================

def load_embedding_model():
    return SentenceTransformer(MODEL_NAME)

def infer_topic_filters(query: str):
    """
    Infer high-level topic filters from query text.
    Returns list of keywords to constrain retrieval.
    """
    query_l = query.lower()
    for key, keywords in TOPIC_HINTS.items():
        if key in query_l:
            return keywords
    return []

# ===============================
# QUERY CHROMA
# ===============================

def query_chroma(query: str, model, collection):
    query_embedding = model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    # 🔹 NEW: infer topic filters
    topic_filters = infer_topic_filters(query)

    where_clause = None
    if topic_filters:
        where_clause = {
            "topic": {"$in": topic_filters}
        }


    # 🔹 UPDATED Chroma query
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        where=where_clause,
        include=["documents", "metadatas", "distances"]
    )

    # 🔹 FALLBACK: if filtering is too strict
    if not results["documents"] or not results["documents"][0]:
       results = collection.query(
          query_embeddings=[query_embedding],
          n_results=TOP_K,
          include=["documents", "metadatas", "distances"]
    )

    output = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

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
            "text_preview": doc[:600]
        })

    return output


# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    TEST_QUERIES = [
        
        "Explain ACID properties in DBMS",
        "What is serializability?",
        "Explain deadlock and deadlock prevention",
       
    ]

    print("🔹 Loading model and ChromaDB...")
    model = load_embedding_model()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(name=COLLECTION_NAME)

    all_results = {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "collection": COLLECTION_NAME,
        "top_k": TOP_K,
        "queries": []
    }

    for q in TEST_QUERIES:
        print(f"\n🔎 QUERY: {q}")
        print("=" * 80)

        results = query_chroma(q, model, collection)

        for r in results[:5]:
            print(f"Rank {r['rank']} | Distance {r['distance']}")
            print(f"Chapter: {r['chapter']}")
            print(f"Section: {r['section']}")
            print(r["text_preview"].replace("\n", " "))
            print("-" * 80)

        reranked_results = rerank(q, results)

        all_results["queries"].append({
            "query": q,
            "chroma_results": results,
            "reranked_results": reranked_results
        })

        


    # ===============================
    # SAVE OUTPUT
    # ===============================

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(
        OUTPUT_DIR,
        f"query_results_{timestamp}.json"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print("\n✅ Query results saved to:")
    print(output_path)
