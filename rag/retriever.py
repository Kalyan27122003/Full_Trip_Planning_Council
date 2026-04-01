# rag/retriever.py
from pathlib import Path
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

CHROMA_DIR = Path(__file__).parent / "chroma_db"

_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
    return _embeddings

def query_rag(collection_name: str, query: str, k: int = 4) -> str:
    """Query a ChromaDB collection and return formatted context."""
    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=get_embeddings(),
            persist_directory=str(CHROMA_DIR),
        )
        docs = vectorstore.similarity_search(query, k=k)
        if not docs:
            return "No relevant information found in knowledge base."
        return "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        return f"RAG retrieval error: {str(e)}"
