import os
import json
import chromadb
from chromadb.config import Settings

# -------------------------------
# PATH CONFIGURATION
# -------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EMBEDDINGS_PATH = os.path.join(
    BASE_DIR, "..", "vectors", "embeddings.json"
)

CHROMA_DIR = os.path.join(
    BASE_DIR, "..", "chroma_store"
)

COLLECTION_NAME = "academic_textbook_chunks"

# -------------------------------
# LOAD EMBEDDINGS JSON
# -------------------------------

def load_embeddings(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
# -------------------------------
# SANITIZE METADATA FOR BULL VALUES
# -------------------------------    
    
def sanitize_metadata(metadata: dict) -> dict:
    """
    Replace None values with ChromaDB-safe defaults.
    """
    clean = {}
    for k, v in metadata.items():
        if v is None:
            clean[k] = ""
        else:
            clean[k] = v
    return clean


# -------------------------------
# PREPARE DATA FOR CHROMA
# -------------------------------

def prepare_chroma_inputs(data):
    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for global_idx, item in enumerate(data):
        # ---------- ID ----------
        raw_section = item.get("section") or "no_section"
        section_clean = (
            raw_section
            .replace(" ", "_")
            .replace(".", "_")
            .lower()
        )

        chunk_id = (
            f"{item['book']}__"
            f"{section_clean}__"
            f"chunk_{global_idx:06d}"
        )

        # ---------- DOCUMENT ----------
        text = item["text"]
        vector = item["embedding"]

        # ---------- METADATA ----------
        metadata = {
            k: v for k, v in item.items()
            if k not in ("text", "embedding", "images")
        }

        # Images → JSON string (Chroma-safe)
        images = item.get("images")
        if images:
            metadata["images"] = json.dumps(images)
        else:
            metadata["images"] = ""

        metadata = sanitize_metadata(metadata)

        # ---------- APPEND (CRITICAL) ----------
        ids.append(chunk_id)
        documents.append(text)
        embeddings.append(vector)
        metadatas.append(metadata)

    # ---------- FINAL SAFETY CHECK ----------
    assert len(ids) == len(documents) == len(embeddings) == len(metadatas), \
        f"Length mismatch: ids={len(ids)}, docs={len(documents)}, emb={len(embeddings)}, meta={len(metadatas)}"

    return ids, documents, embeddings, metadatas




# -------------------------------
# INGEST INTO CHROMA
# -------------------------------

def ingest_into_chroma(ids, documents, embeddings, metadatas):
    client = chromadb.Client(
        Settings(
            persist_directory=CHROMA_DIR,
            anonymized_telemetry=False
        )
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )


# -------------------------------
# MAIN
# -------------------------------

if __name__ == "__main__":
    print("🔹 Loading embeddings.json...")
    data = load_embeddings(EMBEDDINGS_PATH)

    print("🔹 Preparing data for ChromaDB...")
    ids, documents, embeddings, metadatas = prepare_chroma_inputs(data)

    print("🔹 Ingesting into ChromaDB...")
    ingest_into_chroma(ids, documents, embeddings, metadatas)

    print(f"✅ Ingestion complete!")
    print(f"📦 Collection: {COLLECTION_NAME}")
    print(f"📁 Stored at: {CHROMA_DIR}")
