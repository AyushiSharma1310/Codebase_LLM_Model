import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PythonLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS          # ← updated
from langchain_community.llms import OpenAI
                # ← for Groq/OpenAI‑compatible completions

load_dotenv()

def load_and_split_code(path="codebase/"):
    docs = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                docs.extend(PythonLoader(full_path).load())

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return splitter.split_documents(docs)

def create_or_load_index(docs, persist_dir="vectorstore"):
    # Use a free local embedding model instead of OpenAI/Groq
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    
    if os.path.exists(persist_dir):
        return FAISS.load_local(persist_dir, embeddings, allow_dangerous_deserialization=True)
    else:
        db = FAISS.from_documents(docs, embeddings)
        db.save_local(persist_dir)
        return db

from groq import Groq
import os

def get_llm_response(query, db):
    docs = db.similarity_search(query, k=5)

    # ✅ Extract content
    content = "\n\n".join([doc.page_content for doc in docs if hasattr(doc, 'page_content')])

    # ✅ Print for debugging
    print("=== INPUT SENT TO GROQ ===")
    print(content)
    print("==========================")

    if not isinstance(content, str) or content.strip() == "":
        raise ValueError("Invalid input to LLM: Must be a non-empty string.")

    # ✅ Build the Groq client and send request
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
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
