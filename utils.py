import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from groq import Groq
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

def load_and_split_code(path="codebase/"):
    docs = []
    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if content.strip():
                        docs.append(Document(page_content=content, metadata={"source": full_path}))
                        print(f"Loaded: {full_path}")
            except Exception as e:
                print(f"Error loading {full_path}: {e}")
    print(f"Loaded {len(docs)} files from {path}")
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} document chunks.")
    return chunks

def create_or_load_index(docs, persist_dir="vectorstore"):
    if not docs:
        raise ValueError("No documents found to index.")

    docs = [
        doc for doc in docs
        if isinstance(doc, Document) and hasattr(doc, "page_content") and isinstance(doc.page_content, str) and doc.page_content.strip()
    ]

    if not docs:
        raise ValueError("No valid documents to index after filtering.")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )

    try:
        if os.path.exists(persist_dir):
            db = FAISS.load_local(persist_dir, embeddings, allow_dangerous_deserialization=True)
        else:
            db = FAISS.from_documents(docs, embeddings)
            db.save_local(persist_dir)
    except Exception as e:
        print(f"Index load/create error: {e}. Rebuilding...")
        db = FAISS.from_documents(docs, embeddings)
        db.save_local(persist_dir)

    print("DEBUG: Returning db object from create_or_load_index")
    return db

def get_llm_response(query, db):
    if db is None:
        raise ValueError("The vector database is not initialized. Please create the index first.")

    docs = db.similarity_search(query, k=5)
    if not docs:
        raise ValueError("No relevant documents found for your query.")

    content = "\n\n".join([doc.page_content for doc in docs if hasattr(doc, 'page_content')])

    print("=== INPUT SENT TO GROQ ===")
    print(content)
    print("==========================")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Invalid input to LLM: Must be a non-empty string.")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError("GROQ_API_KEY is missing or invalid. Please check your .env file or environment variable.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for code understanding."},
            {"role": "user", "content": f"{content}\n\nQuestion: {query}"}
        ],
        temperature=0.2,
        max_tokens=500
    )

    return response.choices[0].message.content
