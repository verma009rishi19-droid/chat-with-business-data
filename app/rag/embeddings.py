"""Embedding Layer for RAG with Gemini and Offline Deterministic Fallback."""

from __future__ import annotations

import hashlib
import logging
import os
import re

import numpy as np
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)


class DeterministicHashEmbeddings(Embeddings):
    """Deterministic, lightweight 384-dimensional embedding function for offline testing & CI.
    
    Generates consistent bag-of-words and n-gram hash vector projections without external network calls.
    Allows local offline unit testing of RAG retrieval without consuming API quota.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        tokens = re.findall(r"\w+", text.lower())
        vec = np.zeros(self.dimension, dtype=np.float32)
        if not tokens:
            return vec.tolist()

        for token in tokens:
            # Hash token into index
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
            vec[idx] += sign

        # Add bigram hashes for context sensitivity
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            h = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
            vec[idx] += 1.5 * sign

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def get_embedding_function(force_mock: bool = False) -> Embeddings:
    """Return configured embedding function (Gemini or offline deterministic)."""
    api_key = settings.GOOGLE_API_KEY or os.environ.get("GOOGLE_API_KEY", "")

    if force_mock or not api_key or api_key.startswith("dummy"):
        logger.info("Using DeterministicHashEmbeddings for vector representations.")
        return DeterministicHashEmbeddings()

    logger.info("Using GoogleGenerativeAIEmbeddings (%s).", settings.EMBEDDING_MODEL)
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=api_key,
    )
