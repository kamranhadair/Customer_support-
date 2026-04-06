"""
app/config.py — Application settings loaded from environment variables.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configurable values for the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ────────────────────────────────────────────────────────────────────
    groq_api_key: str = "your_groq_api_key_here"
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Database ───────────────────────────────────────────────────────────────
    sqlite_db_path: str = "./data/support.db"

    # ── ChromaDB ───────────────────────────────────────────────────────────────
    chroma_rag_path: str = "./chroma_rag"
    chroma_mem0_path: str = "./chroma_mem0"

    # ── Knowledge Base ─────────────────────────────────────────────────────────
    kb_docs_path: str = "./knowledge_base/docs"

    # ── App ────────────────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    backend_url: str = "http://localhost:8000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance — reads .env once."""
    return Settings()
