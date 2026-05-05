import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import requests

# ==============================
# CONFIG
# ==============================

# Load environment variables from project .env
ENV_PATH = (Path(__file__).resolve().parent / ".." / ".env").resolve()
load_dotenv(dotenv_path=ENV_PATH, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
MISTRAL_MODEL = "mistral-small-latest"
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

OUTPUT_DIR = "final_output"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PARENT = (SCRIPT_DIR / ".." / "outputs" / OUTPUT_DIR).resolve()

# ==============================
# INITIALIZE GEMINI
# ==============================


# response = client.models.generate_content(
#     model="gemini-2.5-flash",
#     contents=prompt,
#     config=types.GenerateContentConfig(
#         system_instruction=SYSTEM_INSTRUCTION,
#         temperature=0.25,
#         top_p=0.9,
#         max_output_tokens=900,
#     )
# )

# genai.configure(api_key=GEMINI_API_KEY)

# model = genai.GenerativeModel(
#     model_name=MODEL_NAME,
#     generation_config={
#         "temperature": 0.25,
#         "top_p": 0.9,
#         "max_output_tokens": 900
#     }
# )

# ==============================
# PROMPT BUILDER
# ==============================


# def build_prompt(data: dict) -> str:
#     query = data["query"]
#     blocks = data["web_context"]

#     context_text = []
#     for idx, block in enumerate(blocks, start=1):
#         context_text.append(
#             f"""--- Source {idx} start ---
#             {block["text"]}
#             --- Source {idx} end ---
#             """
#         )

#     joined_context = "\n".join(context_text)

#     prompt = f"""
#         You are an academic content simplification engine which is a part of a web retrieval pipeline.

#         TASK:
#         You are given a DATA to simplify. Produce a final, clean, user-facing explanation following output requirements. You are also provided with query for better context understanding.
#         Use ONLY the information present in the provided DATA.
#         Do NOT introduce new facts, examples, timelines, or assumptions.

#         OUTPUT REQUIREMENTS:
#         - Clear academic language
#         - No marketing tone
#         - No repetition
#         - No citations or URLs
#         - No mention of confidence scores
#         - Ignore duplicated or corrupted text
#         - Merge overlapping information

#         FORMAT (STRICT):
#         Title
#         Brief overview (2–3 lines)

#         Key points
#         - Bullet points

#         Detailed explanation
#         - Well-structured paragraphs or subsections

#         QUERY:
#         {query}

#         DATA:
#         {joined_context}


#         If information is missing or unclear, state it explicitly instead of guessing. Strictly use only given information.
#         """
#     return prompt.strip()

def build_prompt(data: dict) -> str:
    query = data["query"]
    blocks = data["web_context"]

    context_text = []
    for idx, block in enumerate(blocks, start=1):
        context_text.append(f"Source {idx}: {block['text']}")
    joined_context = "\n\n".join(context_text)

    prompt = f"""
        You are an expert Academic Educator. Your task is to transform the provided raw DATA into a comprehensive, simplified academic guide.

        CONTEXT/QUERY: {query} 
        DATA:
        {joined_context}

        INSTRUCTIONS:
        1. PROVIDE DEPTH: While the language should be simple, the explanation must be concise but complete. Avoid repetition and keep the response roughly half the previous length.
        2. STRUCTURE: Use the format below. Keep the 'Detailed Explanation' section shorter than before, but still useful.
        3. TONE: Academic, professional, and educational.
        4. CONSTRAINTS: Use only provided data, but feel free to rephrase and expand on the logic to make it easier to understand.

        FORMAT:
        # [Title]
        
        ### Overview
        [1-2 lines summarizing the core concept]

        ### Key Concepts
        [4-6 bullet points explaining the main terms found in the data]

        ### Detailed Academic Explanation
        [Provide a compact multi-paragraph explanation here. Focus on the essential connections and practical meaning. Keep this section roughly 150-200 words long.]
        """
    return prompt.strip()


def _ensure_gemini_api_key() -> str:
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Set services/retrieval-web/.env and restart the backend."
        )
    return GEMINI_API_KEY


def _normalize_gemini_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if "api key expired" in lowered or "api_key_invalid" in lowered or "invalid api key" in lowered:
        return (
            "GEMINI_API_KEY is invalid or expired. Renew the key in services/retrieval-web/.env "
            "and restart the backend."
        )

    return f"Gemini request failed: {exc.__class__.__name__}: {message}"


# def run_model(prompt: str):
#     if not GEMINI_API_KEY:
#         raise ValueError(
#             "GEMINI_API_KEY is not set. Please set the GEMINI_API_KEY environment "
#             "variable to use the Gemini API."
#         )
#     client = genai.Client(
#         api_key=GEMINI_API_KEY
#     )
#     output = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=prompt,
#         config=types.GenerateContentConfig(
#             temperature=0.25,
#             top_p=0.9,
#             max_output_tokens=900,
#         )
#     )

#     return output

def _extract_gemini_text(response: Any) -> str | None:
    text = getattr(response, "text", None)
    if text:
        return text.strip() or None
    return None


def _extract_gemini_http_text(response_data: dict[str, Any]) -> str | None:
    candidates = response_data.get("candidates") or []
    if not candidates:
        return None

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()
    return text or None


def _run_gemini_model(prompt: str) -> str | None:
    api_key = _ensure_gemini_api_key()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.9,
            "maxOutputTokens": 1500,
        },
    }

    response = requests.post(url, json=payload, timeout=8)
    response.raise_for_status()
    return _extract_gemini_http_text(response.json())


def _run_mistral_model(prompt: str) -> str | None:
    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY is not configured")

    url = "https://api.mistral.ai/v1/chat/completions"
    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    }
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=12)
    response.raise_for_status()
    response_data = response.json()
    choices = response_data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = (message.get("content") or "").strip()
    return content or None


def run_model(prompt: str):
    last_error: Exception | None = None

    for provider_name, runner in (("mistral", _run_mistral_model), ("gemini", _run_gemini_model)):
        started = time.perf_counter()
        try:
            text = runner(prompt)
            if text:
                if len(text.strip()) < 700:
                    last_error = RuntimeError(
                        f"{provider_name} response too short ({len(text.strip())} chars)"
                    )
                    continue
                print(
                    f"[{provider_name.upper()}] completed in {time.perf_counter() - started:.2f}s")

                class _Response:
                    def __init__(self, text: str):
                        self.text = text
                return _Response(text)
            last_error = RuntimeError(f"{provider_name} returned empty text")
        except Exception as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise RuntimeError(_normalize_gemini_error(last_error)) from last_error

    raise RuntimeError("Model request failed unexpectedly")

# ==============================
# MAIN EXECUTION
# ==============================


def save_simplified(output_text: str, *, timestamp: str | None = None) -> str:
    OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)

    resolved_timestamp = timestamp or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"stage6_simplified_{resolved_timestamp}.txt"
    path = OUTPUT_PARENT / filename

    with open(path, "w", encoding="utf-8") as f:
        f.write(output_text)

    return str(path)


def run(input_path: str | None = None, *, query: str | None = None):
    if not input_path:
        raise ValueError("simplifier.run requires input_path")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompt = build_prompt(data)

    # response = model.generate_content(prompt)
    response = run_model(prompt)
    output_text = response.text.strip()

    timestamp = data.get(
        "timestamp_utc", datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
    output_path = save_simplified(output_text, timestamp=timestamp)

    print(f"[OK] Output saved to: {output_path}")
    return output_path

# ==============================
# ENTRY POINT
# ==============================


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python simplifier.py <input_json_file>")
        sys.exit(1)

    run(sys.argv[1])

# py simplifier.py ../outputs/final_context_outputs/test-mongoDB.json
