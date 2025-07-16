import sys, types, os, zipfile, shutil, logging
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from utils import load_and_split_code, create_or_load_index, get_llm_response

# --- Logging ---
logging.getLogger("tornado.application").setLevel(logging.ERROR)

# --- Fix for torch.classes error in Streamlit ---
sys.modules["torch.classes"] = types.SimpleNamespace(__path__=[])

# --- Load .env Variables ---
load_dotenv()

# --- Streamlit Page Config ---
st.set_page_config(page_title="Code Assistant", page_icon="🧠", layout="wide")
st.markdown("<h1 style='text-align:center;'>🧠 Welcome to Coding-AssistAnt</h1>", unsafe_allow_html=True)

# --- Session State Initialization ---
for key in ["index_created", "db", "uploaded", "processed_docs", "db_map", "current_file"]:
    if key not in st.session_state:
        st.session_state[key] = {} if key == "db_map" else None

# --- Sidebar ---
logo_path = Path("static/coding assistant icon.jpg")
if logo_path.exists():
    st.sidebar.image(str(logo_path), width=250)
else:
    st.sidebar.warning("🖼️ Logo image not found!")

st.sidebar.title("📁 Codebase Tools")
uploaded_file = st.sidebar.file_uploader("Upload a zipped codebase", type=["zip"])
index_button = st.sidebar.button("📦 Create Index")
clear_button = st.sidebar.button("🧹 Clear Session")

with st.sidebar.expander("ℹ️ How to Use"):
    st.markdown("""
    1. Upload a `.zip` file containing your code.
    2. Click **Create Index** to process and embed your codebase.
    3. Use the chat to query your code.
    4. You can switch between previously indexed projects below.
    """)

codebase_path = "codebase"

# --- Switch Between Indexed Projects ---
if st.session_state.db_map:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📂 Indexed Projects**")
    for name in st.session_state.db_map:
        if st.sidebar.button(f"📁 {name}", key=f"select_{name}"):
            st.session_state.current_file = name
            st.session_state.db = st.session_state.db_map[name]
            st.session_state.index_created = True
            st.sidebar.success(f"🔄 Switched to: {name}")

# --- Clear Current Session ---
if clear_button:
    if os.path.exists(codebase_path):
        shutil.rmtree(codebase_path)
    for key in ["uploaded", "index_created", "db", "current_file", "processed_docs"]:
        st.session_state[key] = None
    st.sidebar.success("Session cleared! Previous indexes retained.")

# --- Upload and Extract ZIP ---
if uploaded_file and not st.session_state.get("uploaded"):
    uploaded_name = uploaded_file.name.split(".")[0]
    st.session_state.current_file = uploaded_name

    # Define the new codebase path inside vectorstore
    codebase_path = os.path.join("vectorstore", uploaded_name)
    if os.path.exists(codebase_path):
        shutil.rmtree(codebase_path)
    os.makedirs(codebase_path, exist_ok=True)

    with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
        zip_ref.extractall(codebase_path)

    if not any(os.scandir(codebase_path)):
        st.sidebar.error("❌ Uploaded zip is empty.")
    else:
        st.sidebar.success("✅ Codebase extracted!")
        st.session_state.uploaded = True
        st.session_state.index_created = False
        st.session_state.db = None

# --- Create Index ---
if index_button:
    name = st.session_state.get("current_file")
    if not name:
        st.sidebar.warning("⚠️ Please upload a codebase.")
    else:
        codebase_path = os.path.join("vectorstore", name)  # NEW: Point to the extracted folder
        with st.spinner("🔍 Indexing your codebase..."):
            try:
                docs = load_and_split_code(codebase_path)
                st.session_state.processed_docs = docs
                if not docs:
                    st.sidebar.error("❌ No readable files found.")
                else:
                    db = create_or_load_index(docs, codebase_path)  # Index stored in same path
                    st.session_state.db = db
                    st.session_state.db_map[name] = db
                    st.session_state.index_created = True
                    st.sidebar.success("✅ Index created!")
            except Exception as e:
                st.sidebar.error(f"❌ Indexing failed: {e}")

# --- Branding Header ---
st.markdown("<h2 style='text-align: center;'>🤖 Codebase Assistant</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Upload. Index. Understand Your Code.</p>", unsafe_allow_html=True)

# --- Layout Tabs ---
tab1, tab2, tab3 = st.tabs(["💬 Ask Questions", "📄 Browse Code", "📊 Project Info"])

# --- Tab 1: Q&A ---
with tab1:
    st.subheader("Ask Questions About Your Codebase")
    query = st.text_input("💡 Enter your question:")
    if st.button("🧠 Get Answer", type="primary"):
        if not query.strip():
            st.warning("⚠️ Please enter a question.")
        elif not st.session_state.index_created or not st.session_state.db:
            st.warning("⚠️ Index not ready.")
        else:
            with st.spinner("🤖 Generating answer..."):
                try:
                    response = get_llm_response(query, st.session_state.db)
                    st.success("✅ Answer:")
                    st.write(response)
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# --- Tab 2: File Viewer ---
with tab2:
    st.subheader("📑 Files in Uploaded Project")
    if not os.path.exists(codebase_path):
        st.info("📂 No code files uploaded yet.")
    else:
        for root, _, files in os.walk(codebase_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                    with st.expander(f"📄 {file}"):
                        st.code(code, language="python")
                except Exception as e:
                    st.error(f"Error reading {file}: {e}")

# --- Tab 3: Stats ---
with tab3:
    st.subheader("📊 Codebase Statistics")
    num_files = len(st.session_state.processed_docs or [])
    num_chunks = sum(
        [len(doc.page_content) // 1000 + 1 for doc in st.session_state.processed_docs]
    ) if st.session_state.processed_docs else 0
    st.metric("📄 Total Files Loaded", num_files)
    st.metric("🔍 Total Chunks Indexed", num_chunks)
    st.metric("🤖 Embedding Model", "MiniLM-L6-v2")

# --- Footer ---
st.markdown("---")
st.markdown("Made with ❤️ by [Ayushi Sharma](https://github.com/AyushiSharma1310)", unsafe_allow_html=True)
