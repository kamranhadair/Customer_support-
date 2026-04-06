"""
app/copilot.py — The Copilot Orchestrator.

Pipeline for a single ticket:
  1. Load ticket + customer from DB
  2. Search Mem0 for relevant customer memories
  3. Search ChromaDB knowledge base (RAG)
  4. Execute CRM/billing LangChain tool calls
  5. Assemble context → build prompt
  6. Call ChatGroq LLM to generate draft
  7. Save draft to DB
  8. Store interaction in Mem0 memory
  9. Return CopilotResponse
"""
import json
import logging
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_groq import ChatGroq

from app.config import get_settings
from app.database import get_customer, get_ticket, save_draft
from app.memory import add_customer_memory, search_customer_memory
from app.models import ContextBundle, CopilotResponse, KBResult
from app.rag import search_knowledge_base
from app.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Customer Support Copilot for a SaaS company.
Your job is to help support agents by drafting a professional, empathetic, and accurate
response to a customer ticket.

You will be given:
- The customer's ticket (subject and description)
- Retrieved memories from previous interactions with this customer
- Relevant knowledge base excerpts
- CRM data (customer profile, plan, account health)
- Billing information
- Recent support ticket history

Guidelines for your draft:
1. Be warm, professional, and empathetic — start by acknowledging the customer's issue.
2. Use the knowledge base to provide accurate, specific solutions or information.
3. Cross-reference the customer's plan and billing data to give plan-specific responses.
4. Reference past interactions if relevant (e.g., "I see you contacted us last week about...").
5. Provide clear, numbered steps for any troubleshooting steps.
6. End with an offer to help further and include the support email if needed.
7. Keep the response concise but complete — ideally under 300 words.
8. Do NOT fabricate information not present in the context.
9. Address the customer by their first name.

Output ONLY the draft response text — no preamble, no meta-commentary."""


# ── Tool Execution ─────────────────────────────────────────────────────────────


def _execute_tools(tool_calls: list[dict], tool_map: dict) -> list[dict]:
    """Execute a list of tool calls and return ToolMessage-ready results."""
    results = []
    for call in tool_calls:
        name = call.get("name", "")
        args = call.get("args", {})
        call_id = call.get("id", "unknown")
        tool_fn = tool_map.get(name)
        if tool_fn is None:
            content = json.dumps({"error": f"Tool '{name}' not found"})
        else:
            try:
                raw = tool_fn.invoke(args)
                content = json.dumps(raw) if not isinstance(raw, str) else raw
            except Exception as exc:
                content = json.dumps({"error": str(exc)})
        results.append({"id": call_id, "name": name, "content": content})
    return results


# ── Context Gathering ──────────────────────────────────────────────────────────


def _gather_tool_context(customer_id: int, ticket_description: str) -> dict[str, Any]:
    """
    Use the LLM with bound tools to perform CRM/billing lookups.
    Returns a dict with crm_data, billing_data, and recent_tickets populated.
    """
    settings = get_settings()
    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
    )
    tool_map = {t.name: t for t in ALL_TOOLS}
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    messages = [
        SystemMessage(
            content=(
                "You are a data-gathering assistant. Your ONLY job is to call the "
                "available tools to collect all relevant information about the customer. "
                "Call get_customer_profile, get_billing_info, and get_recent_tickets for "
                f"customer_id={customer_id}. Do not provide any text explanation."
            )
        ),
        HumanMessage(
            content=(
                f"Gather all available data for customer_id={customer_id}. "
                f"Their ticket says: {ticket_description[:200]}"
            )
        ),
    ]

    context_data: dict[str, Any] = {
        "crm_data": {},
        "billing_data": {},
        "recent_tickets": [],
    }

    # Agentic loop — keep calling tools until the LLM is done
    max_iterations = 5
    for _ in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break  # LLM finished calling tools

        tool_results = _execute_tools(response.tool_calls, tool_map)
        for result in tool_results:
            # Parse each tool result into the right key
            try:
                data = json.loads(result["content"])
            except json.JSONDecodeError:
                data = result["content"]

            name = result["name"]
            if name == "get_customer_profile":
                context_data["crm_data"] = data
            elif name == "get_billing_info":
                context_data["billing_data"] = data
            elif name == "get_recent_tickets":
                context_data["recent_tickets"] = data if isinstance(data, list) else []

            messages.append(
                ToolMessage(content=result["content"], tool_call_id=result["id"])
            )

    return context_data


# ── Prompt Assembly ────────────────────────────────────────────────────────────


def _build_human_prompt(
    ticket_subject: str,
    ticket_description: str,
    customer_name: str,
    memories: list[str],
    kb_results: list[dict],
    crm_data: dict,
    billing_data: dict,
    recent_tickets: list[dict],
) -> str:
    sections = []

    sections.append(f"## Ticket\n**Subject:** {ticket_subject}\n**Description:**\n{ticket_description}")

    sections.append(f"## Customer\n**Name:** {customer_name}\n**Plan:** {crm_data.get('plan', 'unknown')}\n"
                    f"**Company:** {crm_data.get('company', 'N/A')}\n"
                    f"**Account Health:** {crm_data.get('account_health', 'N/A')}")

    if memories:
        mem_text = "\n".join(f"- {m}" for m in memories)
        sections.append(f"## Previous Interaction Memories\n{mem_text}")
    else:
        sections.append("## Previous Interaction Memories\n(No previous memories found for this customer)")

    if kb_results:
        kb_text = ""
        for i, r in enumerate(kb_results, 1):
            kb_text += f"\n### KB Source {i}: {r.get('source', 'unknown')} (score: {r.get('score', 'N/A')})\n{r.get('content', '')}\n"
        sections.append(f"## Knowledge Base Excerpts{kb_text}")
    else:
        sections.append("## Knowledge Base Excerpts\n(No relevant KB articles found)")

    if billing_data and not billing_data.get("error"):
        sections.append(
            f"## Billing Summary\n"
            f"- Monthly amount: ${billing_data.get('monthly_amount_usd', 0):.2f}\n"
            f"- Next renewal: {billing_data.get('next_renewal_date', 'N/A')}\n"
            f"- Payment method: {billing_data.get('payment_method', 'N/A')}\n"
            f"- Outstanding balance: ${billing_data.get('outstanding_balance_usd', 0):.2f}"
        )

    if recent_tickets and isinstance(recent_tickets, list) and not (
        len(recent_tickets) == 1 and "error" in recent_tickets[0]
    ):
        ticket_lines = "\n".join(
            f"- [{t.get('status', '?')}] {t.get('subject', '?')} ({t.get('created_at', '?')})"
            for t in recent_tickets[:5]
            if isinstance(t, dict)
        )
        sections.append(f"## Recent Support History\n{ticket_lines}")

    sections.append(
        "## Your Task\nWrite a professional draft response to this support ticket. "
        "Use the context above to personalise the response and provide accurate information."
    )

    return "\n\n".join(sections)


# ── Main Orchestrator ──────────────────────────────────────────────────────────


def generate_draft(ticket_id: int) -> CopilotResponse:
    """
    Main copilot entry point. Given a ticket_id, gathers all context
    and generates an AI-drafted response.
    """
    settings = get_settings()

    # 1. Load ticket and customer
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} not found")

    customer = get_customer(ticket.customer_id)
    if customer is None:
        raise ValueError(f"Customer {ticket.customer_id} not found")

    logger.info(
        "Generating draft for ticket=%d, customer=%d (%s)",
        ticket_id, customer.id, customer.name,
    )

    # 2. Retrieve Mem0 customer memories
    query = f"{ticket.subject} {ticket.description}"
    memories = search_customer_memory(customer.id, query, limit=5)

    # 3. RAG — search knowledge base
    kb_hits = search_knowledge_base(query, n_results=3)
    kb_results_models = [
        KBResult(
            content=h["content"],
            source=h["source"],
            score=h.get("score"),
        )
        for h in kb_hits
    ]

    # 4. LangChain tool calls — CRM/billing lookups
    tool_context = _gather_tool_context(customer.id, ticket.description)

    # 5. Build prompt
    human_prompt = _build_human_prompt(
        ticket_subject=ticket.subject,
        ticket_description=ticket.description,
        customer_name=customer.name,
        memories=memories,
        kb_results=kb_hits,
        crm_data=tool_context["crm_data"],
        billing_data=tool_context["billing_data"],
        recent_tickets=tool_context["recent_tickets"],
    )

    # 6. Generate draft with ChatGroq
    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0.3,
        max_tokens=1024,
    )
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ])
    draft_text = response.content.strip()

    # 7. Save draft to DB
    context_snapshot = {
        "memories": memories,
        "kb_results": [{"content": h["content"], "source": h["source"], "score": h.get("score")} for h in kb_hits],
        "crm_data": tool_context["crm_data"],
        "billing_data": tool_context["billing_data"],
        "recent_tickets": tool_context["recent_tickets"],
    }
    saved_draft = save_draft(ticket_id, draft_text, context_snapshot)

    # 8. Add to Mem0 memory — capture this interaction
    interaction_summary = (
        f"Customer contacted support about: {ticket.subject}. "
        f"Issue details: {ticket.description[:300]}"
    )
    add_customer_memory(customer.id, interaction_summary)

    logger.info("Draft generated and saved (draft_id=%d)", saved_draft.id)

    # 9. Return structured response
    return CopilotResponse(
        ticket_id=ticket_id,
        draft_text=draft_text,
        draft_id=saved_draft.id,
        context=ContextBundle(
            customer_memories=memories,
            kb_results=kb_results_models,
            crm_data=tool_context["crm_data"],
            billing_data=tool_context["billing_data"],
            recent_tickets=tool_context["recent_tickets"],
        ),
    )
