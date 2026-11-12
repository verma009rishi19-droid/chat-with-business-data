"""Observability integration for Langfuse and LangSmith tracing."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def get_tracing_callbacks(trace_id: str | None = None, tags: list[str] | None = None) -> list[Any]:
    """Resolve active tracing callbacks based on configuration.
    
    Supports:
    - Langfuse: full LLM/chain/tool traces with cost, latency, and input/output inspection.
    - LangSmith: native LangChain/LangGraph cloud tracing.
    """
    callbacks: list[Any] = []
    provider = settings.OBSERVABILITY_PROVIDER.lower()

    if provider == "langfuse":
        if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
            logger.warning("Langfuse chosen as observability provider but keys are not configured.")
            return callbacks
        try:
            from langfuse.callback import CallbackHandler
            handler = CallbackHandler(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
                session_id=trace_id,
                tags=tags or ["business-data-agent"],
            )
            callbacks.append(handler)
            logger.info("Langfuse tracing callback registered for session %s", trace_id)
        except ImportError:
            logger.warning("langfuse package not installed. Tracing disabled.")
        except Exception as e:
            logger.error("Failed to initialize Langfuse callback: %s", e)

    elif provider == "langsmith":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ.setdefault("LANGCHAIN_PROJECT", "business-data-analyst")
        logger.info("LangSmith tracing active via environment variables.")

    return callbacks
