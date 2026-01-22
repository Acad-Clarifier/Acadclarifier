import json
import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# =========================
# Configuration (Stage 1 only)
# =========================

MIN_TAVILY_SCORE = 0.6          # coarse relevance threshold
MIN_CONTENT_CHARS = 800         # drop very short / shallow pages
REQUIRED_FIELDS = {"url", "content", "score"}

OUTPUT_DIR = "stage1_outputs"


# =========================
# Validation helpers
# =========================

def is_valid_result(result: Dict[str, Any]) -> bool:
    """
    Checks whether a Tavily result has required fields.
    """
    return REQUIRED_FIELDS.issubset(result.keys())


def passes_coarse_filters(result: Dict[str, Any]) -> bool:
    """
    Applies Stage-1 coarse filters:
    - Tavily score threshold
    - Minimum content length
    """
    try:
        score_ok = float(result["score"]) >= MIN_TAVILY_SCORE
        content_ok = len(result["content"].strip()) >= MIN_CONTENT_CHARS
        return score_ok and content_ok
    except Exception:
        return False


# =========================
# Core processing
# =========================

def filter_tavily_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Applies validation + coarse filtering to Tavily results.
    """
    filtered = []

    for idx, result in enumerate(raw_results):
        if not is_valid_result(result):
            continue

        if not passes_coarse_filters(result):
            continue

        filtered.append(
            {
                "url": result["url"],
                "score": result["score"],
                "content": result["content"]
            }
        )

    return filtered


# =========================
# Persistence
# =========================

def save_filtered_output(
    original_query: str,
    filtered_results: List[Dict[str, Any]]
) -> str:
    """
    Saves filtered Tavily results to a timestamped JSON file.
    """
    # Ensure the sibling tavily_outputs/<OUTPUT_DIR> exists (store outputs alongside tavily outputs)
    output_parent = os.path.join("..", "tavily_outputs", OUTPUT_DIR)
    os.makedirs(output_parent, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage1_filtered_{timestamp}.json"
    file_path = os.path.join(output_parent, filename)

    payload = {
        "query": original_query,
        "stage": "stage_1_coarse_filtering",
        "timestamp_utc": timestamp,
        "num_results": len(filtered_results),
        "results": filtered_results
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return file_path


# =========================
# Entry point
# =========================

def main():
    if len(sys.argv) < 2:
        print("Usage: python stage1_tavily_filter.py <tavily_response.json>")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "tavily_response" not in data:
        raise ValueError("Invalid input JSON: missing 'tavily_response'")

    tavily_response = data["tavily_response"]
    original_query = data.get("query", "UNKNOWN_QUERY")

    if "results" not in tavily_response:
        raise ValueError("Invalid Tavily response: missing 'results'")

    raw_results = tavily_response["results"]

    filtered_results = filter_tavily_results(raw_results)

    output_path = save_filtered_output(original_query, filtered_results)

    print("[STAGE 1 COMPLETE]")
    print(f"Input results : {len(raw_results)}")
    print(f"Filtered kept : {len(filtered_results)}")
    print(f"Output saved : {output_path}")


if __name__ == "__main__":
    main()

# Output command: py filtering.py ../tavily_outputs/test.json
