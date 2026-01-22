import os
import json
import sys
from datetime import datetime
from typing import Dict, Any

import urllib.request
import urllib.error
import urllib.parse

# =========================
# Configuration
# =========================

# TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
# TAVILY_API_KEY = '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'  # uselessbear99
# jsoham672 - student plan
TAVILY_API_KEY = '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'
TAVILY_ENDPOINT = "https://api.tavily.com/search"

OUTPUT_DIR = "tavily_outputs"

if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY environment variable not set")


# =========================
# Core function
# =========================

def fetch_from_tavily(query: str) -> Dict[str, Any]:
    """
    Calls Tavily API with the given query and returns raw JSON response.
    """

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        # options: basic (1cr), fast(1cr), ultra-fast(1cr), advanced(2cr)
        "search_depth": "advanced",
        "max_results": 5,
        "include_answer": False,
        "include_raw_content": False
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        TAVILY_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.getcode()
            content = resp.read().decode("utf-8")
            if status >= 400:
                raise RuntimeError(
                    f"Tavily API request failed with status {status}: {content}")
            return json.loads(content)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        raise RuntimeError(
            f"Tavily API request failed: HTTP {e.code} {e.reason}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Tavily API request failed: {getattr(e, 'reason', e)}")


# =========================
# Persistence
# =========================

def save_response(query: str, response_json: Dict[str, Any]) -> str:
    """
    Saves Tavily response to a timestamped JSON file.
    """
    output_parent = os.path.join("..", "outputs", OUTPUT_DIR)
    os.makedirs(output_parent, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c for c in query if c.isalnum()
                         or c in (" ", "_"))[:50]
    filename = f"tavily_response_{safe_query}_{timestamp}.json"

    # output_dir = "tavily_outputs"
    # os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_parent, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "query": query,
                "timestamp_utc": timestamp,
                "tavily_response": response_json
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    return file_path


# =========================
# Entry point
# =========================

def main():
    # UNCOMMENT FOR REAL QUERY
    # if len(sys.argv) < 2:
    #     print("Usage: python tavily_fetch.py \"your query here\"")
    #     sys.exit(1)

    # query = sys.argv[1].strip()
    # -------------------------------------------------------------------

    # TEMP: hardcoded query for testing
    # query = "Explain ARM pipeline hazards with examples"
    # query = "Compare the differences between REST and GraphQL APIs"
    # query = "What recent changes were introduced in React 19?"
    # query = "Explain how vector databases internally optimize similarity search at scale."
    # query = "How to securely store API keys in a Node.js production environment?"
    query = "Is MongoDB okay for storing embeddings?"

    print(f"[INFO] Fetching Tavily results for query: {query}")

    if not query:
        raise ValueError("Query cannot be empty")

    print(f"[INFO] Fetching Tavily results for query: {query}")

    response_json = fetch_from_tavily(query)
    file_path = save_response(query, response_json)

    print(f"[SUCCESS] Tavily response saved to: {file_path}")


if __name__ == "__main__":
    main()
