import re
import json
from typing import List, Dict
from transformers import AutoTokenizer

# ===============================
# CONFIGURATION
# ===============================

BOOK_ID = "book_1"
TOKENIZER_NAME = "sentence-transformers/all-MiniLM-L6-v2"

WINDOW_SIZE = 400          # slightly larger for theory
OVERLAP = 80               # ~20% overlap
MIN_CHUNK_TOKENS = 120     # avoid weak chunks

tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

# ===============================
# STRUCTURAL DETECTION
# ===============================

CHAPTER_MD = re.compile(r"^#\s+(.*)")
SECTION_MD = re.compile(r"^##\s+(.*)")

def detect_heading(line: str):
    line = line.strip()

    ch = CHAPTER_MD.match(line)
    if ch:
        return "chapter", ch.group(1).strip()

    sec = SECTION_MD.match(line)
    if sec:
        return "section", sec.group(1).strip()

    return None, None

# ===============================
# STRUCTURE PARSING
# ===============================

def parse_structure(pages: List[Dict]) -> List[Dict]:
    sections = []

    current_chapter = None
    current_section = None
    buffer = []
    page_start = None
    page_end = None

    for page in pages:
        page_no = page["page"]
        lines = page["text"].splitlines()

        for line in lines:
            heading_type, heading_text = detect_heading(line)

            if heading_type:
                if buffer:
                    sections.append({
                        "chapter": current_chapter,
                        "section": current_section,
                        "text": "\n".join(buffer).strip(),
                        "pages": (page_start, page_end)
                    })
                    buffer = []

                if heading_type == "chapter":
                    current_chapter = heading_text
                    current_section = None
                else:
                    current_section = heading_text

                page_start = page_no
                page_end = page_no
            else:
                if line.strip():
                    buffer.append(line)
                    page_start = page_no if page_start is None else page_start
                    page_end = page_no

    if buffer:
        sections.append({
            "chapter": current_chapter,
            "section": current_section,
            "text": "\n".join(buffer).strip(),
            "pages": (page_start, page_end)
        })

    return sections

# ===============================
# CHUNKING LOGIC
# ===============================

def chunk_section(section: Dict) -> List[Dict]:
    # 🔑 Context enrichment (CRITICAL)
    context_header = (
        f"Book: {BOOK_ID}\n"
        f"Chapter: {section['chapter']}\n"
        f"Section: {section['section']}\n\n"
    )

    full_text = context_header + section["text"]
    tokens = tokenizer.encode(full_text, add_special_tokens=False)

    chunks = []
    stride = WINDOW_SIZE - OVERLAP
    chunk_idx = 0

    for start in range(0, len(tokens), stride):
        end = start + WINDOW_SIZE
        window_tokens = tokens[start:end]

        if len(window_tokens) < MIN_CHUNK_TOKENS:
            break

        chunk_text = tokenizer.decode(window_tokens)

        chunks.append({
            "book": BOOK_ID,
            "chapter": section["chapter"],
            "section": section["section"],
            "chunk_index": chunk_idx,
            "page_start": section["pages"][0],
            "page_end": section["pages"][1],
            "token_count": len(window_tokens),
            "text": chunk_text
        })

        chunk_idx += 1

    return chunks

# ===============================
# PIPELINE DRIVER
# ===============================

def load_cleaned_text(json_path: str) -> List[Dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        raw_pages = json.load(f)

    return [
        {
            "page": item["page_number"],
            "text": item["text"]
        }
        for item in raw_pages
    ]

def structure_aware_chunking(pages: List[Dict]) -> List[Dict]:
    sections = parse_structure(pages)

    all_chunks = []
    for sec in sections:
        if sec["text"]:
            all_chunks.extend(chunk_section(sec))

    return all_chunks

# ===============================
# SAVE
# ===============================

def save_chunks(chunks, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

# ===============================
# EXECUTION
# ===============================

if __name__ == "__main__":
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, "..", "vectors", "cleaned_text.json")
    output_path = os.path.join(BASE_DIR, "..", "vectors", "chunks.json")

    pages = load_cleaned_text(json_path)
    chunks = structure_aware_chunking(pages)
    save_chunks(chunks, output_path)

    print(f"✅ Total chunks created: {len(chunks)}")
    print(f"📁 Saved to: {output_path}")
