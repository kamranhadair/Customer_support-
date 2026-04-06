"""
app/tools.py — LangChain tool-decorated CRM and billing functions.
These tools are called by the copilot orchestrator via LLM tool-calling.
"""
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _future_date(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


# ── Tools ──────────────────────────────────────────────────────────────────────


@tool
def get_customer_profile(customer_id: str) -> dict[str, Any]:
    """
    Retrieve a customer's CRM profile including their account details,
    contact information, subscription plan, and account health status.
    Use this to understand who the customer is and their current plan.
    """
    # Import here to avoid circular imports
    from app.database import get_customer

    try:
        customer = get_customer(int(customer_id))
        if customer is None:
            return {"error": f"Customer {customer_id} not found"}

        # Enrich with mock CRM fields
        return {
            "customer_id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "plan": customer.plan.value,
            "company": customer.company or "Individual",
            "phone": customer.phone or "Not provided",
            "account_created": customer.created_at.strftime("%Y-%m-%d"),
            "account_health": _mock_account_health(customer.plan.value),
            "nps_score": random.randint(6, 10),
            "total_logins_last_30d": random.randint(5, 120),
        }
    except Exception as exc:
        logger.error("get_customer_profile error: %s", exc)
        return {"error": str(exc)}


def _mock_account_health(plan: str) -> str:
    health_map = {
        "free": "at_risk",
        "starter": "healthy",
        "pro": "healthy",
        "enterprise": "champion",
    }
    return health_map.get(plan, "healthy")


@tool
def get_billing_info(customer_id: str) -> dict[str, Any]:
    """
    Look up the billing and payment information for a customer, including
    their current plan cost, next renewal date, payment method, and any
    outstanding balance. Use this when a customer asks about charges,
    invoices, refunds, or payment issues.
    """
    from app.database import get_customer

    try:
        customer = get_customer(int(customer_id))
        if customer is None:
            return {"error": f"Customer {customer_id} not found"}

        plan_pricing = {
            "free": 0.00,
            "starter": 29.00,
            "pro": 99.00,
            "enterprise": 499.00,
        }
        plan = customer.plan.value
        amount = plan_pricing.get(plan, 0.00)

        return {
            "customer_id": customer.id,
            "plan": plan,
            "monthly_amount_usd": amount,
            "billing_cycle": "monthly" if plan != "free" else "N/A",
            "next_renewal_date": _future_date(random.randint(1, 28)) if plan != "free" else "N/A",
            "payment_method": _mock_payment_method(plan),
            "outstanding_balance_usd": 0.00,
            "last_payment_date": _future_date(-random.randint(1, 28)),
            "last_payment_amount_usd": amount,
            "invoices_available": plan != "free",
            "auto_renew": True,
        }
    except Exception as exc:
        logger.error("get_billing_info error: %s", exc)
        return {"error": str(exc)}


def _mock_payment_method(plan: str) -> str:
    if plan == "free":
        return "N/A"
    methods = ["Visa ending in 4242", "Mastercard ending in 1234",
               "PayPal (user@example.com)", "Bank Transfer"]
    return random.choice(methods)


@tool
def get_recent_tickets(customer_id: str) -> list[dict[str, Any]]:
    """
    Retrieve the 5 most recent support tickets submitted by a customer.
    Use this to understand the customer's support history and detect
    patterns like repeated issues or ongoing problems.
    """
    from app.database import get_recent_tickets_by_customer

    try:
        tickets = get_recent_tickets_by_customer(int(customer_id), limit=5)
        return [
            {
                "ticket_id": t.id,
                "subject": t.subject,
                "status": t.status.value,
                "priority": t.priority.value,
                "created_at": t.created_at.strftime("%Y-%m-%d"),
            }
            for t in tickets
        ]
    except Exception as exc:
        logger.error("get_recent_tickets error: %s", exc)
        return [{"error": str(exc)}]


@tool
def update_ticket_status_tool(ticket_id: str, status: str) -> dict[str, Any]:
    """
    Update the status of a support ticket. Valid statuses are:
    'open', 'in_progress', 'resolved', 'closed'.
    Use this when an issue has been resolved or when you need to
    track the progress of a ticket.
    """
    from app.database import update_ticket_status
    from app.models import TicketStatus

    try:
        status_enum = TicketStatus(status.lower())
        ticket = update_ticket_status(int(ticket_id), status_enum)
        if ticket is None:
            return {"error": f"Ticket {ticket_id} not found"}
        return {
            "success": True,
            "ticket_id": ticket.id,
            "new_status": ticket.status.value,
            "updated_at": ticket.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except ValueError:
        return {"error": f"Invalid status '{status}'. Use: open, in_progress, resolved, closed"}
    except Exception as exc:
        logger.error("update_ticket_status_tool error: %s", exc)
        return {"error": str(exc)}


# ── Tool Registry ──────────────────────────────────────────────────────────────

ALL_TOOLS = [
    get_customer_profile,
    get_billing_info,
    get_recent_tickets,
    update_ticket_status_tool,
]
