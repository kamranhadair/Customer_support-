# AI-Powered Customer Support Agent 🤖

> **Cut ticket resolution time by automating context gathering.** This copilot automatically retrieves customer history, searches the knowledge base, looks up CRM/billing data, and generates a ready-to-review draft response — all in one click.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                       │
│   main.py (FastAPI REST API)  │  app.py (Streamlit Dashboard)  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                        Application Layer                        │
│          copilot.py — Orchestrator (Mem0 + RAG + Tools)        │
└──────┬──────────────┬──────────────┬───────────────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌───▼──────────────────────────┐
│  memory.py  │ │   rag.py   │ │           tools.py            │
│ (Mem0 +     │ │ (ChromaDB) │ │ (Mock CRM + Billing LangChain)│
│  ChromaDB)  │ │            │ │                               │
└──────┬──────┘ └─────┬──────┘ └────────────────┬─────────────┘
       │              │                         │
┌──────▼──────────────▼─────────────────────────▼─────────────┐
│                         Data Stores                          │
│  support.db (SQLite) │ chroma_mem0 │ chroma_rag             │
└──────────────────────────────────────────────────────────────┘
```

## ✨ Key Features

| Feature | Technology |
|---------|-----------|
| **Persistent Customer Memory** | Mem0 (local ChromaDB) |
| **Knowledge Base RAG Search** | ChromaDB + SentenceTransformers |
| **CRM & Billing Lookups** | LangChain Tool Calling |
| **AI Draft Generation** | ChatGroq (llama-3.3-70b-versatile) |
| **REST API** | FastAPI |
| **Support Agent Dashboard** | Streamlit |
| **Containerization** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions |

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/kamranhadair/Customer_support-.git
cd Customer_support-
python -m venv .venv && source .venv/bin/activate
make install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your GROQ_API_KEY
```

Get a free API key at [console.groq.com](https://console.groq.com).

### 3. Seed Sample Data

```bash
make seed
```

### 4. Run

```bash
# Terminal 1 — FastAPI backend
make run-api

# Terminal 2 — Streamlit dashboard
make run-dashboard
```

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

### 5. Docker (Alternative)

```bash
make docker-build
make docker-up
```

## 📋 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/customers/` | Create customer |
| GET | `/customers/` | List customers |
| GET | `/customers/{id}` | Get customer |
| POST | `/tickets/` | Create ticket |
| GET | `/tickets/` | List tickets |
| GET | `/tickets/{id}` | Get ticket |
| PATCH | `/tickets/{id}/status` | Update ticket status |
| **POST** | **`/copilot/generate`** | **Generate AI draft** |
| GET | `/tickets/{id}/drafts` | Get drafts for ticket |

## 🧪 Development

```bash
make install-dev   # Install dev dependencies
make lint          # Run ruff linter
make test          # Run all tests
make test-cov      # Tests with coverage
```

## 📁 Project Structure

```
├── app/
│   ├── main.py        # FastAPI routes
│   ├── copilot.py     # Orchestrator
│   ├── config.py      # Settings
│   ├── models.py      # Pydantic schemas
│   ├── database.py    # SQLite operations
│   ├── memory.py      # Mem0 memory layer
│   ├── rag.py         # RAG pipeline
│   └── tools.py       # CRM/billing tools
├── dashboard/
│   └── app.py         # Streamlit dashboard
├── knowledge_base/
│   └── docs/          # KB source documents
├── tests/             # Pytest test suite
├── .github/workflows/ # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
└── seed_data.py       # Sample data seeder
```

## 📄 License

MIT
