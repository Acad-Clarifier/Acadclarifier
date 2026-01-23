import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ===============================
# CONFIGURATION
# ===============================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "academic_textbook_chunks"
TOP_K = 15

# ===============================
# PATHS
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "..", "chroma_store")

# ===============================
# LOAD MODEL
# ===============================

def load_embedding_model():
    return SentenceTransformer(MODEL_NAME)

# ===============================
# QUERY CHROMA
# ===============================

def query_chroma(query: str):
    print(f"\n🔎 QUERY: {query}")
    print("=" * 80)

    # Load embedding model
    model = load_embedding_model()
    query_embedding = model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    # Connect to Chroma
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(name=COLLECTION_NAME)

    # Query
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"]
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), start=1):
        print(f"\n--- Result {i} ---")
        print(f"Distance : {dist:.4f}")
        print(f"Chapter  : {meta.get('chapter')}")
        print(f"Section  : {meta.get('section')}")
        print(f"Pages    : {meta.get('page_start')}–{meta.get('page_end')}")
        print("\nText preview:")
        print(doc[:500].replace("\n", " "))
        print("-" * 80)

# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    TEST_QUERIES = [
        "Explain ACID properties in DBMS",
        "What is transaction management in DBMS?",
        "Define serializability in database systems",
        "Explain deadlock and deadlock prevention",
        "What is two-phase locking protocol?",
        "Difference between conflict and view serializability",
        "Explain recovery techniques in DBMS",
        "What is concurrency control?",
        "Explain database normalization",
        "What is a schedule in DBMS?"
    ]

    for q in TEST_QUERIES:
        query_chroma(q)
