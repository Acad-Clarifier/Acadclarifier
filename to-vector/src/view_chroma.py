import os
import chromadb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CHROMA_DIR = os.path.join(
    BASE_DIR, "..", "chroma_store"
)

COLLECTION_NAME = "academic_textbook_chunks"

client = chromadb.PersistentClient(path=CHROMA_DIR)

print("Using Chroma directory:", CHROMA_DIR)

collection = client.get_collection(name=COLLECTION_NAME)

print("Total chunks stored:", collection.count())

# Fetch first 5 chunks
results = collection.get(
    limit=5,
    include=["documents", "metadatas"]
)

for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
    print("\n----------------------------")
    print(f"Chunk {i+1}")
    print("Text (first 300 chars):")
    print(doc[:300])
    print("\nMetadata:")
    for k, v in meta.items():
        print(f"  {k}: {v}")
