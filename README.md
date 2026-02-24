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
- Streamlit-based kiosk UI
- Light / Dark mode
- Modular architecture for local and web retrieval pipelines

---

## Tech Stack

- Python 3.10+
- Streamlit (Frontend UI)
- Flask (Backend API)
- Requests (Frontend ↔ Backend communication)
- ChromaDB / vector pipeline scripts (local retrieval)
- Tavily pipeline scripts (web retrieval)

---

## Project Structure

```text
AcadClarifier/
├── app.py                            # Compatibility frontend entrypoint
├── backend/
│   └── server.py                     # Compatibility backend entrypoint
├── apps/
│   ├── frontend/
│   │   └── app.py                    # Main Streamlit app
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
python apps/backend/server.py
```

Legacy-compatible (still supported):

```bash
python backend/server.py
```

Backend URL: http://localhost:5000

### 4) Start frontend (Terminal 2)

Recommended:

```bash
python -m streamlit run apps/frontend/app.py
```

Legacy-compatible (still supported):

```bash
python -m streamlit run app.py
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
