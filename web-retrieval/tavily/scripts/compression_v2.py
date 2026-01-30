import json
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# =========================
# Configuration
# =========================

MAX_CONTEXT_TOKENS = 900
MIN_RERANK_SCORE = 4.5
OUTPUT_DIR = "final_context_outputs"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PARENT = (SCRIPT_DIR / ".." / "outputs" / OUTPUT_DIR).resolve()

FORUM_MARKERS = [
    "ask question",
    "stack overflow",
    "can anyone",
    "viewed",
    "asked",
    "share",
    "edited",
    "hot network questions"
]

# =========================
# Utilities
# =========================


def estimate_tokens(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def average_rerank_score(chunks: List[Dict[str, Any]]) -> float:
    if not chunks:
        return 0.0

    scores = [c.get("rerank_score", 0) for c in chunks]
    return sum(scores) / len(scores)


def contains_forum_noise(text: str) -> bool:
    t = text.lower()
    return any(marker in t for marker in FORUM_MARKERS)


def is_forum_source(url: str) -> bool:
    return any(site in url for site in ["stackoverflow.com", "stackexchange.com"])


def has_code_mixture(text: str) -> bool:
    """Detect obvious code-heavy chunks that mix code and prose."""

    lines = [ln for ln in text.splitlines() if ln.strip()]

    if not lines:
        return False

    code_like = 0

    for ln in lines:
        stripped = ln.strip()

        if stripped.startswith(("def ", "class ", "function ")):
            code_like += 1
            continue

        if "{" in stripped or "}" in stripped:
            code_like += 1
            continue

        if stripped.startswith(("#", "//")):
            code_like += 1
            continue

        if "();" in stripped or stripped.endswith("();"):
            code_like += 1
            continue

        if re.search(r"\bfor\b|\bwhile\b|\bif\b.*:|=>", stripped):
            code_like += 1

    return code_like / len(lines) >= 0.35


# =========================
# Stage 6 Decision Logic
# =========================

def should_run_stage6(chunks: List[Dict[str, Any]]) -> bool:
    """
    Decide whether Stage 6 compression is required.
    """
    if not chunks:
        return False

    total_tokens = sum(c.get("token_estimate", estimate_tokens(
        c.get("chunk_text", ""))) for c in chunks)
    avg_rerank = average_rerank_score(chunks)

    # Compression triggers (any → compress)
    compression_triggers = [
        total_tokens > MAX_CONTEXT_TOKENS,
        len(chunks) > 3,
        avg_rerank < MIN_RERANK_SCORE,
        any(is_forum_source(c.get("source", "")) for c in chunks),
        any(contains_forum_noise(c.get("chunk_text", "")) for c in chunks),
        any(has_code_mixture(c.get("chunk_text", "")) for c in chunks)
    ]

    return any(compression_triggers)


# =========================
# Safe Compression Logic
# =========================

def compress_context(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Conservative compression:
    - Remove forum/question chunks
    - Keep full explanation blocks
    - Enforce token budget
    """

    # Hard filter: forum/Q&A chunks are removed and never reintroduced
    non_forum = [
        c for c in chunks
        if not is_forum_source(c.get("source", ""))
        and not contains_forum_noise(c.get("chunk_text", ""))
    ]

    # Drop low-quality after forum removal
    cleaned = [c for c in non_forum if c.get(
        "rerank_score", 0) >= MIN_RERANK_SCORE]

    if not cleaned:
        # Fallback: keep highest scoring from the already non-forum set
        cleaned = sorted(non_forum, key=lambda x: x.get(
            "rerank_score", 0), reverse=True)

    # Sort by rerank score so the best blocks survive trimming
    cleaned.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

    final = []
    used_tokens = 0

    for c in cleaned:
        tokens = c.get("token_estimate", estimate_tokens(
            c.get("chunk_text", "")))

        if used_tokens + tokens > MAX_CONTEXT_TOKENS:
            break

        final.append({
            "text": c.get("chunk_text", ""),
            "source": c.get("source", ""),
            "confidence": round(
                0.6 * c.get("rerank_score", 0) +
                0.4 * c.get("similarity", 0),
                3
            )
        })

        used_tokens += tokens

    return final


# =========================
# Pass-through Logic
# =========================

def passthrough_context(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Directly forward chunks to LLM context.
    """
    return [
        {
            "text": c["chunk_text"],
            "source": c["source"],
            "confidence": round(
                0.6 * c.get("rerank_score", 0) +
                0.4 * c.get("similarity", 0),
                3
            )
        }
        for c in chunks
    ]


# =========================
# Persistence
# =========================

def save_final_context(query: str, context: List[Dict[str, Any]], mode: str) -> str:
    OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage6_context_{mode}_{timestamp}.json"
    path = OUTPUT_PARENT / filename

    payload = {
        "query": query,
        "stage": "stage_6_context_guard",
        "mode": mode,
        "timestamp_utc": timestamp,
        "num_blocks": len(context),
        "web_context": context
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return str(path)


# =========================
# Entry point
# =========================

def run(input_path: str | None, *, query: str | None = None) -> str:
    """
    Executes Stage 6 context guard / compression.

    Parameters:
    - input_path: path to Stage 5 reranked JSON (required)
    - query: optional override if not present in input JSON
    """

    if not input_path:
        raise ValueError("compression_v2.run requires input_path")

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "chunks" not in data:
        raise ValueError("Invalid input: missing 'chunks'")

    resolved_query = data.get("query") or query or "UNKNOWN_QUERY"
    chunks = data["chunks"]

    if should_run_stage6(chunks):
        context = compress_context(chunks)
        mode = "compressed"
    else:
        context = passthrough_context(chunks)
        mode = "passthrough"

    return save_final_context(resolved_query, context, mode)


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    cli_query = sys.argv[2] if len(sys.argv) > 2 else None

    output_path = run(input_path=input_path, query=cli_query)
    print(output_path)


if __name__ == "__main__":
    main()
