import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi

# 🔹 Globals
bm25 = None
documents = []
metadata_store = []

# 🔹 Chroma setup
client = chromadb.Client(Settings(persist_directory="./chroma_db"))
collection = client.get_or_create_collection(name="papers")


# 🚀 ADD PAPERS
def add_papers(papers, model):
    global bm25, documents, metadata_store

    existing_ids = set(collection.get()["ids"])

    for i, paper in enumerate(papers):
        doc_id = paper["doi"] or str(i)

        if doc_id in existing_ids:
            continue

        text = f"{paper['title']} {paper.get('abstract', '')}"
        embedding = model.encode(text).tolist()

        clean_metadata = {
            "title": str(paper.get("title", "")),
            "doi": str(paper.get("doi", "")),
            "year": int(paper.get("year") or 0),
            "abstract": str(paper.get("abstract") or ""),
            "citations": int(paper.get("citations") or 0),
            "is_oa": bool(paper.get("is_oa", False)),
            "pdf": str(paper.get("pdf") or ""),
            "publisher": str(paper.get("publisher", ""))
        }

        # store in memory (BM25)
        documents.append(text.split())
        metadata_store.append(clean_metadata)

        # store in Chroma
        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[clean_metadata],
            documents=[text]
        )

    # 🔥 ALWAYS rebuild BM25 after adding
    if documents:
        bm25 = BM25Okapi(documents)


# 🔍 HYBRID SEARCH
def hybrid_search(query, model, k=20):
    global bm25, documents, metadata_store

    # 🔥 rebuild BM25 if missing (on restart)
    if bm25 is None:
        all_data = collection.get()

        documents = []
        metadata_store = []

        for doc, meta in zip(all_data["documents"], all_data["metadatas"]):
            documents.append(doc.split())
            metadata_store.append(meta)

        if documents:
            bm25 = BM25Okapi(documents)
        else:
            return []

    # 🔹 VECTOR SEARCH
    query_embedding = model.encode(query).tolist()

    vector_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    vector_papers = vector_results["metadatas"][0]

    # 🔹 BM25 SEARCH
    tokenized_query = query.split()
    bm25_scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(
        range(len(bm25_scores)),
        key=lambda i: bm25_scores[i],
        reverse=True
    )[:k]

    bm25_papers = [metadata_store[i] for i in top_indices]

    # 🔥 COMBINE
    combined = vector_papers + bm25_papers

    seen = set()
    final_results = []

    for p in combined:
        if p["title"] not in seen:
            final_results.append(p)
            seen.add(p["title"])

    # 🔥 SORT ONCE (outside loop)
    final_results = sorted(
        final_results,
        key=lambda x: x.get("citations", 0),
        reverse=True
    )

    return final_results[:k]