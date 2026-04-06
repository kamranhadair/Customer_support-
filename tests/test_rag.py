"""
tests/test_rag.py — Unit tests for the RAG pipeline.
"""
import os
import pytest

from app.rag import ingest_documents, search_knowledge_base, get_kb_stats


@pytest.fixture
def kb_docs(tmp_path):
    """Create temporary knowledge base documents."""
    doc1 = tmp_path / "refunds.md"
    doc1.write_text(
        "# Refund Policy\n\nWe offer 30-day refunds. "
        "Customers can request a full refund within 30 days of purchase. "
        "Contact billing@example.com to request a refund."
    )
    doc2 = tmp_path / "plans.md"
    doc2.write_text(
        "# Subscription Plans\n\nFree plan offers 500 API calls per month. "
        "Pro plan offers 100,000 API calls for $99/month. "
        "Enterprise plan has unlimited API calls with custom pricing."
    )
    return str(tmp_path)


def test_ingest_documents(kb_docs, monkeypatch):
    monkeypatch.setenv("KB_DOCS_PATH", kb_docs)
    from app.config import get_settings
    get_settings.cache_clear()

    count = ingest_documents(kb_docs)
    assert count > 0


def test_ingest_empty_dir(tmp_path):
    count = ingest_documents(str(tmp_path))
    assert count == 0


def test_ingest_nonexistent_dir():
    count = ingest_documents("/nonexistent/path")
    assert count == 0


def test_search_after_ingest(kb_docs):
    ingest_documents(kb_docs)
    results = search_knowledge_base("refund policy", n_results=2)
    assert len(results) > 0
    assert "content" in results[0]
    assert "source" in results[0]
    assert "score" in results[0]


def test_search_empty_kb():
    # No documents ingested in this test
    results = search_knowledge_base("anything")
    assert results == []


def test_search_empty_query(kb_docs):
    ingest_documents(kb_docs)
    results = search_knowledge_base("")
    assert results == []


def test_search_relevance(kb_docs):
    ingest_documents(kb_docs)
    results = search_knowledge_base("API calls per month pricing")
    # Should find something related to plans
    assert len(results) > 0
    assert any("plan" in r["source"].lower() or "plan" in r["content"].lower() for r in results)


def test_kb_stats(kb_docs):
    ingest_documents(kb_docs)
    stats = get_kb_stats()
    assert "total_chunks" in stats
    assert stats["total_chunks"] > 0
