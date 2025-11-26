from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF
import os
import numpy as np
import json

# Load the model (this will download it if not present)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def pdf_to_text(path):
    text = ""
    doc = fitz.open(path)
    for page in doc:
        text += page.get_text()
    return text


def text_to_vector(text):
    return model.encode(text, convert_to_numpy=True)


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    pdf_path = os.path.join(BASE_DIR, "data", "sample.pdf")
    print("Using PDF:", pdf_path)

    text = pdf_to_text(pdf_path)
    vector = text_to_vector(text)

    print("Vector shape:", vector.shape)
    print("Sample vector values:", vector[:10])
    # Ensure vectors directory exists at project root
    vectors_dir = os.path.join(BASE_DIR, "vectors")
    os.makedirs(vectors_dir, exist_ok=True)

    # Save as .npy
    npy_path = os.path.join(vectors_dir, "sample_vector.npy")
    np.save(npy_path, vector)
    print("Saved numpy vector to:", npy_path)

    # Save as .json (list of floats)
    json_path = os.path.join(vectors_dir, "sample_vector.json")
    try:
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(vector.tolist(), jf)
        print("Saved JSON vector to:", json_path)
    except Exception as e:
        print("Failed to save JSON vector:", e)

    # Save as .txt (one value per line)
    txt_path = os.path.join(vectors_dir, "sample_vector.txt")
    try:
        with open(txt_path, "w", encoding="utf-8") as tf:
            for v in vector.tolist():
                tf.write(f"{v}\n")
        print("Saved text vector to:", txt_path)
    except Exception as e:
        print("Failed to save text vector:", e)
