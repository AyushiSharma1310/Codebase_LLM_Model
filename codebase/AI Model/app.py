import streamlit as st
import zipfile
import os
import shutil
from utils import load_and_split_code, create_or_load_index, get_llm_response

st.set_page_config(page_title="RAG-based Code Assistant", page_icon="🧠")
st.title("🧠 RAG-based Code Assistant")
st.write("Upload your Python codebase and ask questions powered by Groq + LangChain.")

# Upload .zip file
uploaded_file = st.file_uploader("📁 Upload a zipped folder of your Python codebase", type=["zip"])

# Prepare codebase folder
codebase_path = "codebase"
if uploaded_file:
    if os.path.exists(codebase_path):
        shutil.rmtree(codebase_path)
    os.makedirs(codebase_path, exist_ok=True)

    with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
        zip_ref.extractall(codebase_path)
    st.success("✅ Codebase uploaded and extracted!")

# User input and button
query = st.text_input("💬 Enter your question:")
if st.button("Get Answer", type="primary") and query:
    if not uploaded_file:
        st.warning("⚠️ Please upload your codebase first.")
    else:
        with st.spinner("🔍 Indexing and retrieving relevant code..."):
            try:
                docs = load_and_split_code(codebase_path)
                db = create_or_load_index(docs)
                response = get_llm_response(query, db)
                st.success("✅ Answer:")
                st.write(response)
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")
