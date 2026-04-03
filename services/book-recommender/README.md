# Book Recommender System

A semantic-based book recommendation engine that uses ChromaDB and sentence embeddings to suggest books based on user queries.

## Overview

This project implements an intelligent book recommendation system that leverages modern NLP techniques to understand user queries and find the most relevant books from a database. Instead of simple keyword matching, it uses semantic similarity to understand the meaning behind search queries.

## Features

- **Semantic Search**: Uses sentence-transformers for understanding query meaning, not just keywords
- **Vector Database**: ChromaDB for efficient similarity search on book embeddings
- **Comprehensive Validation**: Input validation for queries and parameters
- **Interactive Mode**: Command-line interface for exploring book recommendations
- **Demo Mode**: Pre-configured demo queries to showcase functionality
- **Logging**: Detailed logging for debugging and monitoring
- **Error Handling**: Robust error handling and user-friendly error messages

## Project Structure

```
Book Recommender/
├── create_library_db.py      # Initialize SQLite database schema
├── insert_data.py            # Populate database with book data
├── sql_to_chromadb.py        # Convert SQL data to ChromaDB embeddings
├── user_library_query.py     # Main recommender interface
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── chroma_data/              # ChromaDB persistent storage
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone/Copy the project** to your desired location

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Initialize the database**:
```bash
python create_library_db.py
```

4. **Insert book data**:
```bash
python insert_data.py
```

5. **Generate embeddings** (converts SQL data to ChromaDB):
```bash
python sql_to_chromadb.py
```

## Usage

### Interactive Mode (Default)
Start the book recommender in interactive mode:
```bash
python user_library_query.py
```

Then enter your search queries:
```
What would you like to read about? machine learning
```

**Advanced query syntax**: Specify the number of results with `--top`:
```
What would you like to read about? web development --top 10
```

### Demo Mode
Run pre-configured demo queries:
```bash
python user_library_query.py --demo
```

## How It Works

### 1. Database Setup
- [create_library_db.py](create_library_db.py) creates the SQLite schema with book metadata
- [insert_data.py](insert_data.py) populates the database with book records

### 2. Embedding Generation
- [sql_to_chromadb.py](sql_to_chromadb.py) reads books from SQLite
- Generates embeddings using the "all-MiniLM-L6-v2" sentence-transformer model
- Stores embeddings in ChromaDB for fast similarity search

### 3. Query Processing
- [user_library_query.py](user_library_query.py) handles user queries:
  - **Validation**: Ensures query is appropriate length and contains valid characters
  - **Encoding**: Converts query to embedding vector
  - **Similarity Search**: Finds top-k most similar books using cosine distance
  - **Filtering**: Removes results below similarity threshold (30%)
  - **Formatting**: Returns results with match percentages and book details

## Configuration

Key parameters in [user_library_query.py](user_library_query.py):

| Parameter | Value | Description |
|-----------|-------|-------------|
| `MIN_QUERY_LENGTH` | 3 | Minimum characters in query |
| `MAX_QUERY_LENGTH` | 500 | Maximum characters in query |
| `TOP_K_DEFAULT` | 5 | Default number of results |
| `SIMILARITY_THRESHOLD` | 0.3 | Minimum similarity score (0-1) |

## Example Output

```
[1] 📚 Machine Learning Fundamentals
    Author: John Smith
    Category: Artificial Intelligence
    Match Score: 89.23% (0.8923)
    Summary: A comprehensive guide to machine learning concepts...

[2] 📚 Deep Learning Advanced Topics
    Author: Jane Doe
    Category: Artificial Intelligence
    Match Score: 85.67% (0.8567)
    Summary: Explores advanced deep learning techniques and applications...
```

## Classes and Functions

### `QueryValidator`
Validates and sanitizes user input queries.
- `validate_query(query)`: Checks query validity and length
- `validate_top_k(top_k)`: Ensures top_k parameter is valid

### `BookRecommender`
Main recommendation engine.
- `query(user_query, top_k)`: Get book recommendations for a query
- `query_interactive()`: Start interactive mode
- `_display_results(recommendations)`: Format and display results

## Dependencies

- **chromadb**: Vector database for storing and searching embeddings
- **sentence-transformers**: Pre-trained models for semantic text embeddings
- **torch**: Required by sentence-transformers for deep learning operations

## Troubleshooting

### "ChromaDB directory not found"
Run `python sql_to_chromadb.py` to generate embeddings.

### "Books collection is empty"
Ensure `python insert_data.py` has been run to populate the database.

### "Failed to load embedding model"
The model requires internet connection for first download. Ensure connectivity.

### Slow first query
The sentence-transformer model is loaded on first use (~300MB). Subsequent queries are faster.

## Performance Considerations

- **First Query**: ~2-3 seconds (model loading + embedding)
- **Subsequent Queries**: ~0.5-1 second (embedding + search)
- **Memory Usage**: ~500MB (model + ChromaDB)
- **Search Time**: O(n) for the embedding, then approximate nearest neighbor search

## Future Enhancements

- User preference learning
- Collaborative filtering
- Advanced filtering by category, author, year
- Result ranking by popularity
- REST API interface
- Web UI dashboard

## License

Not Licensed

## Contributing

Feel free to contribute 

## Support

For issues or questions, please refer to the inline code documentation or check the logging output for detailed error information.
