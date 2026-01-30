
# Acadclarifier

BE Project - Acadclarifier

## Web-retrieval Notes

### Order of scripts

1. tavily_fetch.py
2. filtering-full.py
3. chunking.py
4. embeddings.py
5. reranking.py
6.

# 📚 AcadClarifier

AcadClarifier is an RFID-based academic question answering system designed for library environments.  
It combines **Edge AI**, **Vector Databases**, and **Retrieval-Augmented Generation (RAG)** to help students
ask academic questions from textbooks or real-time internet sources.

> ⚠️ **Note**  
> Hardware components (RFID reader, Raspberry Pi) are **mocked** in this version.  
> This repository focuses on **software architecture, backend logic, and frontend UI**.

---

## 🎯 Features

- 📗 Book-based academic question answering (via RFID session)
- 🌐 Real-time academic question answering
- 🧠 Flask-based backend controller
- 🖥 Streamlit-based kiosk UI
- 🌙 Light / Dark mode
- 📦 Modular, ML-ready architecture

---

## 🛠 Tech Stack

- **Python 3.10**
- **Streamlit** – Frontend UI
- **Flask** – Backend API
- **SQLite** – Session & logs (future use)
- **Requests** – Backend ↔ Frontend communication

---

## 📁 Project Structure

AcadClarifier/
│
├── app.py # Streamlit frontend
├── backend/ # Flask backend
│ ├── server.py
│ ├── routes.py
│ ├── session.py
│ └── ml_client.py # Mock ML responses
│
├── requirements.txt
├── README.md
└── .gitignore



---

## 🚀 How to Run the Project (Step-by-Step)

### 1️⃣ Prerequisites

- Python **3.10**
- Git
- Internet connection

Check Python version:

```bash
python --version


2️⃣ Clone the Repository

git clone https://github.com/<your-username>/AcadClarifier.git
cd AcadClarifier


3️⃣ Create a Virtual Environment

python -m venv venv


Activate the virtual environment

Windows (Git Bash):

source venv/Scripts/activate


Windows (PowerShell):

venv\Scripts\Activate.ps1


Linux / macOS:

source venv/bin/activate


You should see (venv) in the terminal.


4️⃣ Install Dependencies

pip install -r requirements.txt


5️⃣ Run the Backend (Flask)


Open Terminal 1:

cd backend
python server.py


Backend runs at:

http://localhost:5000


6️⃣ Run the Frontend (Streamlit)

Open Terminal 2 (keep backend running):

cd AcadClarifier
python -m streamlit run app.py


Frontend runs at:

http://localhost:8501


🔁 Mocking Book Scan (No Hardware Required)

To simulate an RFID book scan:

curl -X POST http://localhost:5000/rfid/update \
     -H "Content-Type: application/json" \
     -d '{"uid":"BOOK_001"}'


The UI will update automatically.


🧠 System Modes
📗 Book Retrieval Mode

Requires a scanned book (mocked RFID)

Questions are answered from book context (mock ML)

🌐 Real-time Retrieval Mode

No book required

Designed for internet-based academic QA



🎓 Academic Context

This project demonstrates practical implementation of:

Edge AI deployment concepts

Vector database–based semantic search

Retrieval-Augmented Generation (RAG)

IoT integration using RFID

Hybrid local + cloud AI architecture

