import streamlit as st
import requests
import time



# ---------------- CONFIG ----------------
st.set_page_config(page_title="AcadClarifier", layout="wide")


BACKEND_URL = "http://localhost:5000"


# ---------------- THEME STATE ----------------
if "theme" not in st.session_state:
    st.session_state.theme = "light"

if "page" not in st.session_state:
    st.session_state.page = "home"

if "chat" not in st.session_state:
    st.session_state.chat = []

if "web_chat" not in st.session_state:
    st.session_state.web_chat = []


def apply_theme():
    if st.session_state.theme == "light":
        bg = "#f1f3f6"        # soft light gray
        fg = "#1f2937"        # dark slate text
        card = "#ffffff"     # clean card surface
        border = "#d1d5db"   # subtle border
        desc = "#4b5563"
    else:
         bg = "#0e1117"
         fg = "#f1f1f1"
         card = "#161b22"
         border = "#30363d"
         desc = "#c9d1d9"    

    st.markdown(
        f"""
        <style>
        /* App background */
        .stApp {{
            background-color: {bg};
            color: {fg};
        }}

        /* Card container */
        .card {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 32px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.25);
            text-align: center;
        }}

        /* Card title */
        .card h3 {{
            color: {fg};
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        /* Card description */
        .card p {{
            color: {desc};
            font-size: 15px;
            line-height: 1.6;
        }}

        /* Header title */
        .title {{
            font-size: 30px;
            font-weight: 700;
            letter-spacing: 0.6px;
            color: {fg};
        }}

        /* Buttons */
        .stButton > button {{
            border-radius: 10px;
            padding: 0.75em 1em;
            font-weight: 500;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )










apply_theme()

st.divider()


# ---------------- HEADER ----------------
def render_header():
    col1, col2, col3 = st.columns([6, 1, 1])

    with col1:
        st.markdown("<div class='title'>AcadClarifier</div>", unsafe_allow_html=True)

    with col2:
        if st.button("Admin", key="admin_btn"):
            st.session_state.page = "admin"
            st.rerun()

    with col3:
        if st.button("Dark / Light", key="theme_toggle_btn"):
            st.session_state.theme = (
                "dark" if st.session_state.theme == "light" else "light"
            )
            st.rerun()


render_header()

# ---------------- HOME PAGE ----------------
def home_page():
    st.write("")
    st.markdown(
        "<h2 style='text-align:center;'>Select Retrieval Mode</h2>",
        unsafe_allow_html=True
    )
    st.write("")

    col1, col2 = st.columns(2)

    # -------- Cards --------
    with col1:
        st.markdown(
            """
            <div class="card">
                <h3>Book Retrieval</h3>
                <p>Query academic content from scanned textbooks using RFID and local vector search.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Start Book Mode", use_container_width=True):
            st.session_state.page = "book"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div class="card">
                <h3>Real-time Retrieval</h3>
                <p>Query academic knowledge from live internet sources when local data is insufficient.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Start Web Mode", use_container_width=True):
            st.session_state.page = "web"
            st.rerun()

    # -------- About Section --------
        
    st.write("")
    st.divider()
    st.write("")

    with st.expander("📘 About AcadClarifier", expanded=False):
        st.markdown(
            """
            **AcadClarifier** is an RFID-based academic question answering system designed for
            modern library environments.

            ### 🔍 How it works
            - Students scan a textbook using an RFID tag.
            - The system identifies the book and searches its contents using a vector database.
            - If a confident answer is not found locally, the system retrieves real-time information
              from the internet.
            - Final answers are simplified and presented in an easy-to-understand format.

            ### 🧠 Technologies Used
            - **Edge AI** on Raspberry Pi
            - **Vector Database (ChromaDB)** for semantic search
            - **Retrieval-Augmented Generation (RAG)**
            - **RFID-based IoT integration**
            - **Hybrid Local + Cloud AI architecture**

            ### 🎓 Academic Relevance
            This project demonstrates the practical implementation of modern AI systems in
            real-world educational settings by combining IoT, NLP, vector databases, and
            edge computing.
            """
        

    )


# ---------------- BOOK PAGE (PLACEHOLDER) ----------------
def book_page():

    top_col1, top_col2 = st.columns([8, 1])

    with top_col2:
        if st.button("⬅ Back", key="book_back_btn"):
            st.session_state.chat = []
            st.session_state.page = "home"
            st.rerun()

    st.subheader("📗 Book Retrieval")

    # -------- Fetch Active Book --------
    try:
        res = requests.get(f"{BACKEND_URL}/session", timeout=2).json()
        book_uid = res.get("active_book")
    except Exception:
        st.error("Backend not reachable")
        book_uid = None

    # -------- No Book Yet --------
    if not book_uid:
        st.warning("📡 Please scan a book to begin...")
        st.caption("Waiting for RFID scan...")
        time.sleep(2)
        st.rerun()
        return

    # -------- Book Found --------
    st.success("✅ Book Scanned")
    st.info(f"Scanned Book UID: {book_uid}")

    st.divider()

    # -------- Chat History --------
    for role, msg in st.session_state.chat:
        if role == "user":
            st.chat_message("user").write(msg)
        else:
            st.chat_message("assistant").write(msg)

    # -------- Input Box --------
    question = st.chat_input("Ask a question about this book...")

    if question:
        # show user message
        st.session_state.chat.append(("user", question))

        try:
            response = requests.post(
                f"{BACKEND_URL}/ask",
                json={"question": question},
                timeout=10
            ).json()

            answer = response.get("answer", "No answer")
            confidence = response.get("confidence", 0)

            final_answer = f"{answer}\n\nConfidence: {confidence}"

        except Exception:
            final_answer = "Backend error while answering."

        st.session_state.chat.append(("bot", final_answer))
        st.rerun()

    if st.button("⬅ Back"):
        st.session_state.chat = []
        st.session_state.page = "home"
        st.rerun()


def admin_page():
    st.subheader("👨‍💼 System Administrator")
    st.info("Admin dashboard will be added here.")
    st.write("Future features:")
    st.write("- Logs viewer")
    st.write("- Book database manager")
    st.write("- System settings")

    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()




# ---------------- WEB PAGE (PLACEHOLDER) ----------------
def web_page():
    st.subheader("🌐 Real-time Retrieval")
    st.caption("Ask any academic question")

    st.divider()

    # -------- Chat History --------
    for role, msg in st.session_state.web_chat:
        if role == "user":
            st.chat_message("user").write(msg)
        else:
            st.chat_message("assistant").write(msg)

    # -------- Input --------
    question = st.chat_input("Ask your question...")

    if question:
        st.session_state.web_chat.append(("user", question))

        try:
            response = requests.post(
                f"{BACKEND_URL}/ask",
                json={"question": question},
                timeout=15
            ).json()

            answer = response.get("answer", "No answer")
            confidence = response.get("confidence", 0)

            final_answer = f"{answer}\n\nConfidence: {confidence}"

        except Exception:
            final_answer = "Backend error while answering."

        st.session_state.web_chat.append(("bot", final_answer))
        st.rerun()

    if st.button("⬅ Back"):
        st.session_state.web_chat = []
        st.session_state.page = "home"
        st.rerun()



def render_footer():
    st.markdown(
        """
        <hr style="margin-top:40px;margin-bottom:10px;">
        <div style="text-align:center; font-size:13px; color:gray;">
            AcadClarifier — RFID-Based Academic Question Answering System<br>
            Academic Project | Edge AI • RAG • IoT • Vector Databases
        </div>
        """,
        unsafe_allow_html=True
    )


# ---------------- MAIN RENDER ----------------


if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "book":
    book_page()
elif st.session_state.page == "web":
   web_page()
elif st.session_state.page == "admin":
    admin_page()

render_footer()