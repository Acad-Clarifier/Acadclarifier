import os
import json
from typing import List, Dict
from sentence_transformers import SentenceTransformer

# -------------------------------
# CONFIGURATION
# -------------------------------

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32
MAX_CHARS = 3000      # safety limit (model-independent)
MIN_CHARS = 50        # avoid junk embeddings

# -------------------------------
# PATH RESOLUTION
# -------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHUNKS_PATH = os.path.join(BASE_DIR, "..", "vectors", "chunks.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "vectors", "embeddings.json")

# -------------------------------
# LOAD MODEL
# -------------------------------

def load_embedding_model():
    """
    Load embedding model deterministically.
    """
    model = SentenceTransformer(MODEL_NAME)
    return model

# -------------------------------
# LOAD & VALIDATE CHUNKS
# -------------------------------

def load_chunks(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    valid_chunks = []

    for c in chunks:
        text = c.get("text", "").strip()

        # Skip empty or junk chunks
        if len(text) < MIN_CHARS:
            continue

        # Hard cap text length (extra safety)
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS]
            c["text"] = text

        valid_chunks.append(c)

    return valid_chunks

# -------------------------------
# BATCHED EMBEDDING
# -------------------------------

def embed_chunks(chunks: List[Dict], model: SentenceTransformer) -> List[Dict]:
    texts = [c["text"] for c in chunks]
    embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]

        batch_embeddings = model.encode(
            batch,
            show_progress_bar=False,
            normalize_embeddings=True
        )

        embeddings.extend(batch_embeddings)

    # Attach embeddings back to metadata
    embedded_chunks = []
    for chunk, vector in zip(chunks, embeddings):
        embedded_chunks.append({
            **chunk,
            "embedding": vector.tolist()
        })

    return embedded_chunks

# -------------------------------
# SAVE OUTPUT
# -------------------------------

def save_embeddings(data: List[Dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# -------------------------------
# MAIN PIPELINE
# -------------------------------

if __name__ == "__main__":
    print("🔹 Loading chunks...")
    chunks = load_chunks(CHUNKS_PATH)
    print(f"✅ Valid chunks: {len(chunks)}")

    print("🔹 Loading embedding model...")
    model = load_embedding_model()

    print("🔹 Generating embeddings...")
    embedded_chunks = embed_chunks(chunks, model)

    print("🔹 Saving embeddings...")
    save_embeddings(embedded_chunks, OUTPUT_PATH)

    print(f"✅ Embeddings saved to: {OUTPUT_PATH}")
