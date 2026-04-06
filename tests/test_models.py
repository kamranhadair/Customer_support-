"""
tests/test_models.py — Unit tests for Pydantic domain models.
"""
import pytest
from pydantic import ValidationError

from app.models import (
    CustomerCreate,
    CustomerPlan,
    TicketCreate,
    TicketPriority,
    TicketStatus,
    TicketStatusUpdate,
    CopilotRequest,
)


def test_customer_create_valid():
    c = CustomerCreate(name="Alice", email="alice@example.com", plan=CustomerPlan.PRO)
    assert c.name == "Alice"
    assert c.email == "alice@example.com"
    assert c.plan == CustomerPlan.PRO


def test_customer_create_invalid_email():
    with pytest.raises(ValidationError):
        CustomerCreate(name="Bob", email="not-an-email", plan=CustomerPlan.FREE)


def test_customer_create_empty_name():
    with pytest.raises(ValidationError):
        CustomerCreate(name="", email="bob@example.com", plan=CustomerPlan.FREE)


def test_customer_plan_values():
    assert CustomerPlan.FREE.value == "free"
    assert CustomerPlan.ENTERPRISE.value == "enterprise"


def test_ticket_create_valid():
    t = TicketCreate(
        customer_id=1,
        subject="Login issue",
        description="Cannot login since yesterday",
        priority=TicketPriority.HIGH,
    )
    assert t.customer_id == 1
    assert t.priority == TicketPriority.HIGH


def test_ticket_create_invalid_customer_id():
    with pytest.raises(ValidationError):
        TicketCreate(customer_id=0, subject="Test", description="Test")


def test_ticket_status_update():
    update = TicketStatusUpdate(status=TicketStatus.RESOLVED)
    assert update.status == TicketStatus.RESOLVED


def test_copilot_request_valid():
    req = CopilotRequest(ticket_id=5)
    assert req.ticket_id == 5


def test_copilot_request_invalid():
    with pytest.raises(ValidationError):
        CopilotRequest(ticket_id=0)
