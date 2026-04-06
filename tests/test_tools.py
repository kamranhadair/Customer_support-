"""
tests/test_tools.py — Unit tests for LangChain CRM/billing tools.
"""
import pytest

from app.database import init_db, create_customer, create_ticket
from app.models import CustomerCreate, CustomerPlan, TicketCreate, TicketPriority
from app.tools import (
    get_customer_profile,
    get_billing_info,
    get_recent_tickets,
    update_ticket_status_tool,
)


@pytest.fixture(autouse=True)
def setup_db_with_data():
    init_db()
    customer = create_customer(CustomerCreate(
        name="Tool Test User",
        email="tooltest@example.com",
        plan=CustomerPlan.PRO,
        company="TestCo",
    ))
    ticket = create_ticket(TicketCreate(
        customer_id=customer.id,
        subject="Tool test ticket",
        description="This is a test",
        priority=TicketPriority.HIGH,
    ))
    return {"customer": customer, "ticket": ticket}


def test_get_customer_profile_success(setup_db_with_data):
    customer = setup_db_with_data["customer"]
    result = get_customer_profile.invoke({"customer_id": str(customer.id)})
    assert result["customer_id"] == customer.id
    assert result["plan"] == "pro"
    assert result["name"] == "Tool Test User"


def test_get_customer_profile_not_found():
    result = get_customer_profile.invoke({"customer_id": "99999"})
    assert "error" in result


def test_get_billing_info_success(setup_db_with_data):
    customer = setup_db_with_data["customer"]
    result = get_billing_info.invoke({"customer_id": str(customer.id)})
    assert result["monthly_amount_usd"] == 99.00
    assert result["plan"] == "pro"
    assert "next_renewal_date" in result


def test_get_billing_info_free_plan():
    customer = create_customer(CustomerCreate(
        name="Free User",
        email="free@example.com",
        plan=CustomerPlan.FREE,
    ))
    result = get_billing_info.invoke({"customer_id": str(customer.id)})
    assert result["monthly_amount_usd"] == 0.0
    assert result["billing_cycle"] == "N/A"


def test_get_recent_tickets_success(setup_db_with_data):
    customer = setup_db_with_data["customer"]
    result = get_recent_tickets.invoke({"customer_id": str(customer.id)})
    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0]["subject"] == "Tool test ticket"


def test_get_recent_tickets_empty():
    new_cust = create_customer(CustomerCreate(
        name="No Tickets User",
        email="notixckets@example.com",
        plan=CustomerPlan.STARTER,
    ))
    result = get_recent_tickets.invoke({"customer_id": str(new_cust.id)})
    assert result == []


def test_update_ticket_status_valid(setup_db_with_data):
    ticket = setup_db_with_data["ticket"]
    result = update_ticket_status_tool.invoke({
        "ticket_id": str(ticket.id),
        "status": "resolved",
    })
    assert result["success"] is True
    assert result["new_status"] == "resolved"


def test_update_ticket_status_invalid_status(setup_db_with_data):
    ticket = setup_db_with_data["ticket"]
    result = update_ticket_status_tool.invoke({
        "ticket_id": str(ticket.id),
        "status": "invalid_status",
    })
    assert "error" in result


def test_update_ticket_status_not_found():
    result = update_ticket_status_tool.invoke({
        "ticket_id": "99999",
        "status": "resolved",
    })
    assert "error" in result
