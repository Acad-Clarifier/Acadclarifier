import json
import os
import logging
import time
import uuid
import threading
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

_MODEL_CACHE: Optional[SentenceTransformer] = None
_MODEL_LOCK = threading.Lock()

# Configuration
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # retrieval-local folder
EMBEDDINGS_DIR = BASE_DIR / "outputs" / "embeddings_output"
OUTPUT_DIR = BASE_DIR / "outputs" / "query_output"
MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "text_embeddings"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
TOP_K = 5
SIMILARITY_THRESHOLD = 0.3

# Book titles mapping
BOOK_TITLES = {
    "book-1": "Database System Concepts Sixth Edition - Abraham Silberschatz",
    "book-2": "Hadoop in Action - Chuck Lam",
    "book-3": "Artificial Intelligence A Modern Approach Third Edition - Stuart Russell and Peter Norvig",
    "book-4": "Introduction to Algorithms Fourth Edition - Thomas H. Cormen",
    "book-5": "Computer Networks Fourth Edition - Andrew Tanenbaum",
    "book-6": "Distributed System Concepts and Design - George Colouris",
    "book-7": "Java The Complete Reference Seventh Edition - Herbert Schildt",
    "book-8": "Software Engineering A Practitioner's Approach Seventh Edition - Roger Pressman",
    "book-9": "Data Mining Concepts and Techniques, Third Edition - Jiawei Han",
    "book-10": "Human Computer Interaction Fundamentals and Practice - Gerard Jounghyun Kim"
}


def get_book_title(book_uid: str) -> str:
    """Return the display title for a book uid."""
    return BOOK_TITLES.get(book_uid, "Unknown Title")


def resolve_book_path(book_uid: str) -> Path:
    """Resolve the on-disk Chroma directory for a book uid."""
    return EMBEDDINGS_DIR / book_uid


def discover_available_books() -> List[str]:
    """
    Discover available books by scanning embeddings_output folder.
    Sorts books numerically (book-1, book-2, ..., book-10) not alphabetically.

    Returns:
        List of book names sorted numerically (e.g., ['book-1', 'book-2', ..., 'book-10'])
    """
    try:
        if not EMBEDDINGS_DIR.exists():
            logger.error(f"Embeddings directory not found: {EMBEDDINGS_DIR}")
            return []

        # Get all directories matching 'book-*' pattern
        books = []
        for item in EMBEDDINGS_DIR.iterdir():
            if item.is_dir() and item.name.startswith('book-'):
                books.append(item.name)

        # Sort numerically by extracting the book number
        # This ensures book-1, book-2, ..., book-10 (not book-1, book-10, book-2)
        books.sort(key=lambda x: int(x.replace('book-', '').replace('.', '0')))

        logger.info(f"Discovered {len(books)} books: {books}")
        return books
    except Exception as e:
        logger.error(f"Error discovering books: {str(e)}")
        return []


def display_available_books(books: List[str]):
    """
    Display list of available books to user with full titles.

    Args:
        books: List of book folder names
    """
    print("\n" + "="*90)
    print("AVAILABLE BOOKS IN LOCAL DATABASE")
    print("="*90)

    if not books:
        print("  No books available in the database.")
        print("="*90 + "\n")
        return

    for idx, book in enumerate(books, 1):
        title = BOOK_TITLES.get(book, "Unknown Title")
        print(f"  {idx}. {book} : {title}")

    print("="*90 + "\n")


def select_book(books: List[str]) -> Optional[str]:
    """
    Let user select a book from available list.

    Args:
        books: List of available book names

    Returns:
        Selected book name or None if cancelled/invalid
    """
    if not books:
        logger.warning("No books available for selection")
        print("❌ No books available in the local database.")
        print("   Please use WEB RETRIEVAL to search online sources.\n")
        return None

    while True:
        try:
            choice_str = input(
                "Enter the book number (or 0 to cancel): ").strip()

            if not choice_str.isdigit():
                print("Invalid input. Please enter a number.")
                continue

            choice = int(choice_str)

            if choice == 0:
                logger.info("User cancelled book selection")
                return None

            if 1 <= choice <= len(books):
                selected_book = books[choice - 1]
                selected_title = BOOK_TITLES.get(
                    selected_book, "Unknown Title")
                logger.info(
                    f"User selected: {selected_book} - {selected_title}")
                return selected_book
            else:
                print(
                    f"Invalid selection. Please enter a number between 1 and {len(books)}.")

        except Exception as e:
            logger.warning(f"Error in book selection: {str(e)}")
            print("Invalid input. Please try again.")


def load_model() -> Optional[SentenceTransformer]:
    """
    Load SentenceTransformer model for query embedding.

    Returns:
        Loaded SentenceTransformer model or None on failure
    """
    global _MODEL_CACHE

    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    with _MODEL_LOCK:
        if _MODEL_CACHE is not None:
            return _MODEL_CACHE

        try:
            logger.info(f"Loading model: {MODEL_NAME}")
            _MODEL_CACHE = SentenceTransformer(MODEL_NAME)
            logger.info("✓ Model loaded successfully")
            return _MODEL_CACHE
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return None


def initialize_chromadb_for_book(book_name: str) -> Optional[chromadb.Client]:
    """
    Connect to ChromaDB for specific book.

    Args:
        book_name: Name of the book folder (e.g., 'book-1')

    Returns:
        ChromaDB client or None on failure
    """
    try:
        book_db_path = EMBEDDINGS_DIR / book_name

        if not book_db_path.exists():
            logger.error(f"Book database not found: {book_db_path}")
            return None

        client = chromadb.PersistentClient(path=str(book_db_path))
        logger.info(f"✓ Connected to ChromaDB for {book_name}")
        return client

    except Exception as e:
        logger.error(f"Error initializing ChromaDB for {book_name}: {str(e)}")
        return None


def load_collection(client: chromadb.Client) -> Optional[chromadb.Collection]:
    """
    Load existing collection from ChromaDB.

    Args:
        client: ChromaDB client

    Returns:
        Collection object or None on failure
    """
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        count = collection.count()
        logger.info(f"✓ Loaded collection with {count} embeddings")
        return collection
    except Exception as e:
        logger.error(f"Error loading collection: {str(e)}")
        return None


def run_retrieval_request(
    query: str,
    book_uid: Optional[str],
    query_id: Optional[str] = None,
    save_output_file: bool = True,
) -> Dict:
    """
    Run the local retrieval pipeline programmatically.

    Returns a JSON-serializable payload suitable for the simplifier.
    """
    if not isinstance(query, str) or not query.strip():
        return {
            "status": "error",
            "error": "query must be a non-empty string",
            "query_id": query_id or generate_query_id(),
            "book": book_uid,
            "confidence": 0.0,
        }

    if not isinstance(book_uid, str) or not book_uid.strip():
        return {
            "status": "error",
            "error": "book selection is required",
            "query_id": query_id or generate_query_id(),
            "book": None,
            "confidence": 0.0,
        }

    normalized_query = query.strip()
    normalized_book_uid = book_uid.strip()
    resolved_query_id = query_id or generate_query_id()

    model = load_model()
    if not model:
        return {
            "status": "error",
            "error": "failed to load embedding model",
            "query_id": resolved_query_id,
            "book": normalized_book_uid,
            "confidence": 0.0,
        }

    client = initialize_chromadb_for_book(normalized_book_uid)
    if not client:
        return {
            "status": "error",
            "error": f"missing embeddings for book '{normalized_book_uid}'",
            "query_id": resolved_query_id,
            "book": normalized_book_uid,
            "confidence": 0.0,
        }

    collection = load_collection(client)
    if not collection:
        return {
            "status": "error",
            "error": f"failed to load collection for book '{normalized_book_uid}'",
            "query_id": resolved_query_id,
            "book": normalized_book_uid,
            "confidence": 0.0,
        }

    query_embedding = embed_query(normalized_query, model)
    if query_embedding is None:
        return {
            "status": "error",
            "error": "failed to generate query embedding",
            "query_id": resolved_query_id,
            "book": normalized_book_uid,
            "confidence": 0.0,
        }

    results = retrieve_documents(collection, query_embedding)
    if results is None:
        return {
            "status": "error",
            "error": "retrieval failed",
            "query_id": resolved_query_id,
            "book": normalized_book_uid,
            "confidence": 0.0,
        }

    similarity_scores, chunk_ids, result_data = process_results(results)
    if similarity_scores is None or not result_data:
        return {
            "status": "error",
            "error": "no sufficiently relevant content found",
            "query_id": resolved_query_id,
            "book": normalized_book_uid,
            "confidence": 0.0,
        }

    book_title = get_book_title(normalized_book_uid)
    retrieval_output_path = None
    if save_output_file:
        save_results(
            resolved_query_id,
            normalized_query,
            normalized_book_uid,
            similarity_scores,
            chunk_ids,
            result_data,
        )
        retrieval_output_path = str(OUTPUT_DIR / f"{resolved_query_id}.json")

    return {
        "status": "success",
        "query_id": resolved_query_id,
        "query": normalized_query,
        "book": normalized_book_uid,
        "book_title": book_title,
        "results": result_data,
        "confidence": round(similarity_scores[0], 4) if similarity_scores else 0.0,
        "summary": {
            "total_results": len(result_data),
            "top_similarity_score": round(similarity_scores[0], 4) if similarity_scores else None,
            "threshold_used": SIMILARITY_THRESHOLD,
            "model_used": MODEL_NAME,
        },
        "retrieval_source_path": retrieval_output_path,
    }


def get_user_query() -> Optional[str]:
    """
    Accept user query from terminal input.

    Returns:
        Cleaned user query string or None on error
    """
    try:
        query = input("\nEnter your query: ").strip()

        if not query:
            logger.error("Empty query provided")
            print("❌ Query cannot be empty.")
            return None

        # Check for minimum query length (at least 3 characters)
        if len(query) < 3:
            logger.error("Query too short")
            print("❌ Query must be at least 3 characters long.")
            return None

        logger.info(f"Query received: {query[:100]}")
        return query
    except Exception as e:
        logger.error(f"Error reading query: {str(e)}")
        return None


def embed_query(query: str, model: SentenceTransformer) -> Optional[np.ndarray]:
    """
    Generate embedding for query with BGE prefix.

    Args:
        query: User query string
        model: SentenceTransformer model

    Returns:
        Query embedding as numpy array or None on failure
    """
    try:
        # Add BGE prefix for retrieval
        prefixed_query = BGE_QUERY_PREFIX + query
        logger.info("Generating query embedding...")

        start_time = time.time()

        # Generate embedding with normalization
        query_embedding = model.encode(
            prefixed_query,
            batch_size=1,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        elapsed_time = time.time() - start_time
        logger.info(
            f"✓ Query embedding generated in {elapsed_time:.4f} seconds")

        return query_embedding
    except Exception as e:
        logger.error(f"Error embedding query: {str(e)}")
        return None


def retrieve_documents(
    collection: chromadb.Collection,
    query_embedding: np.ndarray
) -> Optional[Dict]:
    """
    Perform cosine similarity search in ChromaDB.

    Args:
        collection: ChromaDB collection
        query_embedding: Query embedding array

    Returns:
        Dictionary with retrieval results or None on failure
    """
    try:
        logger.info(f"Querying collection for top {TOP_K} results...")
        start_time = time.time()

        # Query collection with cosine similarity
        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=TOP_K,
            include=["documents", "distances", "metadatas"]
        )

        elapsed_time = time.time() - start_time
        logger.info(f"✓ Retrieval completed in {elapsed_time:.4f} seconds")

        return results
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        return None


def process_results(results: Dict) -> Tuple[Optional[List[float]], Optional[List[str]], Optional[List[Dict]]]:
    """
    Process and validate retrieval results.

    Args:
        results: Raw ChromaDB query results

    Returns:
        Tuple of (similarity_scores, chunk_ids, result_data) or (None, None, None) on failure
    """
    try:
        if not results:
            logger.error("No results provided")
            return None, None, None

        # Extract components with safety checks
        documents = results.get('documents', [[]])[
            0] if results.get('documents') else []
        distances = results.get('distances', [[]])[
            0] if results.get('distances') else []
        metadatas = results.get('metadatas', [[]])[
            0] if results.get('metadatas') else []

        if not documents or len(documents) == 0:
            logger.warning("No documents retrieved")
            return None, None, None

        # Convert Chroma distances to cosine similarity scores
        # Chroma returns distances; for cosine: similarity = 1 - distance
        similarity_scores = [1 - dist for dist in distances]

        # Extract chunk IDs from metadata
        chunk_ids = [
            str(meta.get('chunk_id', 'N/A')) for meta in metadatas
        ]

        # Check similarity threshold
        if similarity_scores[0] < SIMILARITY_THRESHOLD:
            logger.warning(
                f"Highest similarity score {similarity_scores[0]:.4f} "
                f"is below threshold {SIMILARITY_THRESHOLD}"
            )
            return None, None, None

        # Prepare result data
        result_data = [
            {
                "rank": i + 1,
                "chunk_id": chunk_ids[i],
                "similarity_score": round(similarity_scores[i], 4),
                "document": documents[i]
            }
            for i in range(len(documents))
        ]

        logger.info(f"✓ Processed {len(documents)} results successfully")
        return similarity_scores, chunk_ids, result_data

    except Exception as e:
        logger.error(f"Error processing results: {str(e)}")
        return None, None, None


def generate_query_id() -> str:
    """
    Generate unique query ID with timestamp.

    Returns:
        Unique query ID string
    """
    return f"query_{int(time.time())}_{str(uuid.uuid4())[:8]}"


def display_results(result_data: List[Dict]):
    """
    Display retrieval results in formatted output.

    Args:
        result_data: List of result dictionaries
    """
    print("\n" + "="*70)
    print("RETRIEVAL RESULTS")
    print("="*70)

    for result in result_data:
        print(f"\nRank {result['rank']}: Chunk ID {result['chunk_id']}")
        print(f"Similarity Score: {result['similarity_score']}")
        print(f"\nContent:")
        print("-" * 70)
        print(result['document'][:500] +
              "..." if len(result['document']) > 500 else result['document'])
        print("-" * 70)


def save_results(
    query_id: str,
    query: str,
    book_name: str,
    similarity_scores: List[float],
    chunk_ids: List[str],
    result_data: List[Dict]
) -> bool:
    """
    Save retrieval results to output directory as JSON.

    Args:
        query_id: Unique query identifier
        query: Original user query
        book_name: Selected book name
        similarity_scores: List of similarity scores
        chunk_ids: List of chunk IDs
        result_data: List of result dictionaries

    Returns:
        True if successful, False otherwise
    """
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Prepare output structure
        output = {
            "query_id": query_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "book": book_name,
            "results": result_data,
            "summary": {
                "total_results": len(result_data),
                "top_similarity_score": round(similarity_scores[0], 4) if similarity_scores else None,
                "threshold_used": SIMILARITY_THRESHOLD,
                "model_used": MODEL_NAME
            }
        }

        # Save as JSON with query_id in filename
        output_file = OUTPUT_DIR / f"{query_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Results saved to {output_file}")
        print(f"\n✓ Query results saved with ID: {query_id}")

        return True

    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        return False


def perform_another_query() -> bool:
    """
    Ask user if they want to perform another query.

    Returns:
        True if user wants to continue, False otherwise
    """
    while True:
        response = input(
            "\nDo you want to perform another query? (yes/no): ").strip().lower()

        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")


def main():
    """Main execution function for local RAG retrieval stage."""
    try:
        logger.info("="*70)
        logger.info("LOCAL RAG RETRIEVAL SYSTEM - USER QUERY PROCESSING")
        logger.info("="*70)

        # Step 1: Discover available books
        logger.info("Scanning for available books...")
        available_books = discover_available_books()

        if not available_books:
            logger.error("No books found in embeddings database")
            print("❌ No books found in the embeddings database.")
            print("   Please check that embeddings have been generated.")
            print("   Alternatively, use WEB RETRIEVAL to search online sources.\n")
            return

        # Main loop for multiple queries
        while True:
            # Step 2: Display books and let user select
            display_available_books(available_books)
            selected_book = select_book(available_books)

            if not selected_book:
                print("⚠️  No book selected.")
                print("   Please use WEB RETRIEVAL to search online sources.\n")
                break

            # Step 3: Accept user query
            selected_title = BOOK_TITLES.get(selected_book, "Unknown Title")
            print(f"\nSelected Book: {selected_book}")
            print(f"Title: {selected_title}")
            query = get_user_query()

            if not query:
                print("Invalid query. Please try again.\n")
                continue

            # Step 4: Load components
            model = load_model()
            if not model:
                print("❌ Failed to load embedding model. Please try again.\n")
                continue

            client = initialize_chromadb_for_book(selected_book)
            if not client:
                print(
                    f"❌ Failed to connect to {selected_book} database. Please try again.\n")
                continue

            collection = load_collection(client)
            if not collection:
                print(
                    f"❌ Failed to load {selected_book} collection. Please try again.\n")
                continue

            # Step 5: Embed query
            query_embedding = embed_query(query, model)
            if query_embedding is None:
                print("❌ Failed to embed query. Please try again.\n")
                continue

            # Step 6: Retrieve documents from selected book only
            results = retrieve_documents(collection, query_embedding)
            if results is None:
                print("❌ Failed to retrieve documents. Please try again.\n")
                continue

            # Step 7: Process results
            similarity_scores, chunk_ids, result_data = process_results(
                results)

            # Step 8: Check if results meet threshold
            if similarity_scores is None or not result_data:
                print("⚠️  No sufficiently relevant content found.")
                print("   The query might have low relevance to the selected book.")
                print("   Please try another query or select a different book.\n")

                if not perform_another_query():
                    break
                continue

            # Step 9: Display results
            display_results(result_data)

            # Step 10: Generate unique query ID and save results
            query_id = generate_query_id()
            success = save_results(
                query_id,
                query,
                selected_book,
                similarity_scores,
                chunk_ids,
                result_data
            )

            if not success:
                print("⚠️  Failed to save results to file.")
                logger.error("Failed to save results")

            # Step 11: Ask for another query
            if not perform_another_query():
                break

        logger.info("="*70)
        logger.info("✓ RETRIEVAL SESSION COMPLETED")
        logger.info("="*70)
        print("\n✓ Thank you for using the Local RAG Retrieval System!\n")

    except KeyboardInterrupt:
        logger.info("User interrupted the program")
        print("\n\n⚠️  Session interrupted by user.\n")
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        print(f"\n❌ Fatal error: {str(e)}\n")
        raise


if __name__ == "__main__":
    main()
