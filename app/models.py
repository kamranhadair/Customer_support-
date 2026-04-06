"""
app/models.py — Pydantic domain schemas for the Customer Support Agent.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Enums ──────────────────────────────────────────────────────────────────────


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CustomerPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ── Customer ───────────────────────────────────────────────────────────────────


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, examples=["Alice Johnson"])
    email: EmailStr = Field(..., examples=["alice@example.com"])
    plan: CustomerPlan = Field(default=CustomerPlan.FREE)
    company: Optional[str] = Field(default=None, max_length=120, examples=["Acme Corp"])
    phone: Optional[str] = Field(default=None, max_length=20, examples=["+1-555-0100"])


class CustomerCreate(CustomerBase):
    pass


class Customer(CustomerBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Ticket ─────────────────────────────────────────────────────────────────────


class TicketBase(BaseModel):
    customer_id: int = Field(..., gt=0)
    subject: str = Field(..., min_length=1, max_length=200, examples=["Cannot access my account"])
    description: str = Field(..., min_length=1, examples=["I have been trying to log in for 2 hours..."])
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM)


class TicketCreate(TicketBase):
    pass


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class Ticket(TicketBase):
    id: int
    status: TicketStatus = TicketStatus.OPEN
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Draft Response ─────────────────────────────────────────────────────────────


class DraftResponse(BaseModel):
    id: int
    ticket_id: int
    draft_text: str
    context_used: Optional[str] = None  # JSON blob of context sources
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Copilot API ────────────────────────────────────────────────────────────────


class CopilotRequest(BaseModel):
    ticket_id: int = Field(..., gt=0, examples=[1])


class KBResult(BaseModel):
    content: str
    source: str
    score: Optional[float] = None


class ContextBundle(BaseModel):
    """All context sources gathered by the copilot for a single ticket."""

    customer_memories: list[str] = Field(default_factory=list)
    kb_results: list[KBResult] = Field(default_factory=list)
    crm_data: dict[str, Any] = Field(default_factory=dict)
    billing_data: dict[str, Any] = Field(default_factory=dict)
    recent_tickets: list[dict[str, Any]] = Field(default_factory=list)


class CopilotResponse(BaseModel):
    ticket_id: int
    draft_text: str
    context: ContextBundle
    draft_id: Optional[int] = None


# ── Health ─────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    environment: str
