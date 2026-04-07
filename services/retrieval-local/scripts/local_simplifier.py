import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

import google.generativeai as genai

# ============================================================================
# CONFIGURATION
# ============================================================================
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # retrieval-local folder
QUERY_OUTPUT_DIR = BASE_DIR / "outputs" / "query_output"
FINAL_OUTPUT_DIR = BASE_DIR / "outputs" / "final_output"
ENV_FILE = BASE_DIR / ".env"

MODEL_NAME = "gemini-2.5-flash"
TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 8000

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_api_key_from_env() -> str:
    """
    Load Gemini API key from .env file.
    
    Returns:
        API key string
        
    Raises:
        ValueError: If API key not found
    """
    try:
        # Load environment variables from .env file
        load_dotenv(ENV_FILE)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in .env file")
            raise ValueError(f"GEMINI_API_KEY not found in {ENV_FILE}")
        
        logger.info("✓ API key loaded successfully from .env file")
        return api_key
    
    except FileNotFoundError:
        logger.error(f".env file not found at {ENV_FILE}")
        raise ValueError(f".env file not found at {ENV_FILE}")
    except Exception as e:
        logger.error(f"Error loading API key: {str(e)}")
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
            logger.error(f"Query output directory not found: {QUERY_OUTPUT_DIR}")
            raise ValueError(f"Query output directory not found: {QUERY_OUTPUT_DIR}")
        
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
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Missing fields in {file_path.name}: {missing_fields}")
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
        for result in results:
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
1. PROVIDE DEPTH: While the language should be simple, the explanation must be detailed and thorough. Do not give a summary; give a full explanation.
2. STRUCTURE: Use the format below. Ensure the 'Detailed Explanation' section is the longest part of your response.
3. TONE: Academic, professional, and educational.
4. CONSTRAINTS: Use only provided data as long as it directly answers the query, but feel free to rephrase and expand on the logic to make it easier to understand.
5. REWRITE TOTALLY: If the user query and the context data are very different from each other and the data is not directly answering the query, you should rewrite the data in a way that it answers the query. Do not just summarize or give a short answer. You should rewrite the data in a way that it answers the query in a detailed and comprehensive manner.

FORMAT:
# [Title]

### Overview
[2-3 lines summarizing the core concept]

### Key Concepts
[Bullet points explaining the main terms found in the data]

### Detailed Academic Explanation
[Provide a multi-paragraph, in-depth explanation here. Elaborate on how the different pieces of data connect. This section should be at least 300 words long.]"""
    
    logger.info("✓ Prompt built successfully")
    return prompt


def generate_response(api_key: str, prompt: str) -> Optional[str]:
    """
    Generate response using Gemini API with error handling.
    
    Args:
        api_key: Gemini API key
        prompt: Formatted prompt string
        
    Returns:
        Generated response text or None on failure
    """
    try:
        # Configure API
        genai.configure(api_key=api_key)
        
        # Initialize model
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
            }
        )
        
        logger.info(f"Generating response with model: {MODEL_NAME}")
        
        # Generate content
        response = model.generate_content(prompt)
        
        if not response.text:
            logger.error("Empty response received from API")
            return None
        
        logger.info("✓ Response generated successfully")
        logger.info(f"  Response length: {len(response.text)} characters")
        
        return response.text
    
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return None


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
        response_text = generate_response(api_key, prompt)
        if not response_text:
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
        logger.error(f"Error processing query file {query_file.name}: {str(e)}")
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
        print(f"✓ Processed: {successful_count}/{len(query_files)} files successfully")
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