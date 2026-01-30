import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import urllib.request
import urllib.error
import urllib.parse

# =========================
# Configuration
# =========================

TAVILY_ENDPOINT = "https://api.tavily.com/search"

OUTPUT_DIR = "tavily_outputs"

# Resolve outputs relative to this script so execution is cwd-agnostic
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PARENT = (SCRIPT_DIR / ".." / "outputs" / OUTPUT_DIR).resolve()


def _load_env() -> None:
    """Load .env variables if present (no external dependency)."""
    for candidate in (SCRIPT_DIR.parent / ".env", SCRIPT_DIR / ".env"):
        if not candidate.exists():
            continue
        with open(candidate, "r", encoding="utf-8") as f:
            for line in f.readlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
        break


_load_env()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


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
    OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c for c in query if c.isalnum()
                         or c in (" ", "_"))[:50]
    filename = f"tavily_response_{safe_query}_{timestamp}.json"

    file_path = OUTPUT_PARENT / filename

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

    return str(file_path)


# =========================
# Entry point
# =========================

def run(input_path: str | None, *, query: str | None = None) -> str:
    """
    Executes Tavily fetch stage.

    Parameters:
    - input_path: must be None for this stage
    - query: required user query
    """

    if input_path not in (None, ""):
        raise ValueError(
            "tavily_fetch.run does not accept input_path; pass None")

    if not query or not query.strip():
        raise ValueError("Query is required for tavily_fetch stage")

    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not configured")

    response_json = fetch_from_tavily(query.strip())
    return save_response(query.strip(), response_json)


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    cli_query = sys.argv[2] if len(sys.argv) > 2 else None

    output_path = run(input_path=input_path, query=cli_query)
    print(output_path)


if __name__ == "__main__":
    main()
