# AcadClarifier

BE Project - AcadClarifier

AcadClarifier is an RFID-based academic question answering system designed for library environments.  
It combines Edge AI, Vector Databases, and Retrieval-Augmented Generation (RAG) to help students
ask academic questions from textbooks or real-time internet sources.

> ⚠️ Note  
> Hardware components (RFID reader, Raspberry Pi) are mocked in this version.  
> This repository focuses on software architecture, backend logic, and frontend UI.

---

## Features

- Book-based academic question answering (via RFID session)
- Real-time academic question answering
- Flask-based backend controller
- Pure HTML/CSS/JavaScript frontend (no framework)
- Light / Dark mode
- Modular architecture for local and web retrieval pipelines

---

## Tech Stack

- Python 3.10+
- Vanilla HTML/CSS/JavaScript (Frontend UI)
- Flask (Backend API)
- Requests (Frontend ↔ Backend communication)
- ChromaDB / vector pipeline scripts (local retrieval)
- Tavily pipeline scripts (web retrieval)

---

## Project Structure

```text
AcadClarifier/
├── app.py                            # Static frontend server entrypoint
├── backend/
│   └── server.py                     # Compatibility backend entrypoint
├── apps/
│   ├── frontend/
│   │   ├── index.html
│   │   ├── pages/
│   │   ├── css/
│   │   ├── js/
│   │   └── components/
│   └── backend/
│       ├── server.py                 # Main Flask app
│       ├── routes.py
│       ├── session.py
│       └── ml_client.py
├── services/
│   ├── retrieval-local/              # Previously to-vector/
│   │   ├── src/
│   │   ├── chroma_store/
│   │   ├── data/
│   │   ├── outputs/
│   │   └── vectors/
│   └── retrieval-web/                # Previously web-retrieval/tavily/
│       ├── scripts/
│       └── outputs/
├── data/                             # Reserved for shared runtime artifacts
├── requirements.txt
└── README.md
```

---

## Run the Project

### 1) Create and activate virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Start backend (Terminal 1)

Recommended:

```bash
python -m apps.backend.server
```

Backend URL: http://localhost:5000

### 4) Start frontend (Terminal 2)

Recommended:

```bash
python app.py
```

Frontend URL: http://localhost:8501

---

## Mocking Book Scan (No Hardware Required)

```bash
curl -X POST http://localhost:5000/rfid/update \
     -H "Content-Type: application/json" \
     -d '{"uid":"BOOK_001"}'
```

---

## Web Retrieval Notes

Current script order:

1. `tavily_fetch.py`
2. `filtering-full.py`
3. `chunking.py`
4. `embeddings.py`
5. `reranking.py`
6. `compression_v2.py`

---

## Library API (Phase 2)

### GET `/library`

Returns a paginated list of books from PostgreSQL.

Query params:

- `q` (optional): search by title, author, ISBN, or topic
- `page` (optional, default `1`)
- `page_size` (optional, default `20`, max `100`)

Example response:

```json
{
  "items": [
    {
      "id": 1,
      "uid": "book-dbms-001",
      "title": "Database System Concepts",
      "author": "Abraham Silberschatz",
      "isbn": "9780073523323",
      "topic": "DBMS",
      "description": "...",
      "coverImageUrl": null,
      "publishedYear": 2010
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

### GET `/library/<book_ref>`

Returns one book by `uid` (preferred) or numeric `id`.

Success response:

```json
{
  "id": 1,
  "uid": "book-dbms-001",
  "title": "Database System Concepts",
  "author": "Abraham Silberschatz",
  "isbn": "9780073523323",
  "topic": "DBMS",
  "description": "...",
  "coverImageUrl": null,
  "publishedYear": 2010
}
```

Not found response (`404`):

```json
{
  "error": "Book not found",
  "book_ref": "unknown"
}
```

### POST `/recommend`

Returns semantic book recommendations from the ChromaDB-backed recommender.

Request body:

- `question` (required): learning goal or topic description
- `top_k` (optional, default `5`): number of recommendations

Example request:

```json
{
  "question": "I want to learn machine learning from basics to practical implementation",
  "top_k": 5
}
```

### POST `/journal/recommend`

Returns journal and paper recommendations processed in the main backend.

Request body:

- `query` or `question` (required): research topic
- `top_k` (optional, default `10`, max `20`)
- `filter_type` (optional): `all`, `open_access`, or `subscription`

Example request:

```json
{
  "query": "Latest breakthroughs in sustainable battery technologies for long-range EVs",
  "top_k": 10,
  "filter_type": "all"
}
```

Example response:

```json
{
  "status": "ok",
  "query": "Latest breakthroughs in sustainable battery technologies for long-range EVs",
  "items": [
    {
      "rank": 1,
      "title": "Advanced Cathode Materials for Next-Gen Lithium-Sulfur Batteries",
      "doi": "10.xxxx/xxxx",
      "year": 2023,
      "abstract": "...",
      "summary": "...",
      "citations": 152,
      "publisher": "Nature Energy",
      "is_oa": true,
      "pdf": "https://...",
      "similarity_score": 1.0,
      "match_percentage": 100.0
    }
  ],
  "total": 1,
  "message": "Journal recommendations fetched successfully"
}
```

---
