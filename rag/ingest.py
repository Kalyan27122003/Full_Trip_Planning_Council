# rag/ingest.py
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
CHROMA_DIR = Path(__file__).parent / "chroma_db"

COLLECTION_MAP = {
    "destinations.txt": "destinations",
    "hotels.txt":        "hotels",
    "food_culture.txt":  "food_culture",
    "transport.txt":     "transport",
    "safety_tips.txt":   "safety_tips",
}

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

def ingest_all():
    embeddings = get_embeddings()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    for filename, collection_name in COLLECTION_MAP.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"⚠️  {filepath} not found, skipping.")
            continue

        loader = TextLoader(str(filepath), encoding="utf-8")
        docs = loader.load()
        chunks = splitter.split_documents(docs)

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=str(CHROMA_DIR),
        )
        print(f"✅  Ingested {len(chunks)} chunks → collection: '{collection_name}'")

    print("\n🎉 All data ingested into ChromaDB successfully!")

if __name__ == "__main__":
    ingest_all()
