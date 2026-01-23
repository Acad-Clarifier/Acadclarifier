import os
import json
import chromadb

# ===============================
# PATH CONFIGURATION
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EMBEDDINGS_PATH = os.path.join(
    BASE_DIR, "..", "vectors", "embeddings.json"
)

CHROMA_DIR = os.path.join(
    BASE_DIR, "..", "chroma_store"
)

COLLECTION_NAME = "academic_textbook_chunks"
EXPECTED_EMBED_DIM = 384   # MiniLM-L6-v2

# ===============================
# LOAD EMBEDDINGS
# ===============================

def load_embeddings(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ===============================
# METADATA SANITIZATION
# ===============================

def sanitize_metadata(metadata: dict) -> dict:
    clean = {}
    for k, v in metadata.items():
        clean[k] = "" if v is None else v
    return clean

# 🔹 Assign high-level topic (used for intent filtering)
    chapter_text = (
    (item.get("chapter") or "") +
    " " +
    (item.get("section") or "")
 ).lower()

    if any(k in chapter_text for k in ["acid", "transaction", "serializ"]):
        metadata["topic"] = "transaction"
    elif any(k in chapter_text for k in ["concurr", "lock", "deadlock"]):
        metadata["topic"] = "concurrency"
    elif any(k in chapter_text for k in ["recovery", "logging", "crash"]):
        metadata["topic"] = "recovery"
    else:
        metadata["topic"] = "general"

# ===============================
# PREPARE CHROMA INPUTS
# ===============================

def prepare_chroma_inputs(data):
    ids, documents, embeddings, metadatas = [], [], [], []

    for global_idx, item in enumerate(data):
        # -------- ID --------
        section = item.get("section") or "no_section"
        section_clean = section.replace(" ", "_").replace(".", "_").lower()

        chunk_id = (
            f"{item['book']}__{section_clean}__chunk_{global_idx:06d}"
        )

        # -------- EMBEDDING --------
        vector = item["embedding"]
        if len(vector) != EXPECTED_EMBED_DIM:
            raise ValueError(
                f"Invalid embedding dim {len(vector)} for {chunk_id}"
            )

        # -------- DOCUMENT --------
        # IMPORTANT: store the SAME text that was embedded
        text = item.get("embedding_text") or item["text"]

        # -------- METADATA (WHITELIST) --------
        metadata = {
            "book": item.get("book"),
            "chapter": item.get("chapter"),
            "section": item.get("section"),
            "page_start": item.get("page_start"),
            "page_end": item.get("page_end"),
        }

        metadata = sanitize_metadata(metadata)

        ids.append(chunk_id)
        documents.append(text)
        embeddings.append(vector)
        metadatas.append(metadata)

    assert len(ids) == len(documents) == len(embeddings) == len(metadatas)

    return ids, documents, embeddings, metadatas

# ===============================
# INGEST
# ===============================

def ingest_into_chroma(ids, documents, embeddings, metadatas):
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    # 🔒 Prevent accidental duplicate ingestion
    existing = set(collection.get(ids=ids)["ids"]) if collection.count() else set()
    if existing:
        print(f"⚠️ Skipping {len(existing)} already-ingested chunks")

    filtered = [
        (i, d, e, m)
        for i, d, e, m in zip(ids, documents, embeddings, metadatas)
        if i not in existing
    ]

    if not filtered:
        print("✅ Nothing new to ingest")
        return

    ids, documents, embeddings, metadatas = zip(*filtered)

    collection.add(
        ids=list(ids),
        documents=list(documents),
        embeddings=list(embeddings),
        metadatas=list(metadatas)
    )

    print("✅ ChromaDB persisted to disk")
    print("Total chunks stored:", collection.count())

# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    print("🔹 Loading embeddings.json...")
    data = load_embeddings(EMBEDDINGS_PATH)

    print("🔹 Preparing Chroma inputs...")
    ids, documents, embeddings, metadatas = prepare_chroma_inputs(data)

    print("🔹 Ingesting into ChromaDB...")
    ingest_into_chroma(ids, documents, embeddings, metadatas)

    print("📦 Collection:", COLLECTION_NAME)
    print("📁 Chroma path:", CHROMA_DIR)
