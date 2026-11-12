"""Streamlit Web Application: Chat with Your Business Data."""

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
    from ui.components import render_chart_component, render_sources_inspector, render_sql_inspector
except ImportError:
    from components import render_chart_component, render_sources_inspector, render_sql_inspector

st.set_page_config(
    page_title="Chat with Your Business Data",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

    return {"status": "offline", "database": "unknown", "db_connected": False, "vector_store_chunks": 0, "mode": "offline"}


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
        final_state = app_graph.invoke({"question": user_prompt, "thread_id": t_id}, config=config)
    except GraphInterrupt:
        state_snap = app_graph.get_state(config)
        snap_values = state_snap.values if state_snap else {}
        prompt = snap_values.get("clarification_prompt") or "Please clarify what timeframe or metric you would like to analyze."
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
        prompt = final_state.get("clarification_prompt") or "Please clarify what timeframe or metric you would like to analyze."
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
        chart_dict = chart_val.model_dump() if hasattr(chart_val, "model_dump") else chart_val

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
        final_state = app_graph.invoke(Command(resume=clarification.strip()), config=config)
    except Exception:
        final_state = app_graph.invoke({"user_clarification": clarification.strip(), "needs_clarification": False}, config=config)

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
        chart_dict = chart_val.model_dump() if hasattr(chart_val, "model_dump") else chart_val

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

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚡ Blinkit Analytics")
    st.markdown("*Multi-Agent Business Intelligence Assistant*")
    st.divider()

    health = check_api_health()
    if health["status"] == "healthy":
        st.success(f"🟢 **System Online** ({health['database'].upper()})")
    elif health["status"] == "degraded":
        st.warning(f"🟡 **System Degraded** ({health['database'].upper()})")
    else:
        st.error("🔴 **API Server Offline** (Run `uvicorn app.api.routes:app`)")

    st.caption(f"Knowledge Base Index: **{health.get('vector_store_chunks', 0)} chunks**")
    st.divider()

    st.markdown("### 💡 Sample Questions")
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
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.session_state.pending_clarification = None
        st.rerun()

# --- MAIN CHAT AREA ---
st.header("📈 Business Analytics Assistant")
st.markdown(
    "Ask business questions in plain English. The assistant queries relational data, "
    "synthesizes operational policies, and renders charts without executing code."
)

# Render Message History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
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

# Render Clarification Input Box if waiting for human clarification
if st.session_state.pending_clarification:
    clarify_info = st.session_state.pending_clarification
    with st.container():
        st.info(f"❓ **Clarification Needed:** {clarify_info['prompt']}")
        with st.form("clarification_form"):
            user_response = st.text_input(
                "Your clarification:",
                placeholder="e.g. Focus on Artisanal Sourdough loaves in Q3...",
            )
            submitted = st.form_submit_button("Submit Clarification 🚀")
            if submitted and user_response.strip():
                # Add user response to chat
                st.session_state.messages.append({"role": "user", "content": user_response.strip()})

                with st.spinner("Resuming analytics workflow..."):
                    try:
                        data = execute_resume(
                            clarification=user_response.strip(),
                            thread_id=clarify_info["thread_id"],
                        )
                        st.session_state.pending_clarification = None
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": data["answer"],
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

# Process Input
user_prompt = st.chat_input("Ask a business question...") or selected_sample

if user_prompt and not st.session_state.pending_clarification:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing business question across SQL warehouse and knowledge base..."):
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
                    st.markdown(data["answer"])
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data["answer"],
                    })
                    st.rerun()
                else:
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
                        "chart_spec": data.get("chart_spec"),
                        "sql_query": data.get("sql_query"),
                        "sql_columns": data.get("sql_columns"),
                        "sql_row_count": data.get("sql_row_count", 0),
                        "sources": data.get("sources", []),
                        "execution_ms": data.get("execution_ms", 0.0),
                    })
            except Exception as e:
                st.error(f"Inquiry execution failure: {e}")
