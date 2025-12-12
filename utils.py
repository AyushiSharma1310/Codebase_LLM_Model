import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from groq import Groq
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Load environment variables from .env
load_dotenv()


def load_and_split_code(path: str) -> list:
    """
    Loads all readable code files from the given path and splits them into chunks.
    """
    docs = []
    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if content.strip():
                        docs.append(Document(page_content=content, metadata={"source": full_path}))
                        print(f"📄 Loaded: {full_path}")
            except Exception as e:
                print(f"⚠️ Error reading {full_path}: {e}")

    print(f"✅ Loaded {len(docs)} file(s) from '{path}'")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    print(f"🪓 Split into {len(chunks)} document chunk(s).")
    return chunks


def create_or_load_index(docs: list, persist_dir: str) -> FAISS:
    """
    Creates or loads a FAISS vector index from document chunks.
    """
    if not docs:
        raise ValueError("No documents provided for indexing.")

    valid_docs = [
        doc for doc in docs
        if isinstance(doc, Document) and isinstance(doc.page_content, str) and doc.page_content.strip()
    ]

    if not valid_docs:
        raise ValueError("No valid documents to index after filtering.")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )

    try:
        db = FAISS.from_documents(valid_docs, embeddings)
        db.save_local(persist_dir)
        print(f"✅ Vector index saved at: {persist_dir}")
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        raise

    return db


def get_llm_response(query: str, db: FAISS) -> str:
    """
    Uses Groq LLM to get an answer for the given query using retrieved documents.
    """
    if db is None:
        raise ValueError("Vector database is not initialized. Please create the index first.")

    docs = db.similarity_search(query, k=5)
    if not docs:
        raise ValueError("No relevant documents found for your query.")

    content = "\n\n".join([doc.page_content for doc in docs if isinstance(doc.page_content, str)])
    if not content.strip():
        raise ValueError("Invalid input to LLM: Must be a non-empty string.")

    print("🔍 Input passed to Groq LLM:")
    print(content)
    print("─────────────────────────────")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError("GROQ_API_KEY is missing or invalid. Check your .env file.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # <-- Changed to valid Groq model
        messages=[
            {"role": "system", "content": "You are a helpful assistant for code understanding."},
            {"role": "user", "content": f"{content}\n\nQuestion: {query}"}
        ],
        temperature=0.2,
        max_tokens=500
    )

    return response.choices[0].message.content
