import sqlite3
import chromadb
import logging
from typing import Optional, List, Dict
from sentence_transformers import SentenceTransformer
from pathlib import Path
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Singleton pattern for embedding model to avoid reloading."""
    _instance: Optional['EmbeddingModel'] = None
    _model: Optional[SentenceTransformer] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_model()
        return cls._instance
    
    def _initialize_model(self):
        """Initialize the embedding model with error handling."""
        try:
            logger.info("Loading sentence-transformers model: all-MiniLM-L6-v2")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✓ Model loaded successfully")
        except Exception as e:
            logger.error(f"✗ Failed to load embedding model: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode texts to embeddings."""
        if self._model is None:
            raise RuntimeError("Model not initialized")
        return self._model.encode(texts, show_progress_bar=False)


class ChromaDBManager:
    """Manages ChromaDB operations with persistent storage."""
    
    def __init__(self, persist_dir: str = "./chroma_data"):
        """
        Initialize ChromaDB manager with persistent storage.
        
        Args:
            persist_dir: Directory for persistent ChromaDB storage
        """
        self.persist_dir = persist_dir
        self.client = None
        self.collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client with persistent storage using new API."""
        try:
            Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
            
            # Use new ChromaDB PersistentClient API (0.4+)
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            logger.info(f"✓ ChromaDB client initialized with persist_dir: {self.persist_dir}")
        except Exception as e:
            logger.error(f"✗ Failed to initialize ChromaDB client: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def get_or_create_collection(self, collection_name: str = "books"):
        """
        Get existing collection or create a new one.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            ChromaDB collection object
        """
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"✓ Collection '{collection_name}' retrieved/created")
            return self.collection
        except Exception as e:
            logger.error(f"✗ Failed to get/create collection: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def collection_exists(self, book_id: str) -> bool:
        """Check if a book already exists in the collection."""
        if self.collection is None:
            return False
        try:
            result = self.collection.get(ids=[book_id])
            return len(result['ids']) > 0
        except Exception as e:
            logger.warning(f"Error checking if book exists: {str(e)}")
            return False
    
    def add_document(self, book_id: str, summary: str, embedding: List[float],
                    metadata: Dict) -> bool:
        """
        Add a document to ChromaDB with error handling.
        
        Args:
            book_id: Unique book identifier
            summary: Book summary text
            embedding: Embedding vector
            metadata: Document metadata (title, author, category)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.collection_exists(book_id):
                logger.warning(f"Book {book_id} already exists, skipping")
                return False
            
            self.collection.add(
                ids=[book_id],
                documents=[summary],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            logger.info(f"✓ Added book {book_id}: {metadata.get('title', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to add document {book_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def persist(self):
        """Persist data to disk (automatic in new ChromaDB API)."""
        try:
            # The new PersistentClient automatically persists data
            # This method is kept for API compatibility
            logger.info("✓ Data automatically persisted with PersistentClient")
        except Exception as e:
            logger.warning(f"Warning: Failed to persist ChromaDB: {str(e)}")


class SQLiteManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: str = "library.db"):
        """
        Initialize SQLite manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_processed_column()
    
    def _ensure_processed_column(self):
        """Ensure 'processed' column exists in books table."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Check if processed column exists
            cur.execute("PRAGMA table_info(books)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'processed' not in columns:
                logger.info("Adding 'processed' column to books table")
                cur.execute("ALTER TABLE books ADD COLUMN processed INTEGER DEFAULT 0")
                conn.commit()
                logger.info("✓ 'processed' column added")
            
            conn.close()
        except Exception as e:
            logger.error(f"✗ Failed to ensure processed column: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def get_unprocessed_books(self) -> List[Dict]:
        """
        Retrieve all unprocessed books from database.
        
        Returns:
            List of book dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("""
                SELECT book_id, title, author, category, summary
                FROM books
                WHERE processed = 0 OR processed IS NULL
                ORDER BY book_id
            """)
            
            books = [dict(row) for row in cur.fetchall()]
            conn.close()
            
            logger.info(f"Retrieved {len(books)} unprocessed books")
            return books
        except Exception as e:
            logger.error(f"✗ Failed to retrieve unprocessed books: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def mark_processed(self, book_id: str) -> bool:
        """
        Mark a book as processed with transactional integrity.
        
        Args:
            book_id: Book ID to mark as processed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.isolation_level = None  # Autocommit disabled
            cur = conn.cursor()
            
            # Start transaction
            cur.execute("BEGIN TRANSACTION")
            
            try:
                cur.execute("""
                    UPDATE books
                    SET processed = 1
                    WHERE book_id = ?
                """, (book_id,))
                
                if cur.rowcount == 0:
                    raise ValueError(f"No book found with ID {book_id}")
                
                # Commit transaction
                cur.execute("COMMIT")
                logger.info(f"✓ Marked book {book_id} as processed")
                return True
            except Exception as e:
                cur.execute("ROLLBACK")
                raise
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"✗ Failed to mark book {book_id} as processed: {str(e)}")
            logger.error(traceback.format_exc())
            return False


def migrate_sql_to_chromadb(chroma_persist_dir: str = "./chroma_data",
                           db_path: str = "library.db"):
    """
    Main migration function: transfer book data from SQLite to ChromaDB.
    
    Args:
        chroma_persist_dir: Directory for ChromaDB persistent storage
        db_path: Path to SQLite database
    """
    logger.info("=" * 60)
    logger.info("Starting SQLite to ChromaDB Migration")
    logger.info("=" * 60)
    
    try:
        # Initialize components
        embedding_model = EmbeddingModel()
        chroma_manager = ChromaDBManager(persist_dir=chroma_persist_dir)
        sql_manager = SQLiteManager(db_path=db_path)
        
        # Get or create collection
        chroma_manager.get_or_create_collection("books")
        
        # Retrieve unprocessed books
        books = sql_manager.get_unprocessed_books()
        
        if not books:
            logger.info("No unprocessed books found. Migration complete.")
            return
        
        logger.info(f"Processing {len(books)} books...")
        logger.info("-" * 60)
        
        successful = 0
        failed = 0
        duplicates = 0
        
        # Process each book
        for idx, book in enumerate(books, 1):
            book_id = book['book_id']
            summary = book['summary']
            
            try:
                # Check for duplicates
                if chroma_manager.collection_exists(book_id):
                    logger.warning(f"[{idx}/{len(books)}] {book_id} already in ChromaDB (skipping)")
                    duplicates += 1
                    # Still mark as processed
                    sql_manager.mark_processed(book_id)
                    continue
                
                # Generate embedding
                embedding = embedding_model.encode([summary])[0]
                
                # Prepare metadata
                metadata = {
                    'title': book['title'],
                    'author': book['author'],
                    'category': book['category']
                }
                
                # Add to ChromaDB
                if chroma_manager.add_document(book_id, summary, embedding, metadata):
                    # Mark as processed in SQLite
                    if sql_manager.mark_processed(book_id):
                        successful += 1
                    else:
                        failed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing book {book_id}: {str(e)}")
                failed += 1
        
        # Persist ChromaDB
        chroma_manager.persist()
        
        # Print summary
        logger.info("-" * 60)
        logger.info("Migration Summary:")
        logger.info(f"  ✓ Successful: {successful}")
        logger.info(f"  ⊘ Duplicates: {duplicates}")
        logger.info(f"  ✗ Failed: {failed}")
        logger.info(f"  Total Processed: {successful + duplicates}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Migration failed with error: {str(e)}")
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    migrate_sql_to_chromadb()
