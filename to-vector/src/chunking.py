import re
from typing import List, Dict
from transformers import AutoTokenizer

# -------------------------------
# CONFIGURATION
# -------------------------------

BOOK_ID = "book_1"
TOKENIZER_NAME = "sentence-transformers/all-MiniLM-L6-v2"

WINDOW_SIZE = 350       # tokens per chunk
OVERLAP = 70            # overlapping tokens

tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

# -------------------------------
# STRUCTURAL DETECTION RULES
# -------------------------------

CHAPTER_PATTERN = re.compile(r"^(CHAPTER|Chapter)\s+\d+", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)?\s+")

def detect_heading(line: str):
    line = line.strip()
    if CHAPTER_PATTERN.match(line):
        return "chapter", line
    if SECTION_PATTERN.match(line):
        return "section", line
    return None, None

# -------------------------------
# STAGE 1–2: STRUCTURAL PARSING
# -------------------------------

def normalize_text(text: str) -> str:
    text = text.replace("CHAP TER", "CHAPTER")
    text = re.sub(r"\n([a-z])", r"\1", text)  # join broken words
    return text


def parse_structure(pages: List[Dict]) -> List[Dict]:
    """
    Output:
    [
      {
        "chapter": "...",
        "section": "...",
        "text": "normalize_text(item["text"])",
        "pages": [start, end]
      }
    ]
    """
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

            if heading_type in ("chapter", "section"):
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
                    if page_start is None:
                        page_start = page_no
                    page_end = page_no

    if buffer:
        sections.append({
            "chapter": current_chapter,
            "section": current_section,
            "text": "\n".join(buffer).strip(),
            "pages": (page_start, page_end)
        })

    return sections

# -------------------------------
# STAGE 3–5: TOKEN-BASED SLIDING WINDOW
# -------------------------------

def chunk_section(section: Dict) -> List[Dict]:
    tokens = tokenizer.encode(section["text"], add_special_tokens=False)

    chunks = []
    stride = WINDOW_SIZE - OVERLAP
    chunk_idx = 0

    for start in range(0, len(tokens), stride):
        end = start + WINDOW_SIZE
        window_tokens = tokens[start:end]

        if len(window_tokens) < 50:
            break

        chunk_text = tokenizer.decode(window_tokens)

        chunks.append({
            "book": BOOK_ID,
            "chapter": section["chapter"],
            "section": section["section"],
            "chunk_index": chunk_idx,
            "page_start": section["pages"][0],
            "page_end": section["pages"][1],
            "text": chunk_text
        })

        chunk_idx += 1

    return chunks

# -------------------------------
# PIPELINE DRIVER
# -------------------------------

import json

def load_cleaned_text(json_path: str):
    """
    Loads cleaned_text.json and adapts it to the expected input format.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        raw_pages = json.load(f)

    pages = []
    for item in raw_pages:
        pages.append({
            "page": item["page_number"],  # ADAPT KEY NAME
            "text": item["text"]
        })

    return pages



def structure_aware_chunking(pages: List[Dict]) -> List[Dict]:
    sections = parse_structure(pages)

    all_chunks = []
    for sec in sections:
        if not sec["text"]:
            continue
        all_chunks.extend(chunk_section(sec))

    return all_chunks

# -------------------------------
# SAVING CHUNKS IN A FILE
# -------------------------------

def save_chunks(chunks, output_path):
    import json
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)


# -------------------------------
# EXAMPLE USAGE
# -------------------------------

if __name__ == "__main__":
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, "..", "vectors", "cleaned_text.json")
    output_path = os.path.join(BASE_DIR, "..", "vectors", "chunks.json")

    pages = load_cleaned_text(json_path)
    chunks = structure_aware_chunking(pages)

    save_chunks(chunks, output_path)

    print(f"✅ Total chunks created: {len(chunks)}")
    print(f"📁 Chunks saved to: {output_path}")


