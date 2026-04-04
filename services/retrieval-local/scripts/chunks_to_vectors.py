import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # retrieval-local folder
INPUT_FOLDER = BASE_DIR / "outputs" / "chunking_output"
OUTPUT_DIR = BASE_DIR / "outputs" / "embeddings_output"
MODEL_NAME = "BAAI/bge-base-en-v1.5"
BATCH_SIZE = 32
MIN_TEXT_LENGTH = 10
MAX_TEXT_LENGTH = 8192


def list_available_chunk_files(input_folder: Path) -> List[str]:
    """
    List all available chunk JSON files in the input folder.
    
    Args:
        input_folder (Path): Path to the folder containing chunk files
    
    Returns:
        list: List of chunk JSON filenames (sorted)
    """
    if not input_folder.exists():
        logger.error(f"Input folder not found at {input_folder}")
        return []
    
    json_files = sorted([f.name for f in input_folder.glob('*_chunks.json')])
    return json_files


def select_file(file_list: List[str]) -> str:
    """
    Display available chunk files and let user select one.
    
    Args:
        file_list (list): List of available chunk JSON filenames
    
    Returns:
        str: Selected JSON filename or None if invalid selection
    """
    if not file_list:
        logger.info("No chunk files found in the input folder.")
        return None
    
    print("\n" + "="*50)
    print("Available Chunk Files:")
    print("="*50)
    for idx, json_file in enumerate(file_list, 1):
        print(f"{idx}. {json_file}")
    
    print("\n" + "="*50)
    try:
        choice = int(input("Enter the file number to process (or 0 to cancel): "))
        if choice == 0:
            return None
        if 1 <= choice <= len(file_list):
            return file_list[choice - 1]
        else:
            logger.warning("Invalid selection. Please enter a valid file number.")
            return None
    except ValueError:
        logger.warning("Invalid input. Please enter a number.")
        return None


def extract_book_number(filename: str) -> int:
    """
    Extract book number from chunk filename.
    For example: 'book-1_chunks.json' -> 1
    
    Args:
        filename (str): The chunk JSON filename
    
    Returns:
        int: Book number
    """
    try:
        book_num = filename.replace('book-', '').replace('_chunks.json', '')
        return int(book_num)
    except (ValueError, IndexError):
        return 1


def load_chunks(file_path: Path) -> List[Tuple[int, str]]:
    """
    Load chunks from JSON file, extracting only text content.
    
    Args:
        file_path: Path to chunks.json
        
    Returns:
        List of tuples (chunk_id, text)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = []
        if 'chunks' not in data:
            logger.error("'chunks' key not found in JSON")
            return chunks
        
        for chunk in data['chunks']:
            chunk_id = chunk.get('chunk_id')
            text = chunk.get('text', '').strip()
            
            # Validate chunk
            if chunk_id is None:
                logger.warning("Chunk missing chunk_id, skipping")
                continue
            
            if not text:
                logger.warning(f"Chunk {chunk_id} has empty text, skipping")
                continue
            
            if len(text) < MIN_TEXT_LENGTH:
                logger.warning(f"Chunk {chunk_id} text too short ({len(text)} chars), skipping")
                continue
            
            if len(text) > MAX_TEXT_LENGTH:
                logger.warning(f"Chunk {chunk_id} text too long ({len(text)} chars), truncating")
                text = text[:MAX_TEXT_LENGTH]
            
            chunks.append((chunk_id, text))
        
        logger.info(f"Loaded {len(chunks)} valid chunks from {file_path}")
        return chunks
    
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading chunks: {str(e)}")
        return []


def generate_embeddings(texts: List[str], model: SentenceTransformer) -> np.ndarray:
    """
    Generate embeddings for texts with proper error handling.
    
    Args:
        texts: List of text strings
        model: SentenceTransformer model
        
    Returns:
        Numpy array of embeddings
    """
    try:
        if not texts:
            logger.warning("No texts provided for embedding")
            return np.array([])
        
        # Normalize and clean texts
        cleaned_texts = []
        for text in texts:
            # Remove extra whitespace
            cleaned = ' '.join(text.split())
            # Ensure non-empty
            if cleaned:
                cleaned_texts.append(cleaned)
            else:
                cleaned_texts.append("[EMPTY]")
        
        # Generate embeddings
        embeddings = model.encode(
            cleaned_texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Important for cosine similarity
        )
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        return np.array([])


def initialize_chromadb(output_dir: Path) -> chromadb.Client:
    """
    Initialize ChromaDB client with persistent storage.
    
    Args:
        output_dir: Directory to store ChromaDB data
        
    Returns:
        ChromaDB client
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use new PersistentClient API (replaces deprecated Settings approach)
        client = chromadb.PersistentClient(path=str(output_dir))
        logger.info(f"Initialized ChromaDB with persist directory: {output_dir}")
        return client
    
    except Exception as e:
        logger.error(f"Error initializing ChromaDB: {str(e)}")
        raise


def store_embeddings_in_chromadb(
    client: chromadb.Client,
    chunks: List[Tuple[int, str]],
    embeddings: np.ndarray,
    collection_name: str = "text_embeddings"
) -> bool:
    """
    Store embeddings and metadata in ChromaDB with batching.
    
    Args:
        client: ChromaDB client
        chunks: List of (chunk_id, text) tuples
        embeddings: Numpy array of embeddings
        collection_name: Name for the collection
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if len(chunks) != len(embeddings):
            logger.error(f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")
            return False
        
        if len(chunks) == 0:
            logger.warning("No chunks to store")
            return False
        
        # Delete existing collection if present
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted existing collection: {collection_name}")
        except Exception:
            pass
        
        # Create collection
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Prepare data for insertion
        ids = [str(chunk_id) for chunk_id, _ in chunks]
        documents = [text for _, text in chunks]
        embeddings_list = embeddings.tolist()
        metadatas = [{"chunk_id": chunk_id} for chunk_id, _ in chunks]
        
        # Add embeddings in batches to avoid ChromaDB batch size limits
        batch_size = 5000  # ChromaDB max batch size is ~5461
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(chunks))
            
            batch_ids = ids[start_idx:end_idx]
            batch_documents = documents[start_idx:end_idx]
            batch_embeddings = embeddings_list[start_idx:end_idx]
            batch_metadatas = metadatas[start_idx:end_idx]
            
            collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
            
            logger.info(f"Added batch {batch_idx + 1}/{total_batches} ({len(batch_ids)} embeddings)")
        
        logger.info(f"Stored {len(chunks)} embeddings in collection: {collection_name}")
        
        # ChromaDB automatically persists with PersistentClient
        logger.info("ChromaDB data stored persistently")
        return True
    
    except Exception as e:
        logger.error(f"Error storing embeddings in ChromaDB: {str(e)}")
        return False


def verify_embeddings_quality(embeddings: np.ndarray) -> Dict:
    """
    Verify embeddings quality for cosine similarity.
    
    Args:
        embeddings: Numpy array of embeddings
        
    Returns:
        Dictionary with quality metrics
    """
    try:
        metrics = {
            "total_embeddings": len(embeddings),
            "embedding_dim": embeddings.shape[1] if len(embeddings) > 0 else 0,
            "norms": np.linalg.norm(embeddings, axis=1) if len(embeddings) > 0 else [],
            "all_normalized": np.allclose(
                np.linalg.norm(embeddings, axis=1), 1.0
            ) if len(embeddings) > 0 else False
        }
        
        logger.info(f"Embedding Quality Metrics: {metrics}")
        return metrics
    
    except Exception as e:
        logger.error(f"Error verifying embeddings: {str(e)}")
        return {}


def process_single_book(selected_file: str, book_number: int):
    """
    Process a single book's chunks to vectors.
    
    Args:
        selected_file: Name of the chunk JSON file
        book_number: Book number for folder naming
    """
    try:
        # Load chunks
        logger.info(f"Loading chunks from {selected_file}...")
        chunks_file_path = INPUT_FOLDER / selected_file
        chunks = load_chunks(chunks_file_path)
        
        if not chunks:
            logger.error("No valid chunks loaded")
            return
        
        # Load model
        logger.info(f"Loading model: {MODEL_NAME}")
        model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded successfully")
        
        # Extract texts from chunks
        texts = [text for _, text in chunks]
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = generate_embeddings(texts, model)
        
        if len(embeddings) == 0:
            logger.error("Failed to generate embeddings")
            return
        
        # Verify embeddings quality
        logger.info("Verifying embeddings quality...")
        verify_embeddings_quality(embeddings)
        
        # Create book-specific output directory
        book_output_dir = OUTPUT_DIR / f"book-{book_number}"
        logger.info(f"Using output directory: {book_output_dir}")
        
        # Initialize ChromaDB for this book
        logger.info("Initializing ChromaDB...")
        client = initialize_chromadb(book_output_dir)
        
        # Store embeddings
        logger.info("Storing embeddings in ChromaDB...")
        success = store_embeddings_in_chromadb(client, chunks, embeddings)
        
        if success:
            logger.info(f"✓ Book-{book_number}: All embeddings stored successfully")
        else:
            logger.error(f"✗ Book-{book_number}: Failed to store embeddings")
    
    except Exception as e:
        logger.error(f"Fatal error processing book: {str(e)}")


def main():
    """Main execution function."""
    try:
        # List available chunk files
        logger.info("Scanning for chunk files...")
        available_files = list_available_chunk_files(INPUT_FOLDER)
        
        if not available_files:
            logger.error("No chunk files found in the input folder.")
            logger.info(f"Expected location: {INPUT_FOLDER}")
            return
        
        # Loop until user presses 0
        while True:
            # Let user select a file
            selected_file = select_file(available_files)
            
            if selected_file:
                book_number = extract_book_number(selected_file)
                logger.info(f"Processing {selected_file} (Book {book_number})...")
                process_single_book(selected_file, book_number)
                print()  # Add blank line for better readability
            else:
                # User pressed 0 or made invalid selection
                logger.info("Exiting embeddings converter. Goodbye!")
                break
    
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()