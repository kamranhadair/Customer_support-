"""
app/rag.py — RAG pipeline: ingest knowledge base docs into ChromaDB, semantic search.
"""
import logging
import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

from app.config import get_settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "knowledge_base"
CHUNK_SIZE = 500          # characters per chunk
CHUNK_OVERLAP = 80        # overlap to preserve context at boundaries


# ── Client & Collection ────────────────────────────────────────────────────────


def _get_embedding_function():
    """Return a local SentenceTransformer embedding function (no API key required)."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def _get_client() -> chromadb.PersistentClient:
    settings = get_settings()
    os.makedirs(settings.chroma_rag_path, exist_ok=True)
    return chromadb.PersistentClient(path=settings.chroma_rag_path)


def get_collection() -> chromadb.Collection:
    """Get or create the knowledge-base ChromaDB collection."""
    client = _get_client()
    ef = _get_embedding_function()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


# ── Text Chunking ──────────────────────────────────────────────────────────────


def _chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({
                "text": chunk,
                "id": f"{source}_chunk_{idx}",
                "source": source,
            })
            idx += 1
        start = end - CHUNK_OVERLAP
    return chunks


# ── Ingestion ──────────────────────────────────────────────────────────────────


def ingest_documents(docs_dir: Optional[str] = None) -> int:
    """
    Read all .txt and .md files from docs_dir, chunk them, and upsert into ChromaDB.
    Returns the number of chunks ingested.
    """
    settings = get_settings()
    docs_path = Path(docs_dir or settings.kb_docs_path)

    if not docs_path.exists():
        logger.warning("KB docs directory does not exist: %s", docs_path)
        return 0

    collection = get_collection()
    all_chunks: list[dict] = []

    for filepath in sorted(docs_path.glob("**/*")):
        if filepath.suffix.lower() not in {".txt", ".md"}:
            continue
        try:
            text = filepath.read_text(encoding="utf-8")
            source = filepath.stem
            chunks = _chunk_text(text, source)
            all_chunks.extend(chunks)
            logger.info("Chunked %s → %d chunks", filepath.name, len(chunks))
        except Exception as exc:
            logger.error("Failed to read %s: %s", filepath, exc)

    if not all_chunks:
        logger.warning("No documents found to ingest in %s", docs_path)
        return 0

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{"source": c["source"]} for c in batch],
        )

    logger.info("Ingested %d total chunks into ChromaDB", len(all_chunks))
    return len(all_chunks)


# ── Search ─────────────────────────────────────────────────────────────────────


def search_knowledge_base(query: str, n_results: int = 3) -> list[dict]:
    """
    Perform semantic search against the knowledge base.

    Returns a list of dicts with keys: content, source, score.
    """
    if not query.strip():
        return []

    collection = get_collection()

    # Check if collection has documents
    if collection.count() == 0:
        logger.warning("Knowledge base is empty. Run ingest_documents() first.")
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.error("ChromaDB query failed: %s", exc)
        return []

    hits = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        # Cosine distance → similarity score (1 - dist)
        hits.append({
            "content": doc,
            "source": meta.get("source", "unknown"),
            "score": round(1.0 - dist, 4),
        })

    return hits


def get_kb_stats() -> dict:
    """Return stats about the knowledge base collection."""
    collection = get_collection()
    return {
        "collection_name": COLLECTION_NAME,
        "total_chunks": collection.count(),
        "chroma_path": get_settings().chroma_rag_path,
    }
