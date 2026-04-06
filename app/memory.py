"""
app/memory.py — Persistent customer memory using Mem0 with local ChromaDB backend.
"""
import logging
import os
from typing import Optional

from mem0 import Memory

from app.config import get_settings

logger = logging.getLogger(__name__)

_memory_instance: Optional[Memory] = None


# ── Initialization ─────────────────────────────────────────────────────────────


def get_memory() -> Memory:
    """Return a singleton Mem0 Memory instance (local ChromaDB backend)."""
    global _memory_instance
    if _memory_instance is not None:
        return _memory_instance

    settings = get_settings()
    os.makedirs(settings.chroma_mem0_path, exist_ok=True)

    config = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "customer_memories",
                "path": settings.chroma_mem0_path,
            },
        },
        "llm": {
            "provider": "groq",
            "config": {
                "model": settings.groq_model,
                "api_key": settings.groq_api_key,
                "temperature": 0.1,
                "max_tokens": 1000,
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "multi-qa-MiniLM-L6-cos-v1",
            },
        },
        "version": "v1.1",
    }

    _memory_instance = Memory.from_config(config)
    logger.info("Mem0 initialized with local ChromaDB at %s", settings.chroma_mem0_path)
    return _memory_instance


# ── Memory Operations ──────────────────────────────────────────────────────────


def add_customer_memory(customer_id: int, text: str, metadata: Optional[dict] = None) -> list[dict]:
    """
    Store a new memory for a customer (extracted from conversation text).

    Mem0 intelligently extracts facts from the text and stores them.
    Returns the list of memory entries added.
    """
    mem = get_memory()
    extra_meta = {"customer_id": str(customer_id), **(metadata or {})}
    try:
        result = mem.add(text, user_id=str(customer_id), metadata=extra_meta)
        added = result.get("results", []) if isinstance(result, dict) else result
        logger.info(
            "Added %d memory entries for customer %s", len(added), customer_id
        )
        return added
    except Exception as exc:
        logger.error("Failed to add memory for customer %s: %s", customer_id, exc)
        return []


def search_customer_memory(customer_id: int, query: str, limit: int = 5) -> list[str]:
    """
    Retrieve memories most relevant to the given query for a specific customer.

    Returns a list of memory text strings.
    """
    if not query.strip():
        return []

    mem = get_memory()
    try:
        results = mem.search(query, user_id=str(customer_id), limit=limit)
        memories = results.get("results", []) if isinstance(results, dict) else results
        texts = [
            m.get("memory", m.get("text", str(m)))
            for m in memories
            if m
        ]
        logger.info(
            "Found %d memories for customer %s (query: %r)",
            len(texts), customer_id, query[:50],
        )
        return texts
    except Exception as exc:
        logger.error("Memory search failed for customer %s: %s", customer_id, exc)
        return []


def get_all_customer_memories(customer_id: int) -> list[dict]:
    """
    Return all stored memories for a customer.
    Useful for displaying history in the dashboard.
    """
    mem = get_memory()
    try:
        results = mem.get_all(user_id=str(customer_id))
        memories = results.get("results", []) if isinstance(results, dict) else results
        return memories or []
    except Exception as exc:
        logger.error("Failed to get all memories for customer %s: %s", customer_id, exc)
        return []


def delete_customer_memories(customer_id: int) -> bool:
    """Delete all memories for a customer (e.g., on account deletion)."""
    mem = get_memory()
    try:
        mem.delete_all(user_id=str(customer_id))
        logger.info("Deleted all memories for customer %s", customer_id)
        return True
    except Exception as exc:
        logger.error("Failed to delete memories for customer %s: %s", customer_id, exc)
        return False
