import chromadb
import logging
from typing import Optional, List, Dict
from sentence_transformers import SentenceTransformer
from pathlib import Path
import traceback
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Constants for validation
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 500
TOP_K_DEFAULT = 5
SIMILARITY_THRESHOLD = 0.3  # Filter out very low similarity results


class QueryValidator:
    """Validates and sanitizes user queries."""
    
    @staticmethod
    def validate_query(query: str) -> tuple[bool, str, Optional[str]]:
        """
        Validate user query with comprehensive checks.
        
        Args:
            query: User input query string
            
        Returns:
            Tuple of (is_valid, sanitized_query, error_message)
        """
        # Check if query is None or not a string
        if query is None:
            return False, "", "Query cannot be None"
        
        if not isinstance(query, str):
            return False, "", f"Query must be a string, got {type(query).__name__}"
        
        # Strip whitespace
        sanitized = query.strip()
        
        # Check if empty after stripping
        if len(sanitized) == 0:
            return False, "", "Query cannot be empty or contain only whitespace"
        
        # Check minimum length
        if len(sanitized) < MIN_QUERY_LENGTH:
            return False, "", f"Query too short. Minimum {MIN_QUERY_LENGTH} characters required"
        
        # Check maximum length
        if len(sanitized) > MAX_QUERY_LENGTH:
            return False, "", f"Query too long. Maximum {MAX_QUERY_LENGTH} characters allowed"
        
        # Check for special characters only (allow alphanumeric, spaces, common punctuation)
        if not re.search(r'[a-zA-Z0-9]', sanitized):
            return False, "", "Query must contain at least one letter or number"
        
        # Warn if contains unusual characters, but allow them
        if re.search(r'[<>{}[\]\\|`~^]', sanitized):
            logger.warning(f"Query contains unusual characters: {sanitized}")
        
        return True, sanitized, None
    
    @staticmethod
    def validate_top_k(top_k: int) -> tuple[bool, int, Optional[str]]:
        """
        Validate top_k parameter.
        
        Args:
            top_k: Number of top results to return
            
        Returns:
            Tuple of (is_valid, validated_top_k, error_message)
        """
        if not isinstance(top_k, int):
            return False, TOP_K_DEFAULT, f"top_k must be an integer, got {type(top_k).__name__}"
        
        if top_k < 1:
            return False, TOP_K_DEFAULT, "top_k must be at least 1"
        
        if top_k > 100:
            logger.warning(f"top_k={top_k} is very large, limiting to 100")
            return True, 100, None
        
        return True, top_k, None


class BookRecommender:
    """Recommends books based on semantic similarity."""
    
    def __init__(self, chroma_persist_dir: str = "./chroma_data"):
        """
        Initialize the Book Recommender.
        
        Args:
            chroma_persist_dir: Path to ChromaDB persistent storage
        """
        self.chroma_persist_dir = chroma_persist_dir
        self.client = None
        self.collection = None
        self.embedding_model = None
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB client and embedding model."""
        try:
            # Check if persistence directory exists
            if not Path(self.chroma_persist_dir).exists():
                raise FileNotFoundError(
                    f"ChromaDB directory not found: {self.chroma_persist_dir}\n"
                    "Please run sql_to_chromadb.py first to create embeddings."
                )
            
            logger.info("Initializing BookRecommender...")
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=self.chroma_persist_dir)
            logger.info(f"✓ Connected to ChromaDB at {self.chroma_persist_dir}")
            
            # Get the books collection
            try:
                self.collection = self.client.get_collection(name="books")
                collection_count = self.collection.count()
                logger.info(f"✓ Loaded 'books' collection with {collection_count} documents")
                
                if collection_count == 0:
                    raise ValueError(
                        "Books collection is empty. "
                        "Please run sql_to_chromadb.py to populate the collection."
                    )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load 'books' collection: {str(e)}\n"
                    "Make sure sql_to_chromadb.py has been executed successfully."
                )
            
            # Initialize embedding model (singleton)
            self.embedding_model = self._get_embedding_model()
            logger.info("✓ Embedding model loaded")
            
        except Exception as e:
            logger.error(f"✗ Failed to initialize BookRecommender: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    @staticmethod
    def _get_embedding_model() -> SentenceTransformer:
        """Get or create embedding model (singleton-like behavior)."""
        try:
            logger.info("Loading sentence-transformers model: all-MiniLM-L6-v2")
            model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✓ Model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"✗ Failed to load embedding model: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _encode_query(self, query: str) -> Optional[List[float]]:
        """
        Encode query to embedding vector.
        
        Args:
            query: Sanitized query string
            
        Returns:
            Embedding vector or None on error
        """
        try:
            embedding = self.embedding_model.encode([query], show_progress_bar=False)[0]
            return embedding.tolist()  # Convert numpy array to list
        except Exception as e:
            logger.error(f"✗ Failed to encode query: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def query(self, user_query: str, top_k: int = TOP_K_DEFAULT) -> List[Dict]:
        """
        Query the book collection and return top similar books.
        
        Args:
            user_query: User's search query
            top_k: Number of top results to return (default: 5)
            
        Returns:
            List of recommended books with similarity scores
        """
        logger.info("=" * 70)
        logger.info(f"Processing user query: '{user_query}'")
        logger.info(f"Requested top_k: {top_k}")
        
        # Validate query
        is_valid, sanitized_query, error_msg = QueryValidator.validate_query(user_query)
        if not is_valid:
            logger.error(f"✗ Invalid query: {error_msg}")
            return self._format_error_result(error_msg)
        
        # Validate top_k
        is_valid, top_k, error_msg = QueryValidator.validate_top_k(top_k)
        if not is_valid:
            logger.error(f"✗ Invalid top_k: {error_msg}")
            top_k = TOP_K_DEFAULT
        
        logger.info(f"✓ Query validation passed")
        logger.info(f"Sanitized query: '{sanitized_query}'")
        
        # Check collection availability
        if self.collection is None:
            error_msg = "Collection not available. Recommender not properly initialized."
            logger.error(f"✗ {error_msg}")
            return self._format_error_result(error_msg)
        
        try:
            # Encode query to embedding
            logger.info("Encoding query to embedding vector...")
            query_embedding = self._encode_query(sanitized_query)
            
            if query_embedding is None:
                error_msg = "Failed to encode query to embedding"
                logger.error(f"✗ {error_msg}")
                return self._format_error_result(error_msg)
            
            logger.info("✓ Query encoded successfully")
            
            # Query ChromaDB for similar documents
            logger.info(f"Searching for top {top_k} similar books...")
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            if not results or not results['ids'] or len(results['ids'][0]) == 0:
                logger.warning("No books found matching the query")
                return self._format_no_results(sanitized_query)
            
            # Format and filter results
            formatted_results = self._format_results(
                results, sanitized_query, top_k
            )
            
            logger.info(f"✓ Found {len(formatted_results)} matching books")
            logger.info("=" * 70)
            
            return formatted_results
            
        except Exception as e:
            error_msg = f"Error during query execution: {str(e)}"
            logger.error(f"✗ {error_msg}")
            logger.error(traceback.format_exc())
            return self._format_error_result(error_msg)
    
    def _format_results(self, results: Dict, query: str, top_k: int) -> List[Dict]:
        """
        Format ChromaDB results into structured book objects.
        
        Args:
            results: Raw results from ChromaDB
            query: Original search query
            top_k: Number of results requested
            
        Returns:
            List of formatted book dictionaries
        """
        formatted = []
        
        ids = results['ids'][0]
        metadatas = results['metadatas'][0]
        documents = results['documents'][0]
        distances = results['distances'][0]
        
        for idx, (book_id, metadata, document, distance) in enumerate(
            zip(ids, metadatas, documents, distances), 1
        ):
            # Convert distance to similarity (chromadb returns distances)
            # For cosine distance: similarity = 1 - distance
            similarity = 1 - distance if distance is not None else 0
            
            # Filter by similarity threshold
            if similarity < SIMILARITY_THRESHOLD:
                logger.warning(
                    f"[{idx}] {book_id} filtered out (similarity: {similarity:.4f} < {SIMILARITY_THRESHOLD})"
                )
                continue
            
            book = {
                "rank": len(formatted) + 1,
                "book_id": book_id,
                "title": metadata.get("title", "Unknown"),
                "author": metadata.get("author", "Unknown"),
                "category": metadata.get("category", "Unknown"),
                "summary": document,
                "similarity_score": round(similarity, 4),
                "match_percentage": round(similarity * 100, 2)
            }
            
            formatted.append(book)
            
            logger.info(
                f"[{book.get('rank')}] {book['title']} - "
                f"Match: {book['match_percentage']}%"
            )
        
        return formatted
    
    def _format_error_result(self, error_message: str) -> List[Dict]:
        """Format error result."""
        return [
            {
                "error": True,
                "message": error_message,
                "status": "failed"
            }
        ]
    
    def _format_no_results(self, query: str) -> List[Dict]:
        """Format no results found response."""
        return [
            {
                "error": False,
                "message": f"No books found matching '{query}'. Try a different query.",
                "status": "no_results",
                "query": query
            }
        ]
    
    def query_interactive(self):
        """Interactive query mode for command-line usage."""
        logger.info("=" * 70)
        logger.info("Welcome to Book Recommender System!")
        logger.info(f"Loaded {self.collection.count()} books in the database")
        logger.info("=" * 70)
        
        while True:
            try:
                print("\n" + "-" * 70)
                user_input = input("What would you like to read about? (or 'quit' to exit): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    logger.info("Thank You for using Book Recommender. Happy reading!")
                    break
                
                # Try to extract top_k from input if provided (format: query --top 10)
                top_k = TOP_K_DEFAULT
                if '--top' in user_input:
                    try:
                        parts = user_input.split('--top')
                        user_input = parts[0].strip()
                        top_k = int(parts[1].strip().split()[0])
                    except (ValueError, IndexError):
                        top_k = TOP_K_DEFAULT
                
                # Get recommendations
                recommendations = self.query(user_input, top_k=top_k)
                
                # Display results
                print("\n" + "=" * 70)
                self._display_results(recommendations)
                print("=" * 70)
                
            except KeyboardInterrupt:
                logger.info("\nThank You for using Book Recommender. Happy reading!")
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                print(f"Error: {str(e)}")
    
    def _display_results(self, recommendations: List[Dict]):
        """Display recommendations in a formatted way."""
        if not recommendations:
            print("No results to display.")
            return
        
        # Check if error response
        if recommendations[0].get("error", False):
            if recommendations[0]["status"] == "failed":
                print(f"❌ Error: {recommendations[0]['message']}")
            else:
                print(f"ℹ️  {recommendations[0]['message']}")
            return
        
        # Display results
        for book in recommendations:
            print(f"\n[{book['rank']}] 📚 {book['title']}")
            print(f"    Author: {book['author']}")
            print(f"    Category: {book['category']}")
            print(f"    Match Score: {book['match_percentage']}% ({book['similarity_score']})")
            print(f"    Summary: {book['summary']}")


def demo_queries():
    """Run demo queries to showcase the recommender."""
    logger.info("Starting Demo Mode")
    logger.info("=" * 70)
    
    try:
        recommender = BookRecommender()
        
        # Demo queries
        demo_queries_list = [
            "machine learning algorithms",
            "web development with Python",
            "database design and optimization",
            "mobile app development",
            "cloud architecture patterns"
        ]
        
        for query in demo_queries_list:
            print("\n" + "=" * 70)
            results = recommender.query(query, top_k=3)
            recommender._display_results(results)
        
        logger.info("=" * 70)
        logger.info("Demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")


if __name__ == "__main__":
    import sys
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--demo":
            # Run demo mode
            demo_queries()
        else:
            # Run interactive mode
            recommender = BookRecommender()
            recommender.query_interactive()
    except Exception as e:
        logger.error(f"Failed to start recommender: {str(e)}")
        logger.error(traceback.format_exc())
