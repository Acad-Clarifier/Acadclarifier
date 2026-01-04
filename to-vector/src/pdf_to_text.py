import os
import pymupdf as fitz  # PyMuPDF
import re
import json
import statistics
from typing import List, Dict, Tuple

# ==============================
# CONFIGURATION
# ==============================
HEADER_MARGIN_RATIO = 0.08   # Top 8% of page
FOOTER_MARGIN_RATIO = 0.92   # Bottom 8% of page
MIN_TOTAL_TEXT_CHARS = 500  # Below this → likely scanned PDF

# ==============================
# TEXT CLEANING UTILITIES
# ==============================


def remove_page_markers(text: str) -> str:
    """
    Remove artificial page markers like [PAGE 1], [PAGE 2], etc.
    """
    text = re.sub(r"\[PAGE \d+\]\n*", "", text)
    return text.strip()


def fix_broken_words(text: str) -> str:
    """
    Merge words incorrectly split ACROSS NEWLINES only.

    Fixes PDF-induced breaks like:
    - "interactio\nn" → "interaction"
    - "Introductio\nn" → "Introduction"
    - "CHAP\nTER" → "CHAPTER"

    Safe rules (minimum 3 chars to avoid merging "a tool" → "atool"):
    - lowercase: [a-z]{3,}\n[a-z]{2,}
    - uppercase: [A-Z]{3,}\n[A-Z]{2,}

    Does NOT merge words separated by normal spaces (e.g., "a tool" stays "a tool").
    """
    # Merge lowercase words split by newline: "interactio\nn" → "interaction"
    text = re.sub(r'([a-z]{3,})\n([a-z]{2,})', r'\1\2', text)

    # Merge uppercase words split by newline: "CHAP\nTER" → "CHAPTER"
    text = re.sub(r'([A-Z]{3,})\n([A-Z]{2,})', r'\1\2', text)

    # Merge title case split by newline: "Introductio\nn" → "Introduction"
    text = re.sub(r'([A-Z][a-z]{2,})\n([a-z]{2,})', r'\1\2', text)

    return text


def normalize_bullets(text: str) -> str:
    """
    Convert inline bullet points to line-separated format.
    • Point one • Point two • Point three
    becomes:
    • Point one
    • Point two
    • Point three
    """
    # Find bullet sequences and split them
    text = re.sub(r'•\s+([^•]+?)(?=\s*•|\s*$)', r'• \1\n', text)
    # Clean up multiple newlines
    text = re.sub(r'\n\s*\n+', '\n', text)
    return text


def normalize_headers(text: str) -> str:
    """
    Ensure Markdown-style headers (##, ###) are:
    - On their own lines
    - Separated from body text by blank lines
    """
    # Ensure headers have newlines before them
    text = re.sub(r'([^\n])(##+ )', r'\1\n\2', text)
    # Ensure headers have newlines after them
    text = re.sub(r'(##+ [^\n]+)([^\n])', r'\1\n\2', text)
    # Add blank line after headers
    text = re.sub(r'(##+ [^\n]+)\n(?!$|\n)', r'\1\n\n', text)
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def merge_page_overflow(pages_data: List[Dict]) -> List[Dict]:
    """
    Merge paragraph spillovers across pages.
    If a page ends without a sentence terminator (. ? ! :),
    merge its text with the next page's beginning.
    """
    merged = []
    i = 0

    while i < len(pages_data):
        current_page = pages_data[i].copy()
        current_text = current_page["text"].strip()

        # Check if this page ends with a sentence terminator
        while i < len(pages_data) - 1:
            # Check if text ends with sentence-ending punctuation
            if not current_text or current_text[-1] in ".?!:":
                break

            # If not, merge with next page
            next_page = pages_data[i + 1]
            current_text += " " + next_page["text"].strip()
            i += 1

        current_page["text"] = current_text
        merged.append(current_page)
        i += 1

    return merged


def clean_text_content(text: str) -> str:
    """
    Cleans common PDF artifacts while preserving meaning.
    """
    # Fix true hyphenated line breaks: "semi-\nconductor" → "semiconductor"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Replace single newlines inside sentences with space
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Normalize multiple spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def remove_equation_noise(text: str) -> str:
    """
    Removes lines dominated by equations/symbols (bad for embeddings).
    """
    clean_lines = []
    for line in text.splitlines():
        if not line.strip():
            continue
        symbol_ratio = sum(
            c in "=+*/<>^_{}[]" for c in line) / max(len(line), 1)
        if symbol_ratio < 0.3:
            clean_lines.append(line)
    return "\n".join(clean_lines)


# ==============================
# FONT ANALYSIS
# ==============================

def analyze_document_styles(doc: fitz.Document) -> Tuple[float, float]:
    """
    Determines body font size and header threshold dynamically.
    """
    font_sizes = []

    sample_pages = min(20, len(doc))
    for i in range(sample_pages):
        page = doc[i]
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" not in b:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        font_sizes.append(span["size"])

    if not font_sizes:
        print("⚠️ No text detected. Possibly scanned PDF.")
        return 11.0, 14.0

    # Robust body font detection
    filtered = [s for s in font_sizes if 8.5 <= s <= 14]
    body_size = statistics.median(filtered)

    # Conservative header detection
    header_threshold = body_size + 2.5

    print(
        f"📊 Body font ≈ {body_size:.1f}pt | Header threshold > {header_threshold:.1f}pt"
    )
    return body_size, header_threshold


# ==============================
# MAIN EXTRACTION LOGIC
# ==============================

def extract_high_quality_text(pdf_path: str) -> List[Dict]:
    doc = fitz.open(pdf_path)
    print(f"📖 Processing '{pdf_path}' ({len(doc)} pages)")

    body_size, header_thresh = analyze_document_styles(doc)
    extracted_pages = []

    total_text_chars = 0

    for page_index, page in enumerate(doc):
        page_height = page.rect.height
        header_limit = page_height * HEADER_MARGIN_RATIO
        footer_limit = page_height * FOOTER_MARGIN_RATIO

        blocks = page.get_text("dict", sort=True)["blocks"]
        page_blocks = []

        for block in blocks:
            if block["type"] != 0:
                continue

            y0, y1 = block["bbox"][1], block["bbox"][3]
            if y1 < header_limit or y0 > footer_limit:
                continue

            block_parts = []

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    size = span["size"]

                    if not text:
                        continue

                    # Ignore tiny footnote-like text
                    if size < body_size - 2.5:
                        continue

                    # Detect section headers
                    if size > header_thresh:
                        text = f"\n## {text}\n"

                    block_parts.append(text)

            if not block_parts:
                continue

            block_text = "\n".join(block_parts)
            block_text = clean_text_content(block_text)
            block_text = remove_equation_noise(block_text)

            if block_text:
                page_blocks.append(block_text)
                total_text_chars += len(block_text)

        final_page_text = "\n\n".join(page_blocks)
        final_page_text = f"[PAGE {page_index + 1}]\n\n" + final_page_text

        extracted_pages.append(
            {
                "page_number": page_index + 1,
                "text": final_page_text
            }
        )

    if total_text_chars < MIN_TOTAL_TEXT_CHARS:
        raise ValueError(
            "❌ Extracted text too small — PDF is likely scanned. OCR required."
        )

    # Post-processing: apply comprehensive cleaning pipeline
    # extracted_pages = merge_page_overflow(extracted_pages)

    for page in extracted_pages:
        text = page["text"]
        text = remove_page_markers(text)
        text = fix_broken_words(text)
        text = normalize_bullets(text)
        text = normalize_headers(text)
        page["text"] = text.strip()

    return extracted_pages


# ==============================
# OUTPUT
# ==============================

def save_to_json(data: List[Dict], output_file: str):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved cleaned text to '{output_file}'")


# ==============================
# EXECUTION
# ==============================

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    INPUT_PDF = os.path.join(BASE_DIR, "data", "sample.pdf")
    OUTPUT_JSON = os.path.join(BASE_DIR, "vectors", "cleaned_text.json")

    try:
        data = extract_high_quality_text(INPUT_PDF)
        save_to_json(data, OUTPUT_JSON)

        # Preview
        preview_page = min(4, len(data) - 1)
        print("\n🔍 Preview:")
        print("-" * 50)
        print(data[preview_page]["text"][:700])
        print("-" * 50)

    except Exception as e:
        print(f"❌ ERROR: {e}")
