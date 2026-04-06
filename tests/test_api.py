"""
tests/test_api.py — Integration tests for the FastAPI endpoints using TestClient.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestCustomerEndpoints:
    def test_create_customer(self, client):
        response = client.post("/customers/", json={
            "name": "API Test User",
            "email": "apitest@example.com",
            "plan": "pro",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test User"
        assert data["id"] is not None

    def test_create_duplicate_email_fails(self, client):
        client.post("/customers/", json={"name": "A", "email": "dup@example.com", "plan": "free"})
        response = client.post("/customers/", json={"name": "B", "email": "dup@example.com", "plan": "free"})
        assert response.status_code == 409

    def test_get_customer(self, client):
        create_resp = client.post("/customers/", json={
            "name": "Fetch Me", "email": "fetchme@example.com", "plan": "starter"
        })
        customer_id = create_resp.json()["id"]
        response = client.get(f"/customers/{customer_id}")
        assert response.status_code == 200
        assert response.json()["id"] == customer_id

    def test_get_customer_not_found(self, client):
        response = client.get("/customers/99999")
        assert response.status_code == 404

    def test_list_customers(self, client):
        client.post("/customers/", json={"name": "L1", "email": "l1@example.com", "plan": "free"})
        client.post("/customers/", json={"name": "L2", "email": "l2@example.com", "plan": "pro"})
        response = client.get("/customers/")
        assert response.status_code == 200
        assert len(response.json()) >= 2


class TestTicketEndpoints:
    def _create_customer(self, client, email="ticket_test@example.com"):
        resp = client.post("/customers/", json={"name": "Ticket User", "email": email, "plan": "starter"})
        return resp.json()["id"]

    def test_create_ticket(self, client):
        cid = self._create_customer(client)
        response = client.post("/tickets/", json={
            "customer_id": cid,
            "subject": "My API ticket",
            "description": "Detailed description",
            "priority": "high",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "open"
        assert data["customer_id"] == cid

    def test_create_ticket_invalid_customer(self, client):
        response = client.post("/tickets/", json={
            "customer_id": 99999,
            "subject": "Test",
            "description": "Test",
        })
        assert response.status_code == 404

    def test_get_ticket(self, client):
        cid = self._create_customer(client, email="gt@example.com")
        t_resp = client.post("/tickets/", json={
            "customer_id": cid, "subject": "Get me", "description": "Desc"
        })
        tid = t_resp.json()["id"]
        response = client.get(f"/tickets/{tid}")
        assert response.status_code == 200
        assert response.json()["id"] == tid

    def test_get_ticket_not_found(self, client):
        assert client.get("/tickets/99999").status_code == 404

    def test_update_ticket_status(self, client):
        cid = self._create_customer(client, email="us2@example.com")
        t_resp = client.post("/tickets/", json={
            "customer_id": cid, "subject": "Status test", "description": "Desc"
        })
        tid = t_resp.json()["id"]
        response = client.patch(f"/tickets/{tid}/status", json={"status": "resolved"})
        assert response.status_code == 200
        assert response.json()["status"] == "resolved"

    def test_list_tickets_filtered_by_status(self, client):
        cid = self._create_customer(client, email="lf@example.com")
        client.post("/tickets/", json={"customer_id": cid, "subject": "T1", "description": "D"})
        response = client.get("/tickets/?status=open")
        assert response.status_code == 200
        for t in response.json():
            assert t["status"] == "open"


class TestCopilotEndpoint:
    def test_copilot_generate_success(self, client):
        """Test copilot endpoint with mocked generate_draft."""
        from app.models import CopilotResponse, ContextBundle
        # Create customer + ticket
        c_resp = client.post("/customers/", json={
            "name": "Copilot User", "email": "copilot@example.com", "plan": "pro"
        })
        cid = c_resp.json()["id"]
        t_resp = client.post("/tickets/", json={
            "customer_id": cid,
            "subject": "Copilot test",
            "description": "Test description for copilot",
        })
        tid = t_resp.json()["id"]

        mock_response = CopilotResponse(
            ticket_id=tid,
            draft_text="Dear User, thank you for contacting us...",
            draft_id=1,
            context=ContextBundle(
                customer_memories=["Customer prefers email contact"],
                kb_results=[],
                crm_data={"plan": "pro"},
                billing_data={"monthly_amount_usd": 99.0},
                recent_tickets=[],
            ),
        )

        with patch("app.main.generate_draft", return_value=mock_response):
            response = client.post("/copilot/generate", json={"ticket_id": tid})

        assert response.status_code == 200
        data = response.json()
        assert "draft_text" in data
        assert data["ticket_id"] == tid

    def test_copilot_ticket_not_found(self, client):
        response = client.post("/copilot/generate", json={"ticket_id": 99999})
        assert response.status_code == 404
