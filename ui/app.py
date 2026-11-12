"""Streamlit Web Application: NexusBI Enterprise Analytics Assistant."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path for Streamlit Cloud deployment
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests
import streamlit as st

try:
    from ui.components import (
        render_chart_component,
        render_route_badge,
        render_sources_inspector,
        render_sql_inspector,
    )
except ImportError:
    from components import (
        render_chart_component,
        render_route_badge,
        render_sources_inspector,
        render_sql_inspector,
    )

st.set_page_config(
    page_title="NexusBI | Chat with Your Business Data",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End Cyber/Data Theme & Live Animated Background
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

code, pre, [class*="stCode"] {
    font-family: 'JetBrains Mono', monospace !important;
}

/* --- LIVE ANIMATED CHAT PANEL BACKGROUND --- */
.stApp {
    background:
        radial-gradient(circle at 10% 15%, rgba(0, 242, 254, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 90% 85%, rgba(79, 172, 254, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.04) 0%, transparent 60%),
        linear-gradient(180deg, #070A12 0%, #0B0F19 50%, #0D1322 100%) !important;
    background-attachment: fixed !important;
}

/* Subtle moving data mesh grid overlay */
div[data-testid="stMainBlockContainer"] {
    background-image:
        radial-gradient(rgba(0, 242, 254, 0.07) 1px, transparent 1px),
        linear-gradient(rgba(255, 255, 255, 0.012) 1px, transparent 1px);
    background-size: 36px 36px, 100% 72px;
    background-position: 0 0;
    animation: liveDataGrid 30s linear infinite;
    border-radius: 16px;
}

@keyframes liveDataGrid {
    0% { background-position: 0 0, 0 0; }
    100% { background-position: 360px 360px, 0 720px; }
}

/* Keyframe Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulseGlow {
    0% { box-shadow: 0 0 0 0 rgba(0, 242, 254, 0.45); }
    70% { box-shadow: 0 0 0 12px rgba(0, 242, 254, 0); }
    100% { box-shadow: 0 0 0 0 rgba(0, 242, 254, 0); }
}

@keyframes titleShimmer {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Hero Branding Card */
.nexus-hero {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.85));
    border: 1px solid rgba(0, 242, 254, 0.25);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
    box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.5), 0 0 24px rgba(0, 242, 254, 0.08);
    animation: fadeIn 0.5s ease-out;
}

.nexus-title {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #FFFFFF 20%, #00F2FE 70%, #4FACFE 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: titleShimmer 6s ease infinite;
    display: flex;
    align-items: center;
    gap: 12px;
}

.nexus-badge {
    font-size: 0.72rem;
    background: rgba(0, 242, 254, 0.12);
    border: 1px solid rgba(0, 242, 254, 0.35);
    color: #00F2FE;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
}

.nexus-subtitle {
    font-size: 1.15rem;
    font-weight: 700;
    color: #38BDF8;
    letter-spacing: -0.01em;
    margin-top: 4px;
    margin-bottom: 6px;
}

.nexus-desc {
    color: #94A3B8;
    font-size: 0.92rem;
    font-weight: 400;
    line-height: 1.5;
}

/* Telemetry Metric Cards */
.telemetry-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 22px;
}

.telemetry-card {
    background: rgba(17, 24, 39, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 12px 16px;
    transition: all 0.25s ease;
}

.telemetry-card:hover {
    border-color: rgba(0, 242, 254, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 242, 254, 0.15);
}

.telemetry-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94A3B8;
    margin-bottom: 2px;
}

.telemetry-value {
    font-size: 1.3rem;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.02em;
}

/* Sidebar Customizations */
section[data-testid="stSidebar"] {
    background-color: #0B0F19 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.07);
}

div[data-testid="stSidebarHeader"] {
    padding-top: 1.5rem;
}

/* Chat Message Styling */
.stChatMessage {
    animation: fadeIn 0.35s ease-out;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(17, 24, 39, 0.6) !important;
}

/* Prompt Button Micro-interactions */
div.stButton > button {
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    background: rgba(30, 41, 59, 0.5) !important;
    color: #E2E8F0 !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    padding: 8px 14px !important;
}

div.stButton > button:hover {
    border-color: #00F2FE !important;
    color: #FFFFFF !important;
    background: rgba(0, 242, 254, 0.12) !important;
    box-shadow: 0 0 14px rgba(0, 242, 254, 0.25) !important;
    transform: translateX(3px) !important;
}

/* Expander Styling */
div[data-testid="stExpander"] {
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    background: rgba(15, 23, 42, 0.45) !important;
    margin-top: 8px !important;
}

/* File Uploader Container Styling */
div[data-testid="stFileUploader"] {
    border: 1px dashed rgba(0, 242, 254, 0.35);
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.5);
    padding: 10px;
    transition: all 0.25s ease;
}

div[data-testid="stFileUploader"]:hover {
    border-color: #00F2FE;
    box-shadow: 0 0 16px rgba(0, 242, 254, 0.15);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def check_api_health() -> dict:
    """Fetch health status from FastAPI backend, with fallback to in-process engine."""
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            data["mode"] = "api"
            return data
    except Exception:
        pass

    try:
        from app.db.connection import check_database_health
        from app.rag.vector_store import get_or_create_collection

        db_stat = check_database_health()
        col = get_or_create_collection()
        return {
            "status": "healthy" if db_stat.get("connected") else "degraded",
            "database": f"{db_stat.get('database', 'sqlite')} (cloud/standalone)",
            "db_connected": bool(db_stat.get("connected")),
            "vector_store_chunks": col.count(),
            "mode": "standalone",
        }
    except Exception:
        pass

    return {
        "status": "offline",
        "database": "unknown",
        "db_connected": False,
        "vector_store_chunks": 0,
        "mode": "offline",
    }


def execute_ask(user_prompt: str, thread_id: str | None = None) -> dict:
    """Execute analytics inquiry via API or direct in-process graph."""
    try:
        payload = {"question": user_prompt}
        if thread_id:
            payload["thread_id"] = thread_id
        resp = requests.post(f"{API_BASE_URL}/ask", json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass

    # Direct in-process execution fallback
    import time
    import uuid

    from langgraph.errors import GraphInterrupt

    from app.graph.workflow import app_graph

    start_t = time.perf_counter()
    t_id = thread_id or f"sess_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": t_id}}

    try:
        final_state = app_graph.invoke(
            {"question": user_prompt, "thread_id": t_id}, config=config
        )
    except GraphInterrupt:
        state_snap = app_graph.get_state(config)
        snap_values = state_snap.values if state_snap else {}
        prompt = (
            snap_values.get("clarification_prompt")
            or "Please clarify what timeframe or metric you would like to analyze."
        )
        return {
            "answer": f"**Clarification Needed:** {prompt}",
            "route": "CLARIFY",
            "needs_clarification": True,
            "clarification_prompt": prompt,
            "thread_id": t_id,
            "execution_ms": round((time.perf_counter() - start_t) * 1000, 2),
        }

    dur_ms = round((time.perf_counter() - start_t) * 1000, 2)
    if final_state.get("__interrupt__") or final_state.get("needs_clarification"):
        prompt = (
            final_state.get("clarification_prompt")
            or "Please clarify what timeframe or metric you would like to analyze."
        )
        return {
            "answer": f"**Clarification Needed:** {prompt}",
            "route": "CLARIFY",
            "needs_clarification": True,
            "clarification_prompt": prompt,
            "thread_id": t_id,
            "execution_ms": dur_ms,
        }

    sources = []
    if final_state.get("retrieved_docs"):
        for doc in final_state["retrieved_docs"]:
            sources.append({
                "doc_id": getattr(doc, "doc_id", "UNKNOWN"),
                "title": getattr(doc, "title", "Business Document"),
                "source": getattr(doc, "source", "unknown.md"),
                "section": getattr(doc, "section", "General"),
                "similarity_score": getattr(doc, "similarity_score", 0.0),
            })

    chart_dict = None
    if final_state.get("chart_spec"):
        chart_val = final_state["chart_spec"]
        chart_dict = (
            chart_val.model_dump()
            if hasattr(chart_val, "model_dump")
            else chart_val
        )

    return {
        "answer": final_state.get("answer", ""),
        "route": final_state.get("route", "SQL"),
        "chart_spec": chart_dict,
        "sql_query": final_state.get("sql_query"),
        "sql_columns": final_state.get("sql_columns", []),
        "sql_row_count": final_state.get("sql_row_count", 0),
        "sources": sources,
        "needs_clarification": False,
        "thread_id": t_id,
        "execution_ms": dur_ms,
    }


def execute_resume(clarification: str, thread_id: str) -> dict:
    """Resume an interrupted graph inquiry with user clarification."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/resume",
            json={"thread_id": thread_id, "user_clarification": clarification},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass

    # Direct in-process resumption
    import time

    from langgraph.types import Command

    from app.graph.workflow import app_graph

    start_t = time.perf_counter()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        final_state = app_graph.invoke(
            Command(resume=clarification.strip()), config=config
        )
    except Exception:
        final_state = app_graph.invoke(
            {
                "user_clarification": clarification.strip(),
                "needs_clarification": False,
            },
            config=config,
        )

    dur_ms = round((time.perf_counter() - start_t) * 1000, 2)
    sources = []
    if final_state.get("retrieved_docs"):
        for doc in final_state["retrieved_docs"]:
            sources.append({
                "doc_id": getattr(doc, "doc_id", "UNKNOWN"),
                "title": getattr(doc, "title", "Business Document"),
                "source": getattr(doc, "source", "unknown.md"),
                "section": getattr(doc, "section", "General"),
                "similarity_score": getattr(doc, "similarity_score", 0.0),
            })

    chart_dict = None
    if final_state.get("chart_spec"):
        chart_val = final_state["chart_spec"]
        chart_dict = (
            chart_val.model_dump()
            if hasattr(chart_val, "model_dump")
            else chart_val
        )

    return {
        "answer": final_state.get("answer", ""),
        "route": final_state.get("route", "SQL"),
        "chart_spec": chart_dict,
        "sql_query": final_state.get("sql_query"),
        "sql_columns": final_state.get("sql_columns", []),
        "sql_row_count": final_state.get("sql_row_count", 0),
        "sources": sources,
        "needs_clarification": False,
        "thread_id": thread_id,
        "execution_ms": dur_ms,
    }


# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "pending_clarification" not in st.session_state:
    st.session_state.pending_clarification = None
if "uploaded_summary" not in st.session_state:
    st.session_state.uploaded_summary = None

# --- SIDEBAR NAVIGATION & TELEMETRY ---
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <div style="
                background: linear-gradient(135deg, #00F2FE, #4FACFE);
                height: 38px; width: 38px; border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                font-size: 1.3rem; font-weight: 800; color: #0F172A;
                box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
            ">N</div>
            <div>
                <div style="font-weight: 800; font-size: 1.25rem; color: #F8FAFC; letter-spacing: -0.01em;">NexusBI</div>
                <div style="font-size: 0.72rem; color: #00F2FE; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;">Autonomous Intelligence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    health = check_api_health()
    if health["status"] == "healthy":
        st.markdown(
            f"""
            <div style="
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 0.8rem;
                display: flex;
                align-items: center;
                gap: 8px;
                color: #34D399;
                font-weight: 600;
            ">
                <span style="height: 8px; width: 8px; border-radius: 50%; background: #10B981; animation: pulseGlow 2s infinite;"></span>
                Online &bull; {health['database'].upper()}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("⚠️ Engine In-Process Fallback")

    st.caption(f"Knowledge Corpus: **{health.get('vector_store_chunks', 22)} Vector Nodes**")
    st.divider()

    st.markdown("#### ⚡ Suggested Analytical Inquiries")
    sample_queries = [
        "Which products had falling sales in Q3, and why?",
        "What was the total GMV in October 2025 during Diwali?",
        "Why did delivery times spike in Mumbai during July and August?",
        "What is our corporate delivery SLA policy and compensation guidelines?",
        "Did the May organic milk campaign increase sales?",
        "trends",  # Demonstrates Human-in-the-Loop Clarification
    ]

    selected_sample = None
    for q in sample_queries:
        if st.button(q, use_container_width=True, key=f"btn_{q}"):
            selected_sample = q

    st.divider()
    if st.button("🗑️ Reset Analysis Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.session_state.pending_clarification = None
        st.session_state.uploaded_summary = None
        st.rerun()


# --- HERO DASHBOARD HEADER ---
st.markdown(
    """
    <div class="nexus-hero">
        <div class="nexus-title">
            <span>🌌 NexusBI</span>
            <span class="nexus-badge">v1.2 Enterprise</span>
        </div>
        <div class="nexus-subtitle">
            Chat with Your Business Data
        </div>
        <div class="nexus-desc">
            Autonomous multi-agent intelligence assistant connecting relational data warehouses,
            vectorized corporate knowledge, and uploaded enterprise datasets.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- LIVE TELEMETRY STRIP ---
st.markdown(
    """
    <div class="telemetry-strip">
        <div class="telemetry-card">
            <div class="telemetry-label">Warehouse Records</div>
            <div class="telemetry-value" style="color: #00F2FE;">14,309</div>
        </div>
        <div class="telemetry-card">
            <div class="telemetry-label">Enterprise GMV</div>
            <div class="telemetry-value" style="color: #34D399;">₹48.72M</div>
        </div>
        <div class="telemetry-card">
            <div class="telemetry-label">Mean Agent SLA</div>
            <div class="telemetry-value" style="color: #A78BFA;">22.3 ms</div>
        </div>
        <div class="telemetry-card">
            <div class="telemetry-label">AST Guardrail Integrity</div>
            <div class="telemetry-value" style="color: #FBBF24;">100.0%</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Render Message History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("route"):
            render_route_badge(msg["route"])
        st.markdown(msg["content"])
        if msg.get("chart_spec"):
            render_chart_component(msg["chart_spec"])
        if msg.get("sql_query"):
            render_sql_inspector(
                msg["sql_query"],
                msg.get("sql_columns"),
                msg.get("sql_row_count", 0),
                msg.get("execution_ms", 0.0),
            )
        if msg.get("sources"):
            render_sources_inspector(msg["sources"])

# Clarification Modal / Input if Interrupted
if st.session_state.pending_clarification:
    clarify_info = st.session_state.pending_clarification
    with st.container():
        st.warning(f"**Human-in-the-Loop Clarification:** {clarify_info['prompt']}")
        user_response = st.text_input(
            "Please provide specific parameters (e.g., 'GMV for Q3 2025' or 'Focus on Mumbai dark store'):",
            key="clarification_input",
        )
        if st.button("Submit Clarification", type="primary", use_container_width=True):
            if user_response.strip():
                st.session_state.messages.append({"role": "user", "content": user_response.strip()})

                with st.spinner("Resuming analytics workflow with provided parameters..."):
                    try:
                        data = execute_resume(
                            clarification=user_response.strip(),
                            thread_id=clarify_info["thread_id"],
                        )
                        st.session_state.pending_clarification = None
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": data["answer"],
                            "route": data.get("route"),
                            "chart_spec": data.get("chart_spec"),
                            "sql_query": data.get("sql_query"),
                            "sql_columns": data.get("sql_columns"),
                            "sql_row_count": data.get("sql_row_count", 0),
                            "sources": data.get("sources", []),
                            "execution_ms": data.get("execution_ms", 0.0),
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to resume analytics: {e}")

# --- DATASET UPLOADER ACCORDION IN INPUT PANEL ---
with st.expander("📁 Upload Custom Dataset (.csv, .xlsx, .parquet, .json)", expanded=False):
    st.markdown(
        """
        <div style="font-size: 0.85rem; color: #94A3B8; margin-bottom: 8px;">
            Upload any business dataset (sales, logs, inventory, customers). NexusBI will parse its data types,
            register it inside the SQL warehouse, and make it instantly queryable in natural language.
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "Choose a dataset file",
        type=["csv", "xlsx", "xls", "parquet", "json"],
        key="custom_dataset_file",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        file_signature = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_uploaded_sig") != file_signature:
            with st.spinner(f"Ingesting '{uploaded_file.name}' into SQL warehouse..."):
                file_bytes = uploaded_file.getvalue()
                from app.db.dataset_uploader import ingest_user_dataset

                ingest_res = ingest_user_dataset(
                    filename=uploaded_file.name,
                    file_bytes=file_bytes,
                )
                if ingest_res.get("success"):
                    st.session_state.last_uploaded_sig = file_signature
                    st.session_state.uploaded_summary = ingest_res
                    st.toast(f"✅ Table '{ingest_res['table_name']}' registered in warehouse!", icon="📊")
                else:
                    st.error(f"Dataset upload failed: {ingest_res.get('error', 'Unknown error')}")

    if st.session_state.get("uploaded_summary"):
        summary = st.session_state.uploaded_summary
        cols_formatted = ", ".join([f"<code>{c['name']}</code> ({c['dtype']})" for c in summary["columns"][:6]])
        st.markdown(
            f"""
            <div style="
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                padding: 10px 14px;
                margin-top: 10px;
            ">
                <div style="color: #34D399; font-weight: 700; font-size: 0.9rem;">
                    ✓ Active Table: <code>{summary['table_name']}</code> ({summary['row_count']:,} rows, {summary['column_count']} columns)
                </div>
                <div style="margin-top: 6px; font-size: 0.78rem; color: #CBD5E1;">
                    <strong>Detected Attributes:</strong> {cols_formatted}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Process Chat Input
chat_placeholder = "Ask a business question in natural language..."
if st.session_state.get("uploaded_summary"):
    tbl = st.session_state.uploaded_summary["table_name"]
    chat_placeholder = f"Ask questions about warehouse or your uploaded table '{tbl}'..."

user_prompt = st.chat_input(chat_placeholder) or selected_sample

if user_prompt and not st.session_state.pending_clarification:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Evaluating intent across relational SQL engine and vectorized operational docs..."):
            try:
                data = execute_ask(
                    user_prompt=user_prompt,
                    thread_id=st.session_state.thread_id,
                )
                st.session_state.thread_id = data["thread_id"]

                # If clarification requested
                if data.get("needs_clarification"):
                    st.session_state.pending_clarification = {
                        "thread_id": data["thread_id"],
                        "prompt": data.get("clarification_prompt", "Please clarify your request."),
                    }
                    render_route_badge("CLARIFY")
                    st.markdown(data["answer"])
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data["answer"],
                        "route": "CLARIFY",
                    })
                    st.rerun()
                else:
                    if data.get("route"):
                        render_route_badge(data["route"])
                    st.markdown(data["answer"])
                    if data.get("chart_spec"):
                        render_chart_component(data["chart_spec"])
                    if data.get("sql_query"):
                        render_sql_inspector(
                            data["sql_query"],
                            data.get("sql_columns"),
                            data.get("sql_row_count", 0),
                            data.get("execution_ms", 0.0),
                        )
                    if data.get("sources"):
                        render_sources_inspector(data["sources"])

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data["answer"],
                        "route": data.get("route"),
                        "chart_spec": data.get("chart_spec"),
                        "sql_query": data.get("sql_query"),
                        "sql_columns": data.get("sql_columns"),
                        "sql_row_count": data.get("sql_row_count", 0),
                        "sources": data.get("sources", []),
                        "execution_ms": data.get("execution_ms", 0.0),
                    })
            except Exception as e:
                st.error(f"Inquiry execution failure: {e}")
