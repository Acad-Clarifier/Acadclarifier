import os
import re
import json
import fitz  # PyMuPDF
import statistics
from typing import List, Dict, Tuple

# ==============================
# CONFIGURATION
# ==============================

HEADER_MARGIN_RATIO = 0.08
FOOTER_MARGIN_RATIO = 0.92
MIN_TOTAL_TEXT_CHARS = 500

NON_CONTENT_PATTERNS = [
    r"table of contents",
    r"\bcontents\b",
    r"copyright",
    r"isbn",
    r"all rights reserved",
    r"preface",
    r"acknowledg(e)?ments",
    r"\bindex\b"
]

EQUATION_SYMBOLS = set("=+*/<>^_{}[]")

# ==============================
# BASIC CLEANING UTILITIES
# ==============================

def is_non_content_page(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in NON_CONTENT_PATTERNS)


def remove_inline_page_numbers(text: str) -> str:
    return re.sub(r"\s+\d{1,4}\s*$", "", text, flags=re.MULTILINE)


def fix_hyphenated_line_breaks(text: str) -> str:
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def fix_broken_words(text: str) -> str:
    text = re.sub(r'([a-z]{3,})\n([a-z]{2,})', r'\1\2', text)
    text = re.sub(r'([A-Z]{3,})\n([A-Z]{2,})', r'\1\2', text)
    text = re.sub(r'([A-Z][a-z]{2,})\n([a-z]{2,})', r'\1\2', text)
    return text


def normalize_bullets_and_lists(text: str) -> str:
    text = re.sub(r'•\s+([^•]+?)(?=\s*•|\s*$)', r'• \1\n', text)
    text = re.sub(r'(\d+)\.\s+', r'\n\1. ', text)
    return text


def remove_equation_noise(text: str) -> str:
    clean = []
    for line in text.splitlines():
        if not line.strip():
            continue
        ratio = sum(c in EQUATION_SYMBOLS for c in line) / max(len(line), 1)
        if ratio < 0.3:
            clean.append(line)
    return "\n".join(clean)


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# ==============================
# FONT ANALYSIS
# ==============================

def analyze_document_styles(doc: fitz.Document) -> Tuple[float, float]:
    font_sizes = []

    for i in range(min(20, len(doc))):
        page = doc[i]
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if s["text"].strip():
                        font_sizes.append(s["size"])

    if not font_sizes:
        return 11.0, 14.0

    filtered = [s for s in font_sizes if 8.5 <= s <= 14]
    body_size = statistics.median(filtered)
    header_threshold = body_size + 2.5

    print(f"📊 Body font ≈ {body_size:.1f}pt | Header > {header_threshold:.1f}pt")
    return body_size, header_threshold

# ==============================
# HEADER SUPPRESSION
# ==============================

def suppress_repeated_headers(pages: List[Dict]) -> None:
    from collections import Counter

    first_lines = []
    for p in pages:
        lines = p["text"].splitlines()
        if lines:
            first_lines.append(lines[0].strip())

    counts = Counter(first_lines)
    repeated = {k for k, v in counts.items() if v > len(pages) * 0.2}

    for p in pages:
        lines = p["text"].splitlines()
        if lines and lines[0].strip() in repeated:
            p["text"] = "\n".join(lines[1:]).strip()

# ==============================
# PAGE MERGING
# ==============================

def merge_page_overflow(pages: List[Dict]) -> List[Dict]:
    merged = []
    i = 0

    while i < len(pages):
        current = pages[i].copy()
        text = current["text"].strip()

        while i < len(pages) - 1 and text and text[-1] not in ".?!:":
            i += 1
            text += " " + pages[i]["text"].strip()

        current["text"] = text
        merged.append(current)
        i += 1

    return merged

# ==============================
# MAIN EXTRACTION
# ==============================

def extract_high_quality_text(pdf_path: str) -> List[Dict]:
    doc = fitz.open(pdf_path)
    print(f"📖 Processing '{pdf_path}' ({len(doc)} pages)")

    body_size, header_thresh = analyze_document_styles(doc)
    extracted = []
    total_chars = 0

    for page_index, page in enumerate(doc):
        page_height = page.rect.height
        header_limit = page_height * HEADER_MARGIN_RATIO
        footer_limit = page_height * FOOTER_MARGIN_RATIO

        blocks = page.get_text("dict", sort=True)["blocks"]
        page_lines = []

        for block in blocks:
            if block["type"] != 0:
                continue

            y0, y1 = block["bbox"][1], block["bbox"][3]
            if y1 < header_limit or y0 > footer_limit:
                continue

            for line in block.get("lines", []):
                line_text = []
                max_font = 0

                for span in line.get("spans", []):
                    if not span["text"].strip():
                        continue
                    if span["size"] < body_size - 2.5:
                        continue

                    max_font = max(max_font, span["size"])
                    line_text.append(span["text"])

                if line_text:
                    text = "".join(line_text).strip()
                    if max_font > header_thresh + 2:
                        page_lines.append(f"\n# {text}\n")
                    elif max_font > header_thresh:
                        page_lines.append(f"\n## {text}\n")
                    else:
                        page_lines.append(text)

        if not page_lines:
            continue

        page_text = "\n".join(page_lines)
        page_text = fix_hyphenated_line_breaks(page_text)
        page_text = remove_equation_noise(page_text)
        page_text = normalize_whitespace(page_text)
        page_text = remove_inline_page_numbers(page_text)

        if is_non_content_page(page_text):
            continue

        total_chars += len(page_text)
        extracted.append({
            "page_number": page_index + 1,
            "text": page_text
        })

    if total_chars < MIN_TOTAL_TEXT_CHARS:
        raise ValueError("❌ PDF appears scanned or non-textual. OCR required.")

    suppress_repeated_headers(extracted)
    extracted = merge_page_overflow(extracted)

    for p in extracted:
        p["text"] = normalize_bullets_and_lists(
            fix_broken_words(p["text"])
        )

    return extracted

# ==============================
# OUTPUT
# ==============================

def save_to_json(data: List[Dict], output_file: str):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved cleaned text → {output_file}")

# ==============================
# EXECUTION
# ==============================

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    INPUT_PDF = os.path.join(BASE_DIR, "data", "sample.pdf")
    OUTPUT_JSON = os.path.join(BASE_DIR, "vectors", "cleaned_text.json")

    try:
        pages = extract_high_quality_text(INPUT_PDF)
        save_to_json(pages, OUTPUT_JSON)

        print("\n🔍 Preview:\n" + "-" * 50)
        print(pages[min(3, len(pages) - 1)]["text"][:800])
        print("-" * 50)

    except Exception as e:
        print(f"❌ ERROR: {e}")
