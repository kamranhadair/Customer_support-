"""
dashboard/app.py — Streamlit Support Agent Dashboard.

A professional, modern support ticket management interface with AI copilot integration.
"""
import json
import os

import requests
import streamlit as st

# ── Configuration ──────────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Support Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main background */
    .main { background-color: #0f1117; }
    .stApp { background-color: #0f1117; color: #e2e8f0; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1f2e 0%, #151b2d 100%);
        border-right: 1px solid #2d3748;
    }

    /* Ticket card */
    .ticket-card {
        background: #1e2535;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .ticket-card:hover { border-color: #6366f1; transform: translateY(-1px); }
    .ticket-card.selected { border-color: #6366f1; background: #252d45; }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-open      { background: #1e3a5f; color: #60a5fa; }
    .badge-progress  { background: #3d2e00; color: #fbbf24; }
    .badge-resolved  { background: #1a3328; color: #34d399; }
    .badge-closed    { background: #2d2d2d; color: #9ca3af; }

    /* Priority badges */
    .prio-urgent  { background: #3d1a1a; color: #f87171; }
    .prio-high    { background: #3d2a1a; color: #fb923c; }
    .prio-medium  { background: #2e2a1a; color: #facc15; }
    .prio-low     { background: #1a2e1a; color: #86efac; }

    /* Draft box */
    .draft-box {
        background: #1a2035;
        border: 1px solid #3b4a6b;
        border-radius: 12px;
        padding: 24px;
        line-height: 1.7;
    }

    /* Context panel */
    .context-section {
        background: #161d2e;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 10px;
        font-size: 13px;
    }

    /* Metric cards */
    .metric-card {
        background: #1e2535;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #6366f1; }
    .metric-label { font-size: 12px; color: #94a3b8; margin-top: 4px; }

    /* Button overrides */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        transform: translateY(-1px);
    }

    /* Expander */
    .streamlit-expanderHeader { font-size: 13px; color: #94a3b8; }

    /* Divider */
    hr { border-color: #2d3748; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── API Helpers ────────────────────────────────────────────────────────────────


def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the backend API. Is the FastAPI server running?")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path: str, data: dict):
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=data, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the backend API. Is the FastAPI server running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error {e.response.status_code}: {e.response.json().get('detail', str(e))}")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_patch(path: str, data: dict):
    try:
        r = requests.patch(f"{BACKEND_URL}{path}", json=data, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


# ── Badge Helpers ──────────────────────────────────────────────────────────────


def status_badge(status: str) -> str:
    cls = {
        "open": "badge-open",
        "in_progress": "badge-progress",
        "resolved": "badge-resolved",
        "closed": "badge-closed",
    }.get(status, "badge-open")
    label = status.replace("_", " ")
    return f'<span class="badge {cls}">{label}</span>'


def priority_badge(prio: str) -> str:
    cls = f"prio-{prio}"
    icons = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    return f'<span class="badge {cls}">{icons.get(prio, "")} {prio}</span>'


# ── Session State ──────────────────────────────────────────────────────────────


if "selected_ticket_id" not in st.session_state:
    st.session_state.selected_ticket_id = None
if "generated_draft" not in st.session_state:
    st.session_state.generated_draft = None


# ── Sidebar ────────────────────────────────────────────────────────────────────


with st.sidebar:
    st.markdown("### 🤖 Support Copilot")
    st.caption("AI-powered ticket assistant")
    st.divider()

    # Stats
    customers = api_get("/customers/") or []
    tickets = api_get("/tickets/") or []

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{len(customers)}</div>'
            '<div class="metric-label">Customers</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        open_count = sum(1 for t in tickets if t["status"] == "open")
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{open_count}</div>'
            '<div class="metric-label">Open</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    # Filters
    st.markdown("**Filter Tickets**")
    status_filter = st.selectbox(
        "Status",
        options=["All", "open", "in_progress", "resolved", "closed"],
        index=0,
    )
    priority_filter = st.selectbox(
        "Priority",
        options=["All", "urgent", "high", "medium", "low"],
        index=0,
    )

    st.divider()
    st.caption(f"🔗 API: {BACKEND_URL}")


# ── Main Panel ─────────────────────────────────────────────────────────────────


# Header
st.markdown(
    """
    <div style="padding: 20px 0 10px 0;">
        <h1 style="font-size:28px; font-weight:700; color:#e2e8f0; margin:0;">
            🎫 Support Ticket Dashboard
        </h1>
        <p style="color:#94a3b8; font-size:14px; margin-top:6px;">
            AI-powered copilot with customer memory, knowledge base search, and CRM lookups
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["📋 Tickets", "👥 Customers", "➕ New Ticket"])

# ─────────────────────────────────────── TAB 1: TICKETS ────────────────────────


with tab1:
    col_list, col_detail = st.columns([1, 1.6], gap="large")

    with col_list:
        st.markdown("#### Ticket Queue")

        # Apply filters
        params = {}
        if status_filter != "All":
            params["status"] = status_filter
        filtered_tickets = api_get("/tickets/", params=params) or []
        if priority_filter != "All":
            filtered_tickets = [t for t in filtered_tickets if t["priority"] == priority_filter]

        if not filtered_tickets:
            st.info("No tickets match the current filters.")
        else:
            for ticket in filtered_tickets:
                is_selected = st.session_state.selected_ticket_id == ticket["id"]
                card_class = "ticket-card selected" if is_selected else "ticket-card"

                # Find customer name
                customer = next((c for c in customers if c["id"] == ticket["customer_id"]), None)
                cust_name = customer["name"] if customer else f"Customer #{ticket['customer_id']}"

                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:6px;">
                            <span style="font-weight:600; font-size:14px; color:#e2e8f0;">#{ticket['id']} {ticket['subject'][:45]}{'...' if len(ticket['subject'])>45 else ''}</span>
                            {priority_badge(ticket['priority'])}
                        </div>
                        <div style="display:flex; gap:8px; align-items:center;">
                            {status_badge(ticket['status'])}
                            <span style="font-size:12px; color:#64748b;">👤 {cust_name}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"Open #{ticket['id']}", key=f"btn_{ticket['id']}", use_container_width=True):
                    st.session_state.selected_ticket_id = ticket["id"]
                    st.session_state.generated_draft = None
                    st.rerun()

    with col_detail:
        if st.session_state.selected_ticket_id is None:
            st.markdown(
                """
                <div style="text-align:center; padding:60px 0; color:#475569;">
                    <div style="font-size:48px;">📬</div>
                    <div style="font-size:16px; margin-top:12px;">Select a ticket to view details</div>
                    <div style="font-size:13px; margin-top:6px; color:#334155;">Click any ticket on the left to get started</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            ticket_id = st.session_state.selected_ticket_id
            ticket = api_get(f"/tickets/{ticket_id}")
            if ticket:
                customer = api_get(f"/customers/{ticket['customer_id']}")

                # Ticket header
                st.markdown(
                    f"""
                    <div style="margin-bottom:16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h3 style="margin:0; color:#e2e8f0; font-size:18px;">#{ticket['id']} {ticket['subject']}</h3>
                            <div style="display:flex; gap:8px;">
                                {status_badge(ticket['status'])}
                                {priority_badge(ticket['priority'])}
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Customer info
                if customer:
                    plan_colors = {"free": "#64748b", "starter": "#3b82f6", "pro": "#8b5cf6", "enterprise": "#f59e0b"}
                    plan_color = plan_colors.get(customer["plan"], "#64748b")
                    st.markdown(
                        f"""
                        <div class="context-section" style="border-left: 3px solid {plan_color};">
                            <span style="font-weight:600; color:#94a3b8;">👤 CUSTOMER</span><br>
                            <span style="font-size:15px; font-weight:600; color:#e2e8f0;">{customer['name']}</span>
                            &nbsp;<span style="color:#94a3b8;">{customer['email']}</span><br>
                            <span style="font-size:12px; color:{plan_color}; font-weight:600;">
                                ⬆ {customer['plan'].upper()} PLAN
                            </span>
                            &nbsp;&nbsp;<span style="font-size:12px; color:#64748b;">{customer.get('company') or 'Individual'}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Ticket description
                st.markdown("**📝 Issue Description**")
                st.markdown(
                    f'<div class="context-section" style="line-height:1.6;">{ticket["description"]}</div>',
                    unsafe_allow_html=True,
                )

                # Status update
                with st.expander("🔧 Update Ticket Status"):
                    new_status = st.selectbox(
                        "New Status",
                        options=["open", "in_progress", "resolved", "closed"],
                        index=["open", "in_progress", "resolved", "closed"].index(ticket["status"]),
                        key=f"status_sel_{ticket_id}",
                    )
                    if st.button("✅ Update Status", key=f"update_status_{ticket_id}"):
                        result = api_patch(f"/tickets/{ticket_id}/status", {"status": new_status})
                        if result:
                            st.success(f"Status updated to **{new_status}**")
                            st.rerun()

                st.divider()

                # AI Draft Generator
                st.markdown("### 🤖 AI Copilot")
                if st.button(
                    "⚡ Generate AI Draft Response",
                    key=f"gen_draft_{ticket_id}",
                    use_container_width=True,
                ):
                    with st.spinner("🧠 Gathering context (memories, KB, CRM, billing)..."):
                        result = api_post("/copilot/generate", {"ticket_id": ticket_id})
                        if result:
                            st.session_state.generated_draft = result

                # Display draft
                if st.session_state.generated_draft and st.session_state.generated_draft.get("ticket_id") == ticket_id:
                    draft_data = st.session_state.generated_draft

                    st.success(f"✅ Draft generated (ID: {draft_data.get('draft_id', 'N/A')})")

                    # Draft text
                    st.markdown("**📨 Draft Response**")
                    draft_text = st.text_area(
                        label="Edit before sending",
                        value=draft_data["draft_text"],
                        height=220,
                        key=f"draft_text_{ticket_id}",
                        label_visibility="collapsed",
                    )

                    col_copy, col_approve = st.columns([1, 1])
                    with col_copy:
                        if st.button("📋 Copy to Clipboard", use_container_width=True):
                            st.write("_Draft copied!_")
                    with col_approve:
                        if st.button("✅ Mark as Resolved", use_container_width=True):
                            api_patch(f"/tickets/{ticket_id}/status", {"status": "resolved"})
                            st.success("Ticket marked as resolved!")
                            st.rerun()

                    # Context accordion
                    st.markdown("**🔍 Context Used by Copilot**")
                    context = draft_data.get("context", {})

                    with st.expander("🧠 Customer Memories (Mem0)"):
                        memories = context.get("customer_memories", [])
                        if memories:
                            for m in memories:
                                st.markdown(f"- {m}")
                        else:
                            st.caption("No previous memories found for this customer.")

                    with st.expander("📚 Knowledge Base Results (RAG)"):
                        kb = context.get("kb_results", [])
                        if kb:
                            for item in kb:
                                score = item.get("score", "")
                                st.markdown(
                                    f"**Source:** `{item.get('source', '?')}` "
                                    f"| **Score:** {score:.3f}" if isinstance(score, float)
                                    else f"**Source:** `{item.get('source', '?')}`"
                                )
                                st.markdown(
                                    f'<div class="context-section" style="font-size:12px;">{item.get("content","")[:400]}...</div>',
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.caption("No KB results found.")

                    with st.expander("👤 CRM Data"):
                        crm = context.get("crm_data", {})
                        if crm and not crm.get("error"):
                            for k, v in crm.items():
                                if k != "customer_id":
                                    st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                        else:
                            st.caption(crm.get("error", "No CRM data available."))

                    with st.expander("💳 Billing Data"):
                        billing = context.get("billing_data", {})
                        if billing and not billing.get("error"):
                            for k, v in billing.items():
                                if k != "customer_id":
                                    st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                        else:
                            st.caption(billing.get("error", "No billing data available."))

                    with st.expander("🎫 Recent Ticket History"):
                        recent = context.get("recent_tickets", [])
                        if recent and isinstance(recent, list) and not (
                            len(recent) == 1 and "error" in recent[0]
                        ):
                            for t in recent:
                                if isinstance(t, dict):
                                    st.markdown(
                                        f"- **[{t.get('status', '?').upper()}]** "
                                        f"{t.get('subject', '?')} "
                                        f"_(_{t.get('priority', '?')}_, {t.get('created_at', '?')})_"
                                    )
                        else:
                            st.caption("No recent ticket history.")


# ─────────────────────────────────────── TAB 2: CUSTOMERS ─────────────────────


with tab2:
    st.markdown("#### Customer Directory")

    customers_data = api_get("/customers/") or []
    if not customers_data:
        st.info("No customers found. Run `make seed` to add sample data.")
    else:
        plan_icon = {"free": "⚪", "starter": "🔵", "pro": "🟣", "enterprise": "🟡"}
        for c in customers_data:
            with st.container():
                col_info, col_plan = st.columns([3, 1])
                with col_info:
                    st.markdown(
                        f"**{c['name']}** &nbsp; `{c['email']}` &nbsp; "
                        f"{c.get('company', 'Individual') or 'Individual'}"
                    )
                with col_plan:
                    icon = plan_icon.get(c["plan"], "⚪")
                    st.markdown(f"{icon} **{c['plan'].upper()}**")
                st.divider()


# ─────────────────────────────────────── TAB 3: NEW TICKET ────────────────────


with tab3:
    st.markdown("#### Create a New Support Ticket")

    with st.form("new_ticket_form"):
        customers_data = api_get("/customers/") or []
        if not customers_data:
            st.warning("No customers in the database. Run `make seed` first.")
            st.stop()

        customer_options = {f"#{c['id']} {c['name']} ({c['email']})": c["id"] for c in customers_data}
        selected_customer_label = st.selectbox("Customer *", options=list(customer_options.keys()))
        selected_customer_id = customer_options[selected_customer_label]

        subject = st.text_input("Subject *", placeholder="Briefly describe the issue")
        description = st.text_area("Description *", placeholder="Provide full details...", height=150)

        col_pri, col_submit = st.columns([1, 2])
        with col_pri:
            priority = st.selectbox("Priority", options=["low", "medium", "high", "urgent"])
        with col_submit:
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🎫 Create Ticket", use_container_width=True)

        if submitted:
            if not subject.strip() or not description.strip():
                st.error("Subject and Description are required.")
            else:
                new_ticket = api_post(
                    "/tickets/",
                    {
                        "customer_id": selected_customer_id,
                        "subject": subject,
                        "description": description,
                        "priority": priority,
                    },
                )
                if new_ticket:
                    st.success(f"✅ Ticket #{new_ticket['id']} created successfully!")
                    st.session_state.selected_ticket_id = new_ticket["id"]
                    st.rerun()
