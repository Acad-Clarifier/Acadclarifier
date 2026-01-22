import os
import chromadb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CHROMA_DIR = os.path.join(BASE_DIR, "..", "chroma_store")
COLLECTION_NAME = "academic_textbook_chunks"

client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_collection(name=COLLECTION_NAME)

query = "What are the different types of data models?"

results = collection.query(
    query_texts=[query],
    n_results=5,
    include=["documents", "metadatas", "distances"]
)

print("Query:", query)

for i in range(len(results["documents"][0])):
    print("\n-----------------------------")
    print(f"Result {i+1}")
    print("Distance:", results["distances"][0][i])
    print("Text (first 400 chars):")
    print(results["documents"][0][i][:400])
    print("Metadata:")
    for k, v in results["metadatas"][0][i].items():
        print(f"  {k}: {v}")
