import json
import os
import sys
import re
from typing import List, Dict, Any
from datetime import datetime

# =========================
# Configuration
# =========================

MIN_TOKENS = 200
MAX_TOKENS = 300
OVERLAP_RATIO = 0.25          # 25% overlap
OUTPUT_DIR = "chunking_outputs"


# =========================
# Token utilities
# =========================

def estimate_tokens(text: str) -> int:
    """
    Approximate token count using word count.
    """
    return len(re.findall(r"\b\w+\b", text))

# These 2 functions are giving wrong outputs

# def split_into_paragraphs(text: str) -> List[str]:
#     """
#     Splits text into paragraph-like blocks.
#     """
#     blocks = [p.strip() for p in text.split("\n\n") if p.strip()]
#     return blocks


# def split_by_headings(text: str) -> List[str]:
#     """
#     Attempts to split text using section-like headings.
#     """
#     pattern = r"\n[A-Z][A-Za-z0-9\s\-]{3,}\n"
#     splits = re.split(pattern, text)

#     cleaned = [s.strip() for s in splits if s.strip()]
#     return cleaned

# Alternate to above 2 functions [split_by_headings() + split_into_paragraphs()]

def normalize_blocks(text: str) -> List[str]:
    """
    Robust paragraph normalization for web text.
    """
    # Normalize line breaks
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"\n+", "\n", text)

    # Split on double newline OR sentence breaks
    blocks = re.split(r"\n\n|(?<=\.)\s+(?=[A-Z])", text)

    return [b.strip() for b in blocks if b.strip()]

# =========================
# Chunking logic
# =========================


def chunk_blocks(blocks: List[str]) -> List[str]:
    """
    Applies sliding-window chunking over blocks.
    """
    chunks = []
    window = []
    window_tokens = 0

    overlap_tokens = int(MIN_TOKENS * OVERLAP_RATIO)

    for block in blocks:
        block_tokens = estimate_tokens(block)

        # Skip pathological blocks
        if block_tokens == 0:
            continue

        # If block itself is too large, split internally
        if block_tokens > MAX_TOKENS:
            words = block.split()
            for i in range(0, len(words), MAX_TOKENS):
                sub_block = " ".join(words[i:i + MAX_TOKENS])
                chunks.append(sub_block)
            continue

        # Normal sliding window
        if window_tokens + block_tokens <= MAX_TOKENS:
            window.append(block)
            window_tokens += block_tokens
        else:
            # finalize current chunk
            if window_tokens >= MIN_TOKENS:
                chunks.append("\n\n".join(window))

            # create overlap
            overlap = []
            overlap_count = 0
            for w in reversed(window):
                w_tokens = estimate_tokens(w)
                overlap.insert(0, w)
                overlap_count += w_tokens
                if overlap_count >= overlap_tokens:
                    break

            window = overlap + [block]
            window_tokens = sum(estimate_tokens(w) for w in window)

    # Handle remaining content intelligently
    if window:
        window_text = "\n\n".join(window)

        # If last window is too small, try to merge with previous chunk
        if window_tokens < MIN_TOKENS and chunks:
            last_chunk = chunks[-1]
            last_chunk_tokens = estimate_tokens(last_chunk)
            combined_tokens = last_chunk_tokens + window_tokens

            # Allow up to 50% overflow to avoid orphan chunks
            if combined_tokens <= int(MAX_TOKENS * 1.5):
                chunks[-1] = last_chunk + "\n\n" + window_text
            else:
                # Can't merge, emit as separate chunk (better than losing content)
                chunks.append(window_text)
        else:
            # Window meets MIN_TOKENS or no previous chunk exists
            chunks.append(window_text)

    return chunks


# =========================
# Core processing
# =========================

# def chunk_document(result: Dict[str, Any]) -> List[Dict[str, Any]]:
#     """
#     Chunks a single filtered Tavily result.
#     """
#     text = result["content"]
#     source = result["url"]
#     score = result["score"]

#     # Try heading-based split first
#     # sections = split_by_headings(text)

#     # Fallback to paragraph split
#     if len(sections) <= 1:
#         sections = normalize_blocks(text)

#     all_chunks = []
#     section_index = 0

#     for section in sections:
#         # blocks = split_into_paragraphs(section)
#         # chunks = chunk_blocks(blocks)
#         blocks = normalize_blocks(text)
#         chunks = chunk_blocks(blocks)

#         for chunk in chunks:
#             all_chunks.append(
#                 {
#                     "chunk_text": chunk,
#                     "source": source,
#                     "tavily_score": score,
#                     "section_index": section_index,
#                     "token_estimate": estimate_tokens(chunk)
#                 }
#             )

#         section_index += 1

#     return all_chunks

def chunk_document(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = result["content"]
    source = result["url"]
    score = result["score"]

    blocks = normalize_blocks(text)
    chunks = chunk_blocks(blocks)

    output = []
    for i, chunk in enumerate(chunks):
        output.append({
            "chunk_text": chunk,
            "source": source,
            "tavily_score": score,
            "section_index": i,
            "token_estimate": estimate_tokens(chunk)
        })

    return output


def merge_small_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Post-process to merge chunks smaller than MIN_TOKENS with adjacent chunks.
    Allows up to 50% overflow on MAX_TOKENS to prevent orphan chunks.
    """
    if not chunks:
        return chunks

    merged = []
    i = 0

    while i < len(chunks):
        current = chunks[i]
        current_tokens = current["token_estimate"]

        # If current chunk is too small
        if current_tokens < MIN_TOKENS:
            # Try to merge with previous chunk (if exists and same source)
            if merged and merged[-1]["source"] == current["source"]:
                prev = merged[-1]
                combined_tokens = prev["token_estimate"] + current_tokens

                # Allow up to 50% overflow - better to have one larger chunk than orphans
                if combined_tokens <= int(MAX_TOKENS * 1.5):
                    merged[-1]["chunk_text"] += "\n\n" + current["chunk_text"]
                    merged[-1]["token_estimate"] = combined_tokens
                    i += 1
                    continue

            # Try to merge with next chunk (if exists and same source)
            if i + 1 < len(chunks) and chunks[i + 1]["source"] == current["source"]:
                next_chunk = chunks[i + 1]
                combined_tokens = current_tokens + next_chunk["token_estimate"]

                # Allow 50% overflow
                if combined_tokens <= int(MAX_TOKENS * 1.5):
                    current["chunk_text"] += "\n\n" + next_chunk["chunk_text"]
                    current["token_estimate"] = combined_tokens
                    merged.append(current)
                    i += 2  # Skip the next chunk since we merged it
                    continue

            # Can't merge, keep as is (prioritize content preservation)
            merged.append(current)
        else:
            # Chunk meets minimum size
            merged.append(current)

        i += 1

    return merged


def process_stage2_results(stage2_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Applies chunking to all Stage-2 filtered results.
    """
    results = stage2_data["results"]
    final_chunks = []

    for result in results:
        final_chunks.extend(chunk_document(result))

    # Post-process to merge small chunks
    final_chunks = merge_small_chunks(final_chunks)

    return final_chunks


# =========================
# Persistence
# =========================

def save_chunks(query: str, chunks: List[Dict[str, Any]]) -> str:
    # os.makedirs(OUTPUT_DIR, exist_ok=True)

    output_parent = os.path.join("..", "outputs", OUTPUT_DIR)
    os.makedirs(output_parent, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage3_chunks_{timestamp}.json"
    path = os.path.join(output_parent, filename)

    payload = {
        "query": query,
        "stage": "stage_3_chunking",
        "timestamp_utc": timestamp,
        "num_chunks": len(chunks),
        "chunks": chunks
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return path


# =========================
# Entry point
# =========================

def main():
    if len(sys.argv) < 2:
        print("Usage: python stage3_chunker.py <stage1_2_filtered.json>")
        sys.exit(1)

    input_path = sys.argv[1]

    with open(input_path, "r", encoding="utf-8") as f:
        stage2_data = json.load(f)

    if "results" not in stage2_data:
        raise ValueError("Invalid input: missing 'results'")

    query = stage2_data.get("query", "UNKNOWN_QUERY")

    chunks = process_stage2_results(stage2_data)
    output_path = save_chunks(query, chunks)

    print("[STAGE 3 COMPLETE]")
    print(f"Total chunks created : {len(chunks)}")
    print(f"Output saved         : {output_path}")


if __name__ == "__main__":
    main()
