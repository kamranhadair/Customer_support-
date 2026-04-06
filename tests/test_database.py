"""
tests/test_database.py — Unit tests for the SQLite database layer.
"""
import pytest

from app.database import (
    init_db,
    create_customer,
    get_customer,
    get_customer_by_email,
    list_customers,
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_status,
    get_recent_tickets_by_customer,
    save_draft,
    get_drafts_for_ticket,
)
from app.models import CustomerCreate, CustomerPlan, TicketCreate, TicketPriority, TicketStatus


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def make_customer(email="test@example.com", plan=CustomerPlan.STARTER):
    return create_customer(CustomerCreate(
        name="Test User",
        email=email,
        plan=plan,
    ))


def make_ticket(customer_id: int, subject="Test subject"):
    return create_ticket(TicketCreate(
        customer_id=customer_id,
        subject=subject,
        description="Detailed description here",
        priority=TicketPriority.MEDIUM,
    ))


class TestCustomerCRUD:
    def test_create_and_get(self):
        c = make_customer()
        assert c.id is not None
        fetched = get_customer(c.id)
        assert fetched.email == "test@example.com"

    def test_get_nonexistent(self):
        assert get_customer(9999) is None

    def test_get_by_email(self):
        c = make_customer(email="unique@example.com")
        found = get_customer_by_email("unique@example.com")
        assert found.id == c.id

    def test_get_by_email_not_found(self):
        assert get_customer_by_email("ghost@example.com") is None

    def test_list_customers(self):
        make_customer(email="a@example.com")
        make_customer(email="b@example.com")
        customers = list_customers()
        assert len(customers) >= 2

    def test_duplicate_email_raises(self):
        make_customer(email="dup@example.com")
        with pytest.raises(Exception):
            make_customer(email="dup@example.com")


class TestTicketCRUD:
    def test_create_and_get(self):
        c = make_customer(email="tc@example.com")
        t = make_ticket(c.id)
        assert t.id is not None
        fetched = get_ticket(t.id)
        assert fetched.customer_id == c.id
        assert fetched.status == TicketStatus.OPEN

    def test_get_nonexistent(self):
        assert get_ticket(9999) is None

    def test_list_tickets_by_status(self):
        c = make_customer(email="lt@example.com")
        make_ticket(c.id, subject="Open ticket")
        tickets = list_tickets(status="open")
        assert any(t.subject == "Open ticket" for t in tickets)

    def test_update_status(self):
        c = make_customer(email="us@example.com")
        t = make_ticket(c.id)
        updated = update_ticket_status(t.id, TicketStatus.RESOLVED)
        assert updated.status == TicketStatus.RESOLVED

    def test_recent_tickets_by_customer(self):
        c = make_customer(email="rt@example.com")
        for i in range(3):
            make_ticket(c.id, subject=f"Ticket {i}")
        recent = get_recent_tickets_by_customer(c.id, limit=2)
        assert len(recent) == 2


class TestDraftCRUD:
    def test_save_and_retrieve_draft(self):
        c = make_customer(email="dr@example.com")
        t = make_ticket(c.id)
        draft = save_draft(t.id, "Dear customer, here is your response...", {"memories": []})
        assert draft.id is not None
        assert "Dear customer" in draft.draft_text

    def test_get_drafts_for_ticket(self):
        c = make_customer(email="gd@example.com")
        t = make_ticket(c.id)
        save_draft(t.id, "Draft 1")
        save_draft(t.id, "Draft 2")
        drafts = get_drafts_for_ticket(t.id)
        assert len(drafts) == 2

    def test_get_drafts_empty(self):
        c = make_customer(email="ed@example.com")
        t = make_ticket(c.id)
        assert get_drafts_for_ticket(t.id) == []
