import os
import json
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

# ===============================
# CONFIGURATION
# ===============================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOKENIZER_NAME = MODEL_NAME

BATCH_SIZE = 32
MAX_TOKENS = 450          # safe for MiniLM
MIN_TOKENS = 100          # avoid weak embeddings

# ===============================
# PATHS
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHUNKS_PATH = os.path.join(BASE_DIR, "..", "vectors", "chunks.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "vectors", "embeddings.json")

# ===============================
# LOAD MODEL & TOKENIZER
# ===============================

def load_models():
    model = SentenceTransformer(MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
    return model, tokenizer

# ===============================
# EMBEDDING INPUT PREPARATION
# ===============================

def build_embedding_text(chunk: Dict) -> str:
    """
    Construct embedding-safe, context-rich text.
    """
    parts = []

    if chunk.get("book"):
        parts.append(f"Book: {chunk['book']}")

    if chunk.get("chapter"):
        parts.append(f"Chapter: {chunk['chapter']}")

    if chunk.get("section"):
        parts.append(f"Section: {chunk['section']}")

    parts.append("")  # blank line before content
    parts.append(chunk["text"])

    return "\n".join(parts).strip()

# ===============================
# LOAD & VALIDATE CHUNKS
# ===============================

def load_chunks(path: str, tokenizer) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    valid_chunks = []

    for c in chunks:
        raw_text = c.get("text", "").strip()
        if not raw_text:
            continue

        # Build enriched text FIRST
        enriched_text = build_embedding_text(c)

        tokens = tokenizer.encode(
            enriched_text,
            add_special_tokens=False
        )

        # Token-level filtering
        if len(tokens) < MIN_TOKENS:
            continue

        if len(tokens) > MAX_TOKENS:
            tokens = tokens[:MAX_TOKENS]
            enriched_text = tokenizer.decode(tokens)

        c["embedding_text"] = enriched_text
        c["token_count"] = len(tokens)

        valid_chunks.append(c)

    return valid_chunks

# ===============================
# BATCH EMBEDDING
# ===============================

def embed_chunks(chunks: List[Dict], model: SentenceTransformer) -> List[Dict]:
    texts = [c["embedding_text"] for c in chunks]
    embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_embeddings = model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        embeddings.extend(batch_embeddings)

    embedded_chunks = []
    for chunk, vector in zip(chunks, embeddings):
        chunk_out = {
            k: v for k, v in chunk.items()
            if k not in ("embedding_text",)
        }
        chunk_out["embedding"] = vector.tolist()
        embedded_chunks.append(chunk_out)

    return embedded_chunks

# ===============================
# SAVE
# ===============================

def save_embeddings(data: List[Dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    print("🔹 Loading embedding model & tokenizer...")
    model, tokenizer = load_models()

    print("🔹 Loading & validating chunks...")
    chunks = load_chunks(CHUNKS_PATH, tokenizer)
    print(f"✅ Valid chunks: {len(chunks)}")

    print("🔹 Generating embeddings...")
    embedded_chunks = embed_chunks(chunks, model)

    print("🔹 Saving embeddings...")
    save_embeddings(embedded_chunks, OUTPUT_PATH)

    print(f"✅ Embeddings saved to: {OUTPUT_PATH}")
