# AcadClarifier - Comprehensive Project Summary

## Project Overview

**AcadClarifier** is an intelligent academic learning assistant that simplifies and enhances academic content from multiple sources. It combines local book libraries with web retrieval and journal databases to provide comprehensive, simplified answers to user queries through a Retrieval-Augmented Generation (RAG) pipeline powered by Gemini API.

**Primary Goal**: Transform raw academic data into comprehensive, simplified, and detailed academic guides suitable for students.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND APPLICATION                        │
│                  (HTML/CSS/JS Web Interface)                     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
        ┌───────────▼──────────┐  ┌──────────▼──────────┐
        │   BACKEND SERVER     │  │   ROUTE HANDLER     │
        │   (Flask/Python)     │  │   (APIs & Business  │
        └───────────┬──────────┘  │    Logic)           │
                    │             └─────────┬───────────┘
                    │                       │
        ┌───────────▼───────────────────────▼──────────────┐
        │          DATABASE LAYER                         │
        │  - PostgreSQL (Books, Metadata)                 │
        │  - Session Management                          │
        │  - User Preferences                            │
        └───────────┬───────────────────────────────────┬─┘
                    │                                   │
        ┌───────────▼──────────┐         ┌──────────────▼──────────┐
        │  RAG PIPELINES       │         │  VECTOR DATABASES       │
        │                      │         │  (ChromaDB)             │
        │ 1. Local Books       │         │                         │
        │ 2. Journal Papers    │         │ - Book Embeddings       │
        │ 3. Web Retrieval     │         │ - Query Embeddings      │
        │                      │         │ - Vector Similarity     │
        └───────────┬──────────┘         └──────────────┬──────────┘
                    │                                   │
                    └───────────────┬───────────────────┘
                                    │
                        ┌───────────▼──────────┐
                        │   GEMINI API         │
                        │   (Simplification &  │
                        │    Enhancement)      │
                        └──────────────────────┘
```

---

## Core Components & Functionalities

### 1. **Frontend Application** (`apps/frontend/`)

**Technology**: HTML5, CSS3, Vanilla JavaScript
**Location**: `apps/frontend/`

**Features Implemented**:
- **Responsive UI**: Multi-page SPA using custom router
- **Navigation**: Navbar with service switching
- **Page Components**:
  - `home.html` - Welcome & intro
  - `local.html` - Local book retrieval interface
  - `web.html` - Web-based retrieval UI
  - `journal_rec.html` - Journal paper recommendations
  - `book_rec.html` - Book recommendations from library

**CSS Modules**:
- `styles.css` - Global styles
- `local.css` - Local retrieval styling
- `web.css` - Web retrieval styling
- `journal_rec.css` - Journal recommendations
- `book_rec.css` - Book recommendations
- `home.css` - Homepage styling

**JavaScript Modules**:
- `app.js` - Main app initialization
- `router.js` - Client-side routing
- `api.js` - API communication layer
- `state.js` - Application state management
- `components/` - Reusable UI components (modals, loaders, navbar)

---

### 2. **Backend Server** (`apps/backend/`)

**Technology**: Python, Flask
**Location**: `apps/backend/`

**Database Layer** (`db.py`):
- PostgreSQL integration with SQLAlchemy
- Session management
- Book metadata storage

**Models** (`models/`):
- `book.py` - Book entity with attributes (title, author, ISBN, etc.)

**Repositories** (`repositories/`):
- `book_repository.py` - Data access layer for books
- Database abstraction for CRUD operations

**API Routes** (`routes.py`):
- GET `/api/books` - Retrieve all books
- GET `/api/books/<id>` - Get specific book
- POST `/api/books` - Add book to library
- GET `/api/query/local` - Query local embeddings
- GET `/api/query/web` - Web retrieval
- GET `/api/recommendations/books` - Book recommendations
- GET `/api/recommendations/journal` - Journal recommendations

**Client Integrations**:
- `ml_client.py` - Machine learning service interactions
- `web_pipeline.py` - Web retrieval pipeline
- `journal_client.py` - Journal database connections
- `recommend_client.py` - Recommendation engine

**Server Configuration** (`server.py`, `config.py`, `session.py`):
- Server initialization and routing
- Configuration management (env vars, API keys)
- Session handling and authentication

**Seed Data** (`seeds/`):
- `seed_books.py` - Initial book library data population

---

### 3. **Local RAG Pipeline** (`services/retrieval-local/`)

**Complete workflow for local book retrieval with vector embeddings**

#### **Stage 1: PDF to Text Conversion**
**Script**: `pdf_to_text.py`

**Functionality**:
- Scans `data/` folder for PDF files
- Interactive user selection of books
- Extracts text from all pages using PyPDF2
- Saves as `cleaned_book-X.txt` in `outputs/pdf_to_text_output/`
- Loop-based processing for multiple books

**Key Features**:
- Automatic folder path detection
- Batch processing until user selects exit (0)
- Output: Text files with complete content

---

#### **Stage 2: Text Cleaning**
**Script**: `cleaning_text.py`

**Functionality**:
- Reads from `pdf_to_text_output/` folder
- Removes extraction artifacts and corrupted characters
- Normalizes whitespace and formatting
- Cleans punctuation spacing
- Saves cleaned text to `cleaned_text_output/`

**Cleaning Operations**:
- Remove control characters (extraction errors)
- Multiple newline normalization
- Tab and space consolidation
- Leading/trailing whitespace removal
- Special character removal

**Output Format**: `cleaned_book-X.txt`

---

#### **Stage 3: Text Chunking**
**Script**: `text_to_chunks.py`

**Functionality**:
- Reads from `cleaned_text_output/`
- Splits text into semantic chunks using RecursiveCharacterTextSplitter
- Preserves context with chunk overlap

**Chunking Parameters**:
- `chunk_size`: 480 characters
- `chunk_overlap`: 100 characters
- `separators`: ["\n\n", "\n", ". ", " ", ""]

**Chunk Metadata**:
- `chunk_id`: Sequential identifier
- `text`: Content
- `length`: Character count
- `word_count`: Words in chunk
- `char_count`: Characters in chunk

**Output Format**: `book-X_chunks.json` (JSON with chunk metadata)

---

#### **Stage 4: Vector Embeddings Generation**
**Script**: `chunks_to_vectors.py`

**Functionality**:
- Reads from `chunking_output/`
- Converts text chunks to vector embeddings
- Stores in ChromaDB for semantic search

**Embedding Model**:
- `BAAI/bge-base-en-v1.5` (HuggingFace)
- Normalized embeddings for cosine similarity
- Bidirectional Encoder Representations from Transformers

**ChromaDB Storage**:
- Separate collection per book (`book-1/`, `book-2/`, etc.)
- Persistent storage with SQLite backend
- Cosine distance metric for similarity search
- Batch processing (5000 embeddings per batch) to handle large datasets

**Output Structure**:
```
embeddings_output/
├── book-1/
│   ├── chroma.sqlite3
│   └── [UUIDs]/
├── book-2/
└── ...
```

---

#### **Stage 5: User Query Processing**
**Script**: `user_query.py`

**Functionality**:
- Displays available books with full metadata
- Interactive book selection
- Accepts user queries
- Embeds queries using same model as chunks
- Performs cosine similarity search
- Retrieves top-5 most relevant chunks

**Book Information**:
```
1. book-1 : Database System Concepts Sixth Edition - Abraham Silberschatz
2. book-2 : Hadoop in Action - Chuck Lam
... (all 10 books with titles and authors)
```

**Query Flow**:
1. Discover all books from embeddings_output
2. Display numbered list sorted numerically (book-1, book-2, ..., book-10)
3. User selects book number
4. Accept query with minimum 3 characters
5. Load SentenceTransformer model
6. Connect to selected book's ChromaDB
7. Embed query with BGE prefix: "Represent this sentence for searching relevant passages: "
8. Query collection for top 5 results

**Similarity Threshold**: 0.3 (30% cosine similarity minimum)

**Output Structure** (`query_output/`):
```json
{
  "query_id": "query_1775545199_84b456e3",
  "timestamp": "2026-04-07T...",
  "query": "user's question",
  "book": "book-1",
  "results": [
    {
      "rank": 1,
      "chunk_id": "123",
      "similarity_score": 0.8542,
      "document": "relevant chunk text"
    }
  ],
  "summary": {
    "total_results": 5,
    "top_similarity_score": 0.8542,
    "threshold_used": 0.3,
    "model_used": "BAAI/bge-base-en-v1.5"
  }
}
```

**Features**:
- Unique query IDs for tracking
- Multiple query support (loop until exit)
- Comprehensive logging
- Edge case handling
- Deployment-ready error management

---

#### **Stage 6: Simplification & Enhancement**
**Script**: `local_simplifier.py`

**Functionality**:
- Automated batch processing of all queries
- Converts raw retrieved content to simplified academic guides
- Integrates with Gemini API for LLM-powered enhancement

**Processing Flow**:
1. Discover all query JSON files in `query_output/`
2. For each query file:
   - Load query metadata and retrieved chunks
   - Extract context from top results
   - Build comprehensive prompt for Gemini
   - Generate simplified academic explanation
   - Save output with query metadata

**Gemini Integration**:
- **Model**: `gemini-2.5-flash`
- **API Key**: From `.env` file (python-dotenv)
- **Temperature**: 0.3 (focused, deterministic)
- **Max Output Tokens**: 8000 (comprehensive responses without cutoff)

**Output Format**:
```
QUERY ID: query_1775545199_84b456e3
BOOK: book-1
ORIGINAL QUERY: user's question
================================================================================

# [Title from Gemini]

### Overview
[2-3 line summary]

### Key Concepts
[Bullet points of main terms]

### Detailed Academic Explanation
[Multi-paragraph, 300+ word detailed explanation]
```

**Features**:
- Fully automated batch processing
- Batch summary statistics (processed, successful, failed)
- Comprehensive error handling
- Metadata preservation in output
- Deployment-ready with logging

---

### 4. **Journal Retrieval Pipeline** (`services/retrieval-journal/`)

**Current Status**: Implemented structure (main.py, services.py, vector_store.py)

**Intended Functionality**:
- Query academic journals and papers
- Semantic search through journal databases
- Vector storage for journal documents
- Integration with main backend

---

### 5. **Web Retrieval Pipeline** (`services/retrieval-web/`)

**Technology**: Web scraping, vector processing, reranking

**Modules**:
- `tavily_fetch.py` - Web content fetching using Tavily API
- `chunking.py` - Document chunking for web content
- `embeddings.py` - Vector embeddings for web results
- `filtering.py` - Content filtering and validation
- `reranking.py` - Rerank search results by relevance
- `compression_v2.py` & `compression-v2.py` - Content compression
- `simplifier.py` - Web content simplification
- `pipeline.py` - Orchestration of entire pipeline

**Outputs**:
- `chunking_outputs/` - Chunked web content
- `embeddings_outputs/` - Generated embeddings
- `rerank_outputs/` - Reranked results
- `final_context_outputs/` - Final compressed context
- `final_output/` - Simplified web results

---

### 6. **Book Recommender Service** (`services/book-recommender/`)

**Functionality**:
- Recommends books from local library based on query
- Uses ChromaDB for similarity matching
- Metadata-driven recommendations

**Components**:
- `create_library_db.py` - Initialize book database
- `insert_data.py` - Populate library
- `sql_to_chromadb.py` - Convert library to vector database
- `user_library_query.py` - Query recommendations

**Data Storage**:
- `chroma_data/` - ChromaDB persistent storage

---

## Data Flow Architecture

### Local Retrieval Flow:
```
PDF Files (data/)
    ↓
[pdf_to_text.py]
    ↓
Text Files (pdf_to_text_output/)
    ↓
[cleaning_text.py]
    ↓
Cleaned Text (cleaned_text_output/)
    ↓
[text_to_chunks.py]
    ↓
JSON Chunks (chunking_output/)
    ↓
[chunks_to_vectors.py]
    ↓
ChromaDB Embeddings (embeddings_output/book-X/)
    ↓
User Query via Frontend
    ↓
[user_query.py] - Semantic Search
    ↓
Retrieved Results (query_output/)
    ↓
[local_simplifier.py] + Gemini API
    ↓
Simplified Output (final_output/)
    ↓
Display to User via Frontend
```

---

## Technologies & Libraries

### Backend & Processing:
- **Python 3.x** - Core language
- **Flask** - Web framework
- **SQLAlchemy** - ORM for database
- **PostgreSQL** - Primary database
- **Alembic** - Database migrations

### Machine Learning & NLP:
- **SentenceTransformers** - Embedding model (BAAI/bge-base-en-v1.5)
- **LangChain** - Text splitting and text processing
- **ChromaDB** - Vector database with persistent storage
- **NumPy** - Numerical computations

### API Integrations:
- **Google Generative AI (Gemini)** - LLM for content simplification
- **Tavily API** - Web search and content retrieval

### Frontend:
- **HTML5** - Markup
- **CSS3** - Styling with responsive design
- **Vanilla JavaScript** - Client-side logic
- **Custom Router** - SPA routing

### Utilities:
- **PyPDF2** - PDF text extraction
- **python-dotenv** - Environment variable management
- **Logging** - Comprehensive application logging

---

## Database Schema

### Books Table:
```sql
CREATE TABLE books (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  author VARCHAR(255),
  isbn VARCHAR(20) UNIQUE,
  description TEXT,
  category VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Session Management:
- User session tokens
- Query history tracking
- User preferences

---

## Configuration & Environment

### Environment Variables (`.env`):
```
GEMINI_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/acadclarifier
FLASK_ENV=production
TAVILY_API_KEY=your_tavily_key
```

---

## Key Features Summary

### ✅ Implemented Features:

1. **Local Book Processing Pipeline**
   - PDF to text conversion
   - Text cleaning and normalization
   - Semantic chunking
   - Vector embedding generation
   - ChromaDB storage (per-book isolation)

2. **Query Processing**
   - Interactive book selection
   - Natural language query acceptance
   - Semantic similarity search
   - Top-K result retrieval (k=5)

3. **Content Simplification**
   - Gemini API integration
   - Batch processing of queries
   - Academic content generation
   - Metadata preservation

4. **Frontend Interface**
   - Multi-page SPA
   - Service switching (local/web/journal)
   - Query input UI
   - Results display

5. **Error Handling & Validation**
   - Comprehensive edge case handling
   - Detailed logging throughout
   - Graceful failure management
   - Input validation

### 🔄 Workflow States:

1. **Development & Testing**
   - Process PDFs locally
   - Generate embeddings
   - Test queries

2. **Production Ready**
   - All scripts deployment-ready
   - Environment-aware configuration
   - Persistent storage handling
   - API key management

---

## Deployment Considerations

### Current Deployment Path:
- **Target**: Render.com
- **Storage**: Render persistent disk for embeddings (`/data/embeddings`)
- **Database**: PostgreSQL (Render or external)
- **APIs**: Gemini (Google Cloud), Tavily (Web search)

### Recommended Stack:
```
Render (Web hosting) + 
PostgreSQL (Database) + 
Render Disk (5GB for embeddings) + 
Google Gemini API + 
S3 Backup (optional)
```

---

## Usage Instructions

### Local Development Workflow:

1. **Process Books**
   ```bash
   python services/retrieval-local/scripts/pdf_to_text.py
   python services/retrieval-local/scripts/cleaning_text.py
   python services/retrieval-local/scripts/text_to_chunks.py
   python services/retrieval-local/scripts/chunks_to_vectors.py
   ```

2. **Query Books**
   ```bash
   python services/retrieval-local/scripts/user_query.py
   ```

3. **Simplify Results**
   ```bash
   python services/retrieval-local/scripts/local_simplifier.py
   ```

4. **Start Backend**
   ```bash
   python apps/backend/server.py
   ```

5. **Access Frontend**
   - Open browser to `http://localhost:5000`

---

## Project Status

- ✅ **Local retrieval pipeline**: Fully functional
- ✅ **Vector embeddings**: Implemented with ChromaDB
- ✅ **Query processing**: Complete with ranking
- ✅ **Content simplification**: Batch processing with Gemini
- ✅ **Frontend interface**: Multi-page SPA
- ✅ **Backend API**: Route handlers implemented
- 🔄 **Web retrieval**: Modular structure in place
- 🔄 **Journal retrieval**: Foundation ready
- 🔄 **Book recommendations**: Service layer ready
- ⏳ **Deployment**: Ready for Render with disk configuration

---

## Architecture Highlights

1. **Modular Design**: Each processing stage is independent and scriptable
2. **Persistent Vector Storage**: Per-book ChromaDB isolation for scalability
3. **Reusable Components**: Services can be called independently
4. **Error Resilience**: Comprehensive error handling and logging
5. **Cloud-Ready**: Environment detection and path management
6. **Batch Processing**: Automated processing without manual intervention
7. **API Integration**: Seamless Gemini API integration for enhancement

---

## Notes for LLM Context

This project implements a **multi-stage RAG (Retrieval-Augmented Generation) system** with:
- Local knowledge base built from academic books
- Vector similarity-based retrieval
- LLM-powered content simplification
- Extensible to web and journal sources

The system is designed for **educational use**, helping students understand complex academic concepts through simplified, detailed explanations generated from authoritative sources.
