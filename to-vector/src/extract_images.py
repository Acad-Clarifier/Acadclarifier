import fitz  # PyMuPDF
import os
import json
import re

PDF_PATH = "../data/sample.pdf"
OUTPUT_DIR = "../images/sample_book"
OUTPUT_JSON = "../vectors/images.json"

FIGURE_PATTERN = re.compile(r"(Figure\s+\d+(\.\d+)?)", re.IGNORECASE)

os.makedirs(OUTPUT_DIR, exist_ok=True)

doc = fitz.open(PDF_PATH)
image_records = []

for page_index, page in enumerate(doc):
    text = page.get_text()
    captions = FIGURE_PATTERN.findall(text)

    images = page.get_images(full=True)

    for img_idx, img in enumerate(images):
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)

        image_name = f"page_{page_index+1}_img_{img_idx+1}.png"
        image_path = os.path.join(OUTPUT_DIR, image_name)

        if pix.colorspace is None:
            # Mask image (skip or handle separately)
            pix = None
            continue

        if pix.colorspace.name not in ("DeviceRGB", "DeviceGray"):
            pix = fitz.Pixmap(fitz.csRGB, pix)

        # Save image
        pix.save(image_path)
        pix = None

        image_records.append({
            "page": page_index + 1,
            "image_path": image_path.replace("\\", "/"),
            "caption": captions[img_idx][0] if img_idx < len(captions) else ""
        })

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(image_records, f, indent=2)

print(f"Extracted {len(image_records)} images")
