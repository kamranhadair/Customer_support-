"""
tests/conftest.py — Shared pytest fixtures: in-memory DB, temporary ChromaDB paths.
"""
import os
import tempfile

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def use_temp_paths(tmp_path, monkeypatch):
    """Override storage paths to use isolated temp directories for every test."""
    db_path = str(tmp_path / "test.db")
    rag_path = str(tmp_path / "chroma_rag")
    mem_path = str(tmp_path / "chroma_mem0")

    monkeypatch.setenv("SQLITE_DB_PATH", db_path)
    monkeypatch.setenv("CHROMA_RAG_PATH", rag_path)
    monkeypatch.setenv("CHROMA_MEM0_PATH", mem_path)
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key_ci")

    # Reset lru_cache so settings reload from new env
    get_settings.cache_clear()

    # Reset Mem0 singleton
    import app.memory as mem_module
    mem_module._memory_instance = None

    yield

    # Cleanup: reset caches
    get_settings.cache_clear()
    mem_module._memory_instance = None
