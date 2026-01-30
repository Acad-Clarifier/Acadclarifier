import json
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# =========================
# Configuration
# =========================

# ---- Stage 1 thresholds ----
MIN_TAVILY_SCORE = 0.6
MIN_CONTENT_CHARS = 800
REQUIRED_FIELDS = {"url", "content", "score"}

# ---- Stage 2 thresholds ----
MIN_KEYWORD_HITS = 1
MAX_PRONOUN_RATIO = 0.02  # conversational tone threshold

OUTPUT_DIR = "validation_outputs"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PARENT = (SCRIPT_DIR / ".." / "outputs" / OUTPUT_DIR).resolve()


# =========================
# Utility helpers
# =========================

# excluded words for detection
STOPWORDS = {
    "what", "why", "how", "when", "where", "who",
    "is", "are", "was", "were", "do", "does", "did",
    "explain", "describe", "define",
    "with", "without", "using",
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "compare", "between"
}


def extract_keywords_from_query(query: str) -> List[str]:
    """
    Extracts meaningful keywords from user query.
    """
    tokens = re.findall(r"\b\w+\b", query.lower())

    keywords = [
        t for t in tokens
        if t not in STOPWORDS and len(t) > 2
    ]

    # remove duplicates while preserving order
    seen = set()
    final_keywords = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            final_keywords.append(k)

    return final_keywords


def normalize_text(text: str) -> str:
    return text.lower()


def count_keyword_hits(text: str, keywords: List[str]) -> int:
    text_l = normalize_text(text)
    return sum(text_l.count(k.lower()) for k in keywords)


def pronoun_ratio(text: str) -> float:
    tokens = re.findall(r"\b\w+\b", text.lower())
    if not tokens:
        return 0.0

    pronouns = {"you", "we", "let", "lets", "your", "our"}
    pronoun_count = sum(1 for t in tokens if t in pronouns)
    return pronoun_count / len(tokens)


def has_structure(text: str) -> bool:
    # paragraph breaks
    if "\n\n" in text:
        return True

    # bullet points
    if re.search(r"^\s*[-•*]\s+", text, flags=re.MULTILINE):
        return True

    # section-like headings (capitalized lines)
    if re.search(r"\n[A-Z][A-Za-z\s]{3,}\n", text):
        return True

    return False


# =========================
# Stage 1: coarse validation
# =========================

def passes_stage1(result: Dict[str, Any]) -> bool:
    try:
        missing = REQUIRED_FIELDS - set(result.keys())
        if missing:
            print(
                f"[STAGE1] Reject {result.get('url')} missing fields: {missing}")
            return False

        score = float(result["score"])
        if score < MIN_TAVILY_SCORE:
            print(
                f"[STAGE1] Reject {result.get('url')} score {score} < {MIN_TAVILY_SCORE}")
            return False

        content_len = len(result["content"].strip())
        if content_len < MIN_CONTENT_CHARS:
            print(
                f"[STAGE1] Reject {result.get('url')} content length {content_len} < {MIN_CONTENT_CHARS}")
            return False

        print(
            f"[STAGE1] Pass {result.get('url')} score={score} len={content_len}")
        return True
    except Exception:
        print(
            f"[STAGE1] Error evaluating result {result.get('url')}:", sys.exc_info()[0])
        return False


# =========================
# Stage 2: quality & syllabus checks
# =========================

def passes_stage2(result: Dict[str, Any], syllabus_keywords: List[str]) -> bool:
    text = result["content"]

    # A. structure check
    structure_ok = has_structure(text)
    if not structure_ok:
        print(f"[STAGE2] Reject {result.get('url')} - no structure detected")
        # Continue to report other metrics for debugging
        keyword_hits = count_keyword_hits(text, syllabus_keywords)
        pr = pronoun_ratio(text)
        print(
            f"[STAGE2] Debug {result.get('url')}: keyword_hits={keyword_hits} pronoun_ratio={pr:.4f}")
        return False

    # B. syllabus keyword alignment
    keyword_hits = count_keyword_hits(text, syllabus_keywords)
    if keyword_hits < MIN_KEYWORD_HITS:
        print(
            f"[STAGE2] Reject {result.get('url')} - keyword_hits {keyword_hits} < {MIN_KEYWORD_HITS} (keywords: {syllabus_keywords})")
        return False

    # C. conversational tone filter
    if pronoun_ratio(text) > MAX_PRONOUN_RATIO:
        pr = pronoun_ratio(text)
        print(
            f"[STAGE2] Reject {result.get('url')} - pronoun_ratio {pr:.4f} > {MAX_PRONOUN_RATIO}")
        return False

    pr = pronoun_ratio(text)
    print(
        f"[STAGE2] Pass {result.get('url')} - hits={keyword_hits} pronoun_ratio={pr:.4f} structure={structure_ok}")
    return True


# =========================
# Core processing
# =========================

def filter_results(
    raw_results: List[Dict[str, Any]],
    syllabus_keywords: List[str]
) -> List[Dict[str, Any]]:

    filtered = []

    for result in raw_results:
        if not passes_stage1(result):
            continue

        if not passes_stage2(result, syllabus_keywords):
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

def save_output(query: str, results: List[Dict[str, Any]]) -> str:
    OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage1_2_filtered_{timestamp}.json"
    path = OUTPUT_PARENT / filename

    payload = {
        "query": query,
        "stage": "stage_1_and_2_validation",
        "timestamp_utc": timestamp,
        "num_results": len(results),
        "results": results
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return str(path)


# =========================
# Entry point
# =========================

def run(input_path: str | None, *, query: str | None = None) -> str:
    """
    Executes Stage 1 & 2 filtering.

    Parameters:
    - input_path: path to Tavily response JSON (required)
    - query: optional override if not present in input JSON
    """

    if not input_path:
        raise ValueError("filtering-full.run requires input_path")

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "tavily_response" not in data:
        raise ValueError("Invalid input: missing 'tavily_response'")

    tavily_response = data["tavily_response"]
    original_query = data.get("query") or query or "UNKNOWN_QUERY"

    if "results" not in tavily_response:
        raise ValueError("Invalid Tavily response: missing 'results'")

    query_keywords = extract_keywords_from_query(original_query)

    raw_results = tavily_response["results"]
    filtered_results = filter_results(raw_results, query_keywords)

    return save_output(original_query, filtered_results)


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    cli_query = sys.argv[2] if len(sys.argv) > 2 else None

    output_path = run(input_path=input_path, query=cli_query)
    print(output_path)


if __name__ == "__main__":
    main()

# py filtering-full.py ../outputs/tavily_outputs/test-react.json
