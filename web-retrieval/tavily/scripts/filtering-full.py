import json
import os
import sys
import re
from typing import List, Dict, Any
from datetime import datetime

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
    # os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_parent = os.path.join("..", "outputs", OUTPUT_DIR)
    os.makedirs(output_parent, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage1_2_filtered_{timestamp}.json"
    path = os.path.join(output_parent, filename)

    payload = {
        "query": query,
        "stage": "stage_1_and_2_validation",
        "timestamp_utc": timestamp,
        "num_results": len(results),
        "results": results
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return path


# =========================
# Entry point
# =========================

def main():
    if len(sys.argv) < 2:
        print("Usage: python stage1_2_tavily_filter.py <tavily_response.json>")
        sys.exit(1)

    input_path = sys.argv[1]

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "tavily_response" not in data:
        raise ValueError("Invalid input: missing 'tavily_response'")

    tavily_response = data["tavily_response"]
    original_query = data.get("query", "UNKNOWN_QUERY")

    if "results" not in tavily_response:
        raise ValueError("Invalid Tavily response: missing 'results'")

    # ---- manual syllabus keywords (temporary) ----

    # # should add the feature to add some keywords from query itself
    # syllabus_keywords = [
    #     "pipeline",
    #     "hazard",
    #     "data hazard",
    #     "control hazard",
    #     "structural hazard",
    #     "arm"
    # ]

    # auto keyword detection
    query_keywords = extract_keywords_from_query(original_query)

    raw_results = tavily_response["results"]
    filtered_results = filter_results(raw_results, query_keywords)

    output_path = save_output(original_query, filtered_results)

    print("[STAGE 1 + 2 COMPLETE]")
    print(f"Input results : {len(raw_results)}")
    print(f"Filtered kept : {len(filtered_results)}")
    print(f'keywords detected :{query_keywords}')
    print(f"Output saved : {output_path}")


if __name__ == "__main__":
    main()

# py filtering-full.py ../outputs/tavily_outputs/test-react.json
