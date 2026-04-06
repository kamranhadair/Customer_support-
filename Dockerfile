# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a prefix we can copy
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/              ./app/
COPY dashboard/        ./dashboard/
COPY knowledge_base/   ./knowledge_base/
COPY seed_data.py      .
COPY .env.example      .env

# Create data directories
RUN mkdir -p data chroma_rag chroma_mem0

# Expose both API and dashboard ports
EXPOSE 8000 8501

# Default: run the FastAPI backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
