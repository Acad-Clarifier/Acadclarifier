import json
import os
from datetime import datetime
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ==============================
# CONFIG
# ==============================

# Load environment variables from project .env
ENV_PATH = (Path(__file__).resolve().parent / ".." / ".env").resolve()
load_dotenv(dotenv_path=ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "models/gemini-2.5-flash"

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
    blocks = data["query_context"]

    context_text = []
    for idx, block in enumerate(blocks, start=1):
        context_text.append(f"Source {idx}: {block['text']}")
    joined_context = "\n\n".join(context_text)

    # Use "Positive Reinforcement" for length
    prompt = f"""
        You are an expert Academic Educator. Your task is to transform the provided raw DATA into a comprehensive, simplified academic guide.

        CONTEXT/QUERY: {query}
        DATA:
        {joined_context}

        INSTRUCTIONS:
        1. PROVIDE DEPTH: While the language should be simple, the explanation must be detailed and thorough. Do not give a summary; give a full explanation.
        2. STRUCTURE: Use the format below. Ensure the 'Detailed Explanation' section is the longest part of your response.
        3. TONE: Academic, professional, and educational.
        4. CONSTRAINTS: Use only provided data, but feel free to rephrase and expand on the logic to make it easier to understand.

        FORMAT:
        # [Title]
        
        ### Overview
        [2-3 lines summarizing the core concept]

        ### Key Concepts
        [Bullet points explaining the main terms found in the data]

        ### Detailed Academic Explanation
        [Provide a multi-paragraph, in-depth explanation here. Elaborate on how the different pieces of data connect. This section should be at least 300 words long.]
        """
    return prompt.strip()


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

def run_model(prompt: str):
    client = genai.Client(api_key=GEMINI_API_KEY)
    output = client.models.generate_content(
        # Try "gemini-1.5-pro" if flash is still too short
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,  # Increased from 0.25
            top_p=0.95,
            max_output_tokens=2048,  # Increased to allow for longer responses
        )
    )
    return output

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


def run(input_json_path: str):
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompt = build_prompt(data)

    # response = model.generate_content(prompt)
    response = run_model(prompt)
    output_text = response.text.strip()

    timestamp = data.get(
        "timestamp_utc", datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
    output_path = save_simplified(output_text, timestamp=timestamp)

    print(f"[OK] Output saved to: {output_path}")

# ==============================
# ENTRY POINT
# ==============================


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python simplifier.py <input_json_file>")
        sys.exit(1)

    run(sys.argv[1])
