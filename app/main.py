"""
app/main.py — FastAPI REST API for the Customer Support Agent.
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.copilot import generate_draft
from app.database import (
    create_customer,
    create_ticket,
    get_customer,
    get_customer_by_email,
    get_drafts_for_ticket,
    get_ticket,
    init_db,
    list_customers,
    list_tickets,
    update_ticket_status,
)
from app.models import (
    CopilotRequest,
    CopilotResponse,
    Customer,
    CustomerCreate,
    DraftResponse,
    HealthResponse,
    Ticket,
    TicketCreate,
    TicketStatusUpdate,
)
from app.rag import ingest_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and ingest KB docs on startup."""
    logger.info("🚀 Starting Customer Support Agent API...")
    settings = get_settings()

    init_db()
    logger.info("✅ Database initialized")

    chunks = ingest_documents(settings.kb_docs_path)
    logger.info("✅ Knowledge base ingested: %d chunks", chunks)

    yield

    logger.info("🛑 Shutting down...")


# ── App Setup ──────────────────────────────────────────────────────────────────


app = FastAPI(
    title="Customer Support Agent API",
    description=(
        "AI-Powered Customer Support Copilot with RAG, Persistent Memory (Mem0), "
        "and LangChain Tool Calling."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────────────────


@app.get("/", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Check API health and current environment."""
    return HealthResponse(environment=get_settings().app_env)


# ── Customers ──────────────────────────────────────────────────────────────────


@app.post("/customers/", response_model=Customer, status_code=201, tags=["Customers"])
def create_customer_endpoint(payload: CustomerCreate):
    """Create a new customer."""
    if get_customer_by_email(payload.email):
        raise HTTPException(status_code=409, detail=f"Customer with email '{payload.email}' already exists")
    return create_customer(payload)


@app.get("/customers/", response_model=list[Customer], tags=["Customers"])
def list_customers_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all customers (paginated)."""
    return list_customers(limit=limit, offset=offset)


@app.get("/customers/{customer_id}", response_model=Customer, tags=["Customers"])
def get_customer_endpoint(customer_id: int):
    """Get a single customer by ID."""
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


# ── Tickets ────────────────────────────────────────────────────────────────────


@app.post("/tickets/", response_model=Ticket, status_code=201, tags=["Tickets"])
def create_ticket_endpoint(payload: TicketCreate):
    """Create a new support ticket."""
    if get_customer(payload.customer_id) is None:
        raise HTTPException(status_code=404, detail=f"Customer {payload.customer_id} not found")
    return create_ticket(payload)


@app.get("/tickets/", response_model=list[Ticket], tags=["Tickets"])
def list_tickets_endpoint(
    status: Optional[str] = Query(None, description="Filter by status: open, in_progress, resolved, closed"),
    customer_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List tickets with optional filters."""
    return list_tickets(status=status, customer_id=customer_id, limit=limit, offset=offset)


@app.get("/tickets/{ticket_id}", response_model=Ticket, tags=["Tickets"])
def get_ticket_endpoint(ticket_id: int):
    """Get a single ticket by ID."""
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@app.patch("/tickets/{ticket_id}/status", response_model=Ticket, tags=["Tickets"])
def update_ticket_status_endpoint(ticket_id: int, payload: TicketStatusUpdate):
    """Update the status of a ticket."""
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return update_ticket_status(ticket_id, payload.status)


@app.get("/tickets/{ticket_id}/drafts", response_model=list[DraftResponse], tags=["Tickets"])
def get_ticket_drafts_endpoint(ticket_id: int):
    """Get all AI-generated draft responses for a ticket."""
    if get_ticket(ticket_id) is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return get_drafts_for_ticket(ticket_id)


# ── Copilot ────────────────────────────────────────────────────────────────────


@app.post("/copilot/generate", response_model=CopilotResponse, tags=["Copilot"])
def copilot_generate_endpoint(payload: CopilotRequest):
    """
    🤖 Generate an AI-powered draft response for a support ticket.

    The copilot automatically:
    - Searches the knowledge base (RAG/ChromaDB)
    - Retrieves persistent customer memories (Mem0)
    - Looks up CRM and billing data (LangChain tool calling)
    - Generates a ready-to-review draft response (ChatGroq)
    """
    ticket = get_ticket(payload.ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {payload.ticket_id} not found")

    try:
        result = generate_draft(payload.ticket_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Copilot generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Draft generation failed: {exc}")
