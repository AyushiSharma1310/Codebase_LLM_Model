import sys, types
import os
import zipfile
import shutil
import streamlit as st

from utils import load_and_split_code, create_or_load_index, get_llm_response

# Monkey patch for torch.classes bug in Streamlit file watching
sys.modules["torch.classes"] = types.SimpleNamespace(__path__=[])

# Set API key manually for Groq
os.getenv("GROQ_API_KEY")
# Streamlit page config
st.set_page_config(page_title="RAG-based Code Assistant", page_icon="🧠", layout="wide")
st.title("🧠 RAG-based Code Assistant")

# Initialize session state
for key in ["index_created", "db", "uploaded", "processed_docs", "db_map", "current_file"]:
    if key not in st.session_state:
        st.session_state[key] = {} if key == "db_map" else None

# Sidebar
st.sidebar.title("🔧 Tools")
uploaded_file = st.sidebar.file_uploader("📁 Upload a zipped codebase", type=["zip"])
index_button = st.sidebar.button("📦 Create Index")
clear_button = st.sidebar.button("🧹 Clear Session")

codebase_path = "codebase"

# Switch between indexed projects
if st.session_state.db_map:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📂 Indexed Projects**")
    for name in st.session_state.db_map:
        if st.sidebar.button(f"📂 {name}", key=f"select_{name}"):
            st.session_state.current_file = name
            st.session_state.db = st.session_state.db_map[name]
            st.session_state.index_created = True
            st.sidebar.success(f"Switched to: {name}")

# Clear current session
if clear_button:
    if os.path.exists(codebase_path):
        shutil.rmtree(codebase_path)
    for key in ["uploaded", "index_created", "db", "current_file", "processed_docs"]:
        st.session_state[key] = None
    st.sidebar.success("🧹 Session cleared. Previous indexes retained.")

# Upload ZIP file
if uploaded_file and not st.session_state.get("uploaded"):
    uploaded_name = uploaded_file.name.split(".")[0]
    st.session_state.current_file = uploaded_name

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

# Create vector index
if index_button:
    name = st.session_state.get("current_file")
    if not name:
        st.sidebar.warning("⚠️ Upload codebase first.")
    else:
        with st.spinner("🔍 Indexing files..."):
            try:
                docs = load_and_split_code(codebase_path)
                if not docs:
                    st.sidebar.error("❌ No readable files found.")
                else:
                    persist_path = os.path.join("vectorstore", name)
                    db = create_or_load_index(docs, persist_path)
                    st.session_state.db = db
                    st.session_state.db_map[name] = db
                    st.session_state.index_created = True
                    st.sidebar.success("✅ Index created!")
            except Exception as e:
                st.sidebar.error(f"❌ Indexing failed: {e}")

# Chat section
st.markdown("### 💬 Ask your code questions below")
query = st.text_input("Enter your question:")

if st.button("Get Answer", type="primary"):
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
