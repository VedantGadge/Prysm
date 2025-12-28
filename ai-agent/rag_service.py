
import os
import shutil
from typing import List
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Setup Chroma
DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
client = chromadb.PersistentClient(path=DB_PATH)

# Use Local SOTA Model: BAAI/bge-small-en-v1.5
# It's high performance but small enough (130MB) for local use.
class LocalEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self):
        print("Loading BGE-Small-EN-v1.5 model... (First run may take a moment)")
        self.model = SentenceTransformer('BAAI/bge-small-en-v1.5')

    def __call__(self, input: List[str]) -> List[List[float]]:
        # BGE expects "Represent this sentence for searching relevant passages: " instruction for queries
        # but for docs it just wants text. Since we mix them here in a simple call, we'll embed directly.
        # For optimum BGE performance, queries should have instruction, but we'll keep it simple for now.
        embeddings = self.model.encode(input).tolist()
        return embeddings

# Initialize global embedding function
embed_fn = LocalEmbeddingFunction()

# Get/Create Collection (New name to avoid conflict with old Gemini vectors)
collection = client.get_or_create_collection(
    name="prysm_docs_v2",
    embedding_function=embed_fn
)

def process_pdf(file_path: str, doc_id: str):
    """
    Reads a PDF, chunks it, and adds to ChromaDB.
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t + "\n"
            
        # Chunking Strategy
        chunk_size = 1000
        overlap = 200
        chunks = []
        
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
            
        if not chunks:
            return False, 0
            
        # Add to Chroma
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": doc_id, "chunk_index": i} for i in range(len(chunks))]
        
        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas
        )
        return True, len(chunks)
    except Exception as e:
        print(f"RAG Process Error: {e}")
        return False, 0

def query_rag(query_text: str, n_results=3):
    """
    Search the vector DB.
    """
    # For BGE models, adding this instruction to query improves retrieval
    query_with_instruction = f"Represent this sentence for searching relevant passages: {query_text}"
    
    results = collection.query(
        query_texts=[query_with_instruction],
        n_results=n_results
    )
    
    if not results['documents']:
        return []

    # Flatten results
    docs = results['documents'][0]
    return docs

def clear_db():
    client.delete_collection("prysm_docs_v2")
    # Re-create immediately
    global collection
    collection = client.get_or_create_collection(name="prysm_docs_v2", embedding_function=embed_fn)
