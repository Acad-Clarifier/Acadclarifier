import os
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dotenv import load_dotenv
import requests

try:
    import google.generativeai as genai  # type: ignore
    GOOGLE_GENAI_BACKEND = "legacy"
    GOOGLE_GENAI_CLIENT = None
except ImportError:
    try:
        from google import genai as google_genai  # type: ignore

        genai = None
        GOOGLE_GENAI_BACKEND = "v1"
        GOOGLE_GENAI_CLIENT = google_genai
    except ImportError:
        genai = None
        GOOGLE_GENAI_BACKEND = None
        GOOGLE_GENAI_CLIENT = None

# ============================================================================
# CONFIGURATION
# ============================================================================
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # retrieval-local folder
QUERY_OUTPUT_DIR = BASE_DIR / "outputs" / "query_output"
FINAL_OUTPUT_DIR = BASE_DIR / "outputs" / "final_output"
ENV_FILE = BASE_DIR / ".env"

MODEL_NAME = "gemini-2.5-flash"
MISTRAL_MODEL = "mistral-small-latest"
TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 1500
MODEL_TIMEOUT_SECONDS = 12
MIN_RESPONSE_CHARS = 1200

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _load_api_key_from_env(var_name: str) -> str:
    """Load an API key from the configured .env file."""
    load_dotenv(ENV_FILE)

    api_key = os.getenv(var_name)
    if not api_key:
        logger.error("%s not found in .env file", var_name)
        raise ValueError(f"{var_name} not found in {ENV_FILE}")

    logger.info("✓ %s loaded successfully from .env file", var_name)
    return api_key


def load_api_key_from_env() -> str:
    """
    Load Gemini API key from .env file.

    Returns:
        API key string

    Raises:
        ValueError: If API key not found
    """
    try:
        return _load_api_key_from_env("GEMINI_API_KEY")
    except FileNotFoundError:
        logger.error(f".env file not found at {ENV_FILE}")
        raise ValueError(f".env file not found at {ENV_FILE}")
    except Exception as e:
        logger.error(f"Error loading API key: {str(e)}")
        raise


def load_mistral_api_key_from_env() -> str:
    """Load the Mistral API key from the configured .env file."""
    try:
        return _load_api_key_from_env("MISTRAL_API_KEY")
    except FileNotFoundError:
        logger.error(f".env file not found at {ENV_FILE}")
        raise ValueError(f".env file not found at {ENV_FILE}")
    except Exception as e:
        logger.error(f"Error loading Mistral API key: {str(e)}")
        raise


def discover_query_files() -> List[Path]:
    """
    Discover all query JSON files in query_output folder.

    Returns:
        List of query JSON file paths sorted by name

    Raises:
        ValueError: If query_output folder not found
    """
    try:
        if not QUERY_OUTPUT_DIR.exists():
            logger.error(
                f"Query output directory not found: {QUERY_OUTPUT_DIR}")
            raise ValueError(
                f"Query output directory not found: {QUERY_OUTPUT_DIR}")

        # Get all JSON files matching query_*.json pattern
        query_files = sorted(QUERY_OUTPUT_DIR.glob("query_*.json"))

        if not query_files:
            logger.warning(f"No query files found in {QUERY_OUTPUT_DIR}")
            return []

        logger.info(f"✓ Discovered {len(query_files)} query files")
        for qf in query_files:
            logger.info(f"  - {qf.name}")

        return query_files

    except Exception as e:
        logger.error(f"Error discovering query files: {str(e)}")
        raise


def load_query_json(file_path: Path) -> Optional[Dict]:
    """
    Load and validate query JSON file.

    Args:
        file_path: Path to query JSON file

    Returns:
        Parsed JSON data or None on error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate required fields
        required_fields = ['query_id', 'query', 'results', 'book']
        missing_fields = [
            field for field in required_fields if field not in data]

        if missing_fields:
            logger.error(
                f"Missing fields in {file_path.name}: {missing_fields}")
            return None

        logger.info(f"✓ Loaded query file: {file_path.name}")
        return data

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {file_path.name}")
        return None
    except Exception as e:
        logger.error(f"Error loading query file {file_path.name}: {str(e)}")
        return None


def extract_context_from_results(results: List[Dict]) -> str:
    """
    Extract and format context from query results.

    Args:
        results: List of result dictionaries from query JSON

    Returns:
        Formatted context string
    """
    try:
        if not results:
            logger.warning("No results provided for context extraction")
            return ""

        # Concatenate all documents from results
        context_parts = []
        for result in results[:3]:
            if 'document' in result and result['document']:
                context_parts.append(result['document'])

        joined_context = "\n\n".join(context_parts)

        logger.info(f"✓ Extracted context: {len(joined_context)} characters")
        return joined_context

    except Exception as e:
        logger.error(f"Error extracting context: {str(e)}")
        return ""


def build_prompt(query: str, joined_context: str) -> str:
    """
    Build the prompt for Gemini API.

    Args:
        query: User query string
        joined_context: Context from retrieved documents

    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an expert Academic Educator. Your task is to transform the provided raw DATA into a comprehensive, simplified academic guide.

CONTEXT/QUERY: {query}
DATA:
{joined_context}

INSTRUCTIONS:
1. PROVIDE DEPTH: While the language should be simple, the explanation must be concise but complete. Avoid repetition and keep the response roughly half the previous length.
2. STRUCTURE: Use the format below. Keep the 'Detailed Explanation' section shorter than before, but still useful.
3. TONE: Academic, professional, and educational.
4. CONSTRAINTS: Use only provided data as long as it directly answers the query, but feel free to rephrase and expand on the logic to make it easier to understand.
5. REWRITE TOTALLY: If the user query and the context data are very different from each other and the data is not directly answering the query, rewrite the data in a way that answers the query clearly without unnecessary length.

FORMAT:
# [Title]

### Overview
[1-2 lines summarizing the core concept]

### Key Concepts
[4-6 bullet points explaining the main terms found in the data]

### Detailed Academic Explanation
[Provide a compact multi-paragraph explanation here. Focus on the essential connections and practical meaning. Keep this section roughly 150-200 words long.]"""

    logger.info("✓ Prompt built successfully")
    return prompt


def _extract_gemini_text(response_data: Dict[str, Any]) -> Optional[str]:
    candidates = response_data.get("candidates") or []
    if not candidates:
        return None

    first_candidate = candidates[0] or {}
    content = first_candidate.get("content") or {}
    parts = content.get("parts") or []
    text_parts = [part.get("text", "")
                  for part in parts if isinstance(part, dict)]
    response_text = "".join(text_parts).strip()
    return response_text or None


def _extract_mistral_text(response_data: Dict[str, Any]) -> Optional[str]:
    choices = response_data.get("choices") or []
    if not choices:
        return None

    first_choice = choices[0] or {}
    message = first_choice.get("message") or {}
    response_text = (message.get("content") or "").strip()
    return response_text or None


def _generate_gemini_response(api_key: str, prompt: str) -> Optional[str]:
    if not api_key:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL_NAME}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": TEMPERATURE,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }

    logger.info("Generating response with Gemini model: %s", MODEL_NAME)
    response = requests.post(url, json=payload, timeout=MODEL_TIMEOUT_SECONDS)
    response.raise_for_status()
    response_data = response.json()
    response_text = _extract_gemini_text(response_data)
    if not response_text:
        logger.error("Empty response received from Gemini")
        return None

    logger.info("✓ Gemini response generated successfully")
    logger.info("  Response length: %s characters", len(response_text))
    return response_text


def _generate_mistral_response(api_key: str, prompt: str) -> Optional[str]:
    if not api_key:
        return None

    url = "https://api.mistral.ai/v1/chat/completions"
    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.info("Generating response with Mistral model: %s", MISTRAL_MODEL)
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=MODEL_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    response_data = response.json()
    response_text = _extract_mistral_text(response_data)
    if not response_text:
        logger.error("Empty response received from Mistral")
        return None

    logger.info("✓ Mistral response generated successfully")
    logger.info("  Response length: %s characters", len(response_text))
    return response_text


def generate_response(api_key: str, prompt: str) -> Dict[str, Any]:
    """
    Generate a response sequentially: try Mistral first, then Gemini as backup.
    """
    providers: List[Tuple[str, Any]] = []

    try:
        mistral_api_key = load_mistral_api_key_from_env()
        providers.append(
            ("mistral", lambda: _generate_mistral_response(mistral_api_key, prompt)))
    except Exception as exc:
        logger.warning("Mistral API key unavailable: %s", exc)

    if api_key:
        providers.append(
            ("gemini", lambda: _generate_gemini_response(api_key, prompt)))

    if not providers:
        return {
            "status": "error",
            "provider": "unknown",
            "error": "no generation providers available",
        }

    start_time = time.perf_counter()
    last_error: Optional[str] = None

    for provider_name, provider_fn in providers:
        provider_started = time.perf_counter()
        try:
            response_text = provider_fn()
        except requests.Timeout:
            last_error = f"{provider_name} timed out"
            logger.warning(
                "%s timed out after %ss",
                provider_name.capitalize(),
                MODEL_TIMEOUT_SECONDS,
            )
            continue
        except requests.RequestException as exc:
            last_error = f"{provider_name} request failed: {exc}"
            logger.warning(
                "%s request failed: %s",
                provider_name.capitalize(),
                str(exc),
            )
            continue
        except Exception as exc:
            last_error = f"{provider_name} unexpected failure: {exc}"
            logger.warning(
                "%s unexpected failure: %s",
                provider_name.capitalize(),
                str(exc),
            )
            continue

        if response_text:
            if len(response_text.strip()) < MIN_RESPONSE_CHARS:
                last_error = (
                    f"{provider_name} response too short "
                    f"({len(response_text.strip())} chars)"
                )
                logger.warning(
                    "%s response rejected because it was too short (%s chars)",
                    provider_name.capitalize(),
                    len(response_text.strip()),
                )
                continue

            logger.info(
                "%s completed in %.2fs",
                provider_name.capitalize(),
                time.perf_counter() - provider_started,
            )
            logger.info(
                "%s won the sequential fallback in %.2fs",
                provider_name.capitalize(),
                time.perf_counter() - start_time,
            )
            return {
                "status": "success",
                "provider": provider_name,
                "response_text": response_text,
            }

        last_error = f"{provider_name} returned an empty response"

    return {
        "status": "error",
        "provider": "unknown",
        "error": last_error or "all generation providers failed",
    }


def save_output(response_text: str, query_id: str, query: str, book_name: str) -> Optional[str]:
    """
    Save generated response to output file with metadata.

    Args:
        response_text: Generated response text
        query_id: Unique query identifier
        query: Original user query
        book_name: Book name that was queried

    Returns:
        Full path to saved file or None on failure
    """
    try:
        # Create final_output folder
        FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Build filename using query_id
        output_filename = f"{query_id}_simplified.txt"
        output_path = FINAL_OUTPUT_DIR / output_filename

        # Prepare content with metadata
        output_content = f"""QUERY ID: {query_id}
BOOK: {book_name}
ORIGINAL QUERY: {query}

{'='*80}

{response_text}
"""

        # Save response
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)

        logger.info(f"✓ Output saved successfully")
        logger.info(f"  File: {output_filename}")

        return str(output_path)

    except Exception as e:
        logger.error(f"Error saving output: {str(e)}")
        return None


def simplify_retrieval_payload(
    retrieval_payload: Dict[str, Any],
    api_key: Optional[str] = None,
    save_output_file: bool = True,
) -> Dict[str, Any]:
    """
    Simplify a raw retrieval payload for live API use.

    Returns a JSON-serializable response suitable for the backend.
    """
    if not isinstance(retrieval_payload, dict):
        return {
            "status": "error",
            "error": "retrieval payload must be a dictionary",
        }

    simplify_started = time.perf_counter()

    if retrieval_payload.get("status") != "success":
        return {
            "status": "error",
            "error": retrieval_payload.get("error", "retrieval stage failed"),
            "query_id": retrieval_payload.get("query_id"),
            "book": retrieval_payload.get("book"),
            "confidence": retrieval_payload.get("confidence", 0.0),
        }

    query_id = retrieval_payload.get("query_id") or "query_unknown"
    query = retrieval_payload.get("query", "")
    book_name = retrieval_payload.get("book", "Unknown")
    results = retrieval_payload.get("results", [])

    if not query or not results:
        return {
            "status": "error",
            "error": "query or retrieval results missing",
            "query_id": query_id,
            "book": book_name,
            "confidence": retrieval_payload.get("confidence", 0.0),
        }

    context_started = time.perf_counter()
    joined_context = extract_context_from_results(results)
    if not joined_context:
        return {
            "status": "error",
            "error": "failed to build simplification context",
            "query_id": query_id,
            "book": book_name,
            "confidence": retrieval_payload.get("confidence", 0.0),
        }
    logger.info(
        "Context extraction finished in %.2fs for query_id=%s",
        time.perf_counter() - context_started,
        query_id,
    )

    prompt_started = time.perf_counter()
    prompt = build_prompt(query, joined_context)
    logger.info(
        "Prompt build finished in %.2fs for query_id=%s (prompt length=%s)",
        time.perf_counter() - prompt_started,
        query_id,
        len(prompt),
    )

    effective_api_key = api_key
    if not effective_api_key:
        key_started = time.perf_counter()
        try:
            effective_api_key = load_api_key_from_env()
        except Exception as exc:
            return {
                "status": "error",
                "error": f"missing Gemini API key: {exc}",
                "query_id": query_id,
                "book": book_name,
                "confidence": retrieval_payload.get("confidence", 0.0),
            }
        logger.info(
            "API key loaded in %.2fs for query_id=%s",
            time.perf_counter() - key_started,
            query_id,
        )

    response_started = time.perf_counter()
    generation_result = generate_response(effective_api_key, prompt)
    response_text = generation_result.get(
        "response_text") if isinstance(generation_result, dict) else None
    if generation_result.get("status") != "success" or not response_text:
        return {
            "status": "error",
            "error": "simplification failed",
            "query_id": query_id,
            "book": book_name,
            "confidence": retrieval_payload.get("confidence", 0.0),
        }
    logger.info(
        "%s generation finished in %.2fs for query_id=%s",
        generation_result.get("provider", "unknown").capitalize(),
        time.perf_counter() - response_started,
        query_id,
    )

    output_path = None
    if save_output_file:
        save_started = time.perf_counter()
        output_path = save_output(response_text, query_id, query, book_name)
        logger.info(
            "Simplified output saved in %.2fs for query_id=%s",
            time.perf_counter() - save_started,
            query_id,
        )

    logger.info(
        "Simplification pipeline finished in %.2fs for query_id=%s",
        time.perf_counter() - simplify_started,
        query_id,
    )

    return {
        "status": "success",
        "answer": response_text,
        "confidence": retrieval_payload.get("confidence", 0.0),
        "query_id": query_id,
        "book": book_name,
        "source_path": output_path,
    }


def process_single_query(api_key: str, query_file: Path) -> bool:
    """
    Process a single query file end-to-end.

    Args:
        api_key: Gemini API key
        query_file: Path to query JSON file

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {query_file.name}")
        logger.info('='*70)

        # Step 1: Load query JSON
        query_data = load_query_json(query_file)
        if not query_data:
            logger.error(f"Failed to load query file: {query_file.name}")
            return False

        # Step 2: Extract data
        query_id = query_data.get('query_id')
        query = query_data.get('query', '')
        results = query_data.get('results', [])
        book_name = query_data.get('book', 'Unknown')

        if not query or not results:
            logger.error(f"Query or results missing in {query_file.name}")
            return False

        # Step 3: Extract context
        joined_context = extract_context_from_results(results)
        if not joined_context:
            logger.error(f"Failed to extract context from {query_file.name}")
            return False

        # Step 4: Build prompt
        prompt = build_prompt(query, joined_context)

        # Step 5: Generate response
        generation_result = generate_response(api_key, prompt)
        response_text = generation_result.get(
            "response_text") if isinstance(generation_result, dict) else None
        if generation_result.get("status") != "success" or not response_text:
            logger.error(f"Failed to generate response for {query_file.name}")
            return False

        # Step 6: Save output
        output_path = save_output(response_text, query_id, query, book_name)
        if not output_path:
            logger.error(f"Failed to save output for {query_file.name}")
            return False

        logger.info(f"✓ Successfully processed: {query_file.name}")
        return True

    except Exception as e:
        logger.error(
            f"Error processing query file {query_file.name}: {str(e)}")
        return False


def main():
    """Main execution function for batch processing."""
    try:
        logger.info("="*70)
        logger.info("RAG SIMPLIFICATION STAGE - BATCH PROCESSING WITH GEMINI")
        logger.info("="*70)

        # Step 1: Load API key
        api_key = load_api_key_from_env()

        # Step 2: Discover query files
        query_files = discover_query_files()

        if not query_files:
            logger.warning("No query files found to process")
            print("\n⚠️  No query files found in query_output folder.\n")
            return

        # Step 3: Process each query file
        successful_count = 0
        failed_count = 0

        for query_file in query_files:
            success = process_single_query(api_key, query_file)
            if success:
                successful_count += 1
            else:
                failed_count += 1

        # Step 4: Summary
        logger.info("\n" + "="*70)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("="*70)
        logger.info(f"Total files processed: {len(query_files)}")
        logger.info(f"Successful: {successful_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info("="*70)

        print("\n" + "="*70)
        print("BATCH PROCESSING COMPLETED")
        print("="*70)
        print(
            f"✓ Processed: {successful_count}/{len(query_files)} files successfully")
        if failed_count > 0:
            print(f"✗ Failed: {failed_count} files")
        print(f"✓ Output folder: {FINAL_OUTPUT_DIR}\n")

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        print(f"\n❌ Validation Error: {str(e)}\n")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n❌ Fatal Error: {str(e)}\n")
        raise


if __name__ == "__main__":
    main()
