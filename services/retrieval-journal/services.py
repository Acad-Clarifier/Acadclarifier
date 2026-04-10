import asyncio
import os
import logging
import threading
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_LOCK = threading.Lock()


def get_model():
    global _MODEL

    if _MODEL is not None:
        return _MODEL

    with _MODEL_LOCK:
        if _MODEL is None:
            try:
                _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as exc:  # pragma: no cover - runtime fallback
                logger.exception(
                    "Failed to load journal embedding model: %s", exc)
                return None

    return _MODEL


# 🌐 Semantic Scholar Fetch

SEMANTIC_API_KEY = os.getenv("SEMANTIC_API_KEY", "").strip()
query_cache = {}


async def fetch_semantic_scholar(client, query):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"

    params = {
        "query": query,
        "limit": 20,
        "fields": "title,year,abstract,authors,venue,citationCount,openAccessPdf"
    }

    headers = {
        "User-Agent": "acadclarifier/1.0",
        "Accept": "application/json",
    }

    if SEMANTIC_API_KEY:
        headers["x-api-key"] = SEMANTIC_API_KEY

    try:
        # 🔥 RATE LIMIT PROTECTION (1 req/sec)
        await asyncio.sleep(0.2)

        res = await client.get(url, params=params, headers=headers, timeout=15)

        print("Semantic Status:", res.status_code)

        if res.status_code != 200:
            print("Semantic Error:", res.text)
            return []

        data = res.json()

        papers = []

        for item in data.get("data", []):
            paper = {
                "title": item.get("title"),
                "doi": item.get("paperId"),
                "year": item.get("year"),
                "abstract": item.get("abstract"),
                "citations": item.get("citationCount", 0),
                "publisher": item.get("venue", ""),
                "is_oa": bool(item.get("openAccessPdf")),
                "pdf": (item.get("openAccessPdf") or {}).get("url")
            }

            papers.append(paper)

        return papers

    except Exception as e:
        print("Semantic Scholar Error:", e)
        return []


async def fetch_openalex(client, query):
    url = "https://api.openalex.org/works"

    params = {
        "search": query,
        "per_page": 20
    }

    try:
        res = await client.get(url, params=params, timeout=15)

        print("OpenAlex Status:", res.status_code)

        if res.status_code != 200:
            print("OpenAlex Error:", res.text)
            return []

        data = res.json()
        papers = []

        for item in data.get("results", []):

            # 🔥 FIX: Convert abstract
            abstract_dict = item.get("abstract_inverted_index")
            abstract = ""

            if abstract_dict:
                words = sorted(
                    [(pos, word) for word, positions in abstract_dict.items()
                     for pos in positions]
                )
                abstract = " ".join([word for _, word in words])

            paper = {
                "title": item.get("title"),
                "doi": item.get("id"),
                "year": item.get("publication_year"),
                "abstract": abstract,
                "citations": item.get("cited_by_count", 0),
                "publisher": (item.get("host_venue") or {}).get("publisher", ""),
                "is_oa": (item.get("open_access") or {}).get("is_oa", False),
                "pdf": (item.get("open_access") or {}).get("oa_url")
            }

            papers.append(paper)

        return papers

    except Exception as e:
        print("OpenAlex Error:", e)
        return []


# 🔍 Filter Function
def filter_papers(papers, filter_type):
    if filter_type == "open_access":
        return [p for p in papers if p.get("is_oa")]

    elif filter_type == "subscription":
        known_subscription = [
            p for p in papers
            if any(pub in (p.get("publisher") or "").lower()
                   for pub in [
                       "ieee",
                       "electrical and electronics engineers",
                       "elsevier",
                       "springer"
            ])
        ]

        if known_subscription:
            return known_subscription

        # Fallback for entries where publisher metadata is missing.
        return [p for p in papers if not p.get("is_oa")]

    else:
        return papers


# 🚀 MAIN PIPELINE
async def search_papers(query: str, filter_type: str = "all"):

    async with httpx.AsyncClient() as client:

        # 🔥 Step 1: Fetch papers

        # check cache
        if query in query_cache:
            print("Using cached results")
            papers = query_cache[query]
        else:
            papers = await fetch_semantic_scholar(client, query)
            print("FETCHED PAPERS:", len(papers))

            if not papers:
                papers = await fetch_openalex(client, query)
                print("Using OpenAlex fallback")

                query_cache[query] = papers

        # 🔁 Step 2: Remove duplicates
        seen = set()
        unique_papers = []

        for p in papers:
            if p["title"] not in seen:
                unique_papers.append(p)
                seen.add(p["title"])

        papers = unique_papers

        model = get_model()
        if model is None:
            return {"results": filter_papers(papers, filter_type)}

        # 🧠 Step 3: Store + Hybrid Search (optional fallback when Chroma is unavailable)
        try:
            from vector_store import add_papers, hybrid_search
            add_papers(papers, model)  # safe (no duplicates)
            papers = hybrid_search(query, model)
        except Exception as exc:  # pragma: no cover - runtime fallback
            logger.warning(
                "Vector rerank unavailable, using source ranking only: %s", exc
            )

        # 🎯 Step 4: Apply filter
        papers = filter_papers(papers, filter_type)

        return {"results": papers}
