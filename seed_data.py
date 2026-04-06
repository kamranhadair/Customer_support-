"""
seed_data.py — Seed the database with sample customers and tickets,
and ingest knowledge base documents into ChromaDB.

Run with: python seed_data.py
"""
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_db, create_customer, create_ticket
from app.models import CustomerCreate, CustomerPlan, TicketCreate, TicketPriority
from app.rag import ingest_documents

# ── Sample Customers ───────────────────────────────────────────────────────────

CUSTOMERS = [
    CustomerCreate(
        name="Alice Johnson",
        email="alice@acmecorp.com",
        plan=CustomerPlan.PRO,
        company="Acme Corp",
        phone="+1-555-0101",
    ),
    CustomerCreate(
        name="Bob Martinez",
        email="bob@startupxyz.io",
        plan=CustomerPlan.STARTER,
        company="Startup XYZ",
        phone="+1-555-0202",
    ),
    CustomerCreate(
        name="Carol White",
        email="carol@freelance.dev",
        plan=CustomerPlan.FREE,
        company=None,
        phone=None,
    ),
    CustomerCreate(
        name="David Kim",
        email="david.kim@enterprise.com",
        plan=CustomerPlan.ENTERPRISE,
        company="Enterprise Solutions Ltd",
        phone="+1-555-0404",
    ),
    CustomerCreate(
        name="Emma Davis",
        email="emma@techco.net",
        plan=CustomerPlan.STARTER,
        company="TechCo",
        phone="+1-555-0505",
    ),
]

# ── Sample Tickets (by customer index 0-based) ─────────────────────────────────

TICKETS = [
    # Alice (Pro) — billing dispute
    TicketCreate(
        customer_id=1,
        subject="Unexpected charge on my account",
        description=(
            "Hi, I was charged $99 on March 15th but I thought I was on the Starter plan at $29/mo. "
            "I did not authorize a plan upgrade. Please explain this charge and issue a refund if it was an error. "
            "This is very urgent as my team relies on this service and this has impacted our budget."
        ),
        priority=TicketPriority.HIGH,
    ),
    # Alice (Pro) — login issue
    TicketCreate(
        customer_id=1,
        subject="Cannot log in after password change",
        description=(
            "I changed my password last night and now I cannot log in. "
            "I keep getting 'Invalid credentials' even though I type the new password carefully. "
            "I have tried resetting my password twice but still no luck. Please help."
        ),
        priority=TicketPriority.URGENT,
    ),
    # Bob (Starter) — refund request
    TicketCreate(
        customer_id=2,
        subject="Request for refund — cancelled subscription",
        description=(
            "I cancelled my Starter subscription yesterday because I am moving to a different tool. "
            "I would like a prorated refund for the remaining 18 days of this billing cycle. "
            "My last payment was $29 on March 28. Can you process this please?"
        ),
        priority=TicketPriority.MEDIUM,
    ),
    # Carol (Free) — upgrade question
    TicketCreate(
        customer_id=3,
        subject="How do I upgrade from Free to Pro?",
        description=(
            "I am currently on the Free plan and hitting the 500 API call limit every week. "
            "I want to upgrade to Pro but I have some questions: "
            "1) Can I pay annually? "
            "2) Is there a discount for non-profits? "
            "3) What happens to my existing data when I upgrade?"
        ),
        priority=TicketPriority.LOW,
    ),
    # David (Enterprise) — team management
    TicketCreate(
        customer_id=4,
        subject="Cannot add new team member — invite email not arriving",
        description=(
            "We are trying to onboard a new team member (sarah@enterprise.com) but she is not receiving "
            "the invitation email. I have sent the invite 3 times over the past 2 days. "
            "We have checked her spam folder. Our email domain does not block external emails. "
            "This is blocking a critical project deadline."
        ),
        priority=TicketPriority.HIGH,
    ),
    # Emma (Starter) — API error
    TicketCreate(
        customer_id=5,
        subject="Getting 429 errors on API — hit rate limit",
        description=(
            "My integration keeps returning 429 Too Many Requests errors since this morning. "
            "I am on the Starter plan. I don't think I am exceeding 10,000 calls/month — "
            "it's only the 6th of the month. Is there a daily or hourly rate limit I am not aware of? "
            "My application is broken and customers are affected."
        ),
        priority=TicketPriority.URGENT,
    ),
]


def main():
    print("🌱 Seeding Customer Support Agent database...\n")

    # Initialize schema
    init_db()
    print("✅ Database schema initialized")

    # Create customers
    print("\n📋 Creating customers...")
    created_customers = []
    for c_data in CUSTOMERS:
        try:
            customer = create_customer(c_data)
            created_customers.append(customer)
            print(f"   ✅ [{customer.id}] {customer.name} ({customer.plan.value}) — {customer.email}")
        except Exception as e:
            print(f"   ⚠️  Skipped {c_data.email}: {e}")

    # Create tickets
    print("\n🎫 Creating tickets...")
    for t_data in TICKETS:
        try:
            ticket = create_ticket(t_data)
            print(f"   ✅ [{ticket.id}] [{ticket.priority.value.upper()}] {ticket.subject[:60]}")
        except Exception as e:
            print(f"   ⚠️  Skipped ticket '{t_data.subject[:40]}': {e}")

    # Ingest knowledge base
    print("\n📚 Ingesting knowledge base documents into ChromaDB...")
    chunks = ingest_documents()
    print(f"   ✅ Ingested {chunks} chunks from knowledge_base/docs/")

    print("\n🎉 Seeding complete!")
    print("\nNext steps:")
    print("  1. Set your GROQ_API_KEY in .env")
    print("  2. Run:  make run-api       (FastAPI on :8000)")
    print("  3. Run:  make run-dashboard (Streamlit on :8501)")
    print("  4. API docs: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
