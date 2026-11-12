"""Vector Store Management and Knowledge Base Ingestion using Chroma."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.config import BASE_DIR, settings
from app.rag.embeddings import get_embedding_function

logger = logging.getLogger(__name__)

DOCS_KB_DIR = BASE_DIR / "docs_kb"


def parse_markdown_metadata(content: str, filename: str) -> dict[str, Any]:
    """Extract structured metadata fields from markdown document header."""
    metadata: dict[str, Any] = {
        "source": filename,
        "title": filename.replace(".md", "").replace("_", " ").title(),
        "doc_id": "UNKNOWN",
        "department": "Operations",
    }

    # Extract title from # header
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        metadata["title"] = title_match.group(1).strip()

    # Extract Document ID
    doc_id_match = re.search(r"\*\*Document ID:\*\*\s*([^\n]+)", content)
    if doc_id_match:
        metadata["doc_id"] = doc_id_match.group(1).strip()

    # Extract Effective Date
    date_match = re.search(r"\*\*(?:Effective Date|Date|Effective Dates):\*\*\s*([^\n]+)", content)
    if date_match:
        metadata["effective_date"] = date_match.group(1).strip()

    # Extract Department
    dept_match = re.search(r"\*\*Department:\*\*\s*([^\n]+)", content)
    if dept_match:
        metadata["department"] = dept_match.group(1).strip()

    return metadata


def chunk_markdown_document(
    content: str,
    base_metadata: dict[str, Any],
    max_chunk_chars: int = 700,
    overlap_chars: int = 80,
) -> list[dict[str, Any]]:
    """Chunk markdown document by logical section headers, preserving context and metadata."""
    chunks: list[dict[str, Any]] = []

    # Split by level 2 headings
    sections = re.split(r"(^##\s+.+$)", content, flags=re.MULTILINE)

    current_header = "Overview"
    accumulated_text = ""

    # Grab pre-heading text as first section
    if sections and not sections[0].startswith("##"):
        intro = sections[0].strip()
        if intro:
            chunk_id = f"{base_metadata['source']}_{hashlib.md5(intro.encode()).hexdigest()[:8]}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": intro,
                "metadata": {**base_metadata, "section": "Header & Overview"},
            })
        sections = sections[1:]

    # Pair header and body
    for i in range(0, len(sections), 2):
        if i >= len(sections):
            break
        header_line = sections[i].strip()
        body = sections[i + 1].strip() if i + 1 < len(sections) else ""
        section_title = header_line.replace("##", "").strip()
        full_section = f"{header_line}\n{body}".strip()

        if len(full_section) <= max_chunk_chars:
            chunk_id = f"{base_metadata['source']}_{hashlib.md5(full_section.encode()).hexdigest()[:8]}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": full_section,
                "metadata": {**base_metadata, "section": section_title},
            })
        else:
            # Sub-split long section with sliding window
            paragraphs = full_section.split("\n\n")
            current_sub = ""
            sub_idx = 1
            for p in paragraphs:
                if len(current_sub) + len(p) <= max_chunk_chars:
                    current_sub += ("\n\n" + p if current_sub else p)
                else:
                    if current_sub:
                        c_id = f"{base_metadata['source']}_{hashlib.md5(current_sub.encode()).hexdigest()[:8]}_{sub_idx}"
                        chunks.append({
                            "chunk_id": c_id,
                            "text": current_sub,
                            "metadata": {**base_metadata, "section": f"{section_title} (part {sub_idx})"},
                        })
                        sub_idx += 1
                    current_sub = p[-overlap_chars:] + "\n\n" + p if len(p) > overlap_chars else p

            if current_sub:
                c_id = f"{base_metadata['source']}_{hashlib.md5(current_sub.encode()).hexdigest()[:8]}_{sub_idx}"
                chunks.append({
                    "chunk_id": c_id,
                    "text": current_sub,
                    "metadata": {**base_metadata, "section": f"{section_title} (part {sub_idx})"},
                })

    return chunks


def get_or_create_collection(
    persist_dir: str | None = None,
    collection_name: str | None = None,
) -> Collection:
    """Retrieve or create persistent Chroma collection."""
    path = persist_dir or settings.CHROMA_PERSIST_DIRECTORY
    name = collection_name or settings.CHROMA_COLLECTION_NAME

    os.makedirs(path, exist_ok=True)
    client = chromadb.PersistentClient(path=path)
    collection = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def ingest_knowledge_base(
    docs_dir: Path | str | None = None,
    persist_dir: str | None = None,
    force_mock_embeddings: bool = False,
) -> int:
    """Load all markdown documents, chunk them, embed, and upsert into Chroma."""
    target_dir = Path(docs_dir) if docs_dir else DOCS_KB_DIR
    if not target_dir.exists():
        raise FileNotFoundError(f"Documentation directory not found: {target_dir}")

    md_files = list(target_dir.glob("*.md"))
    if not md_files:
        logger.warning("No markdown documents found in %s", target_dir)
        return 0

    collection = get_or_create_collection(persist_dir=persist_dir)
    embedder = get_embedding_function(force_mock=force_mock_embeddings)

    all_chunks = []
    for f in md_files:
        content = f.read_text(encoding="utf-8")
        meta = parse_markdown_metadata(content, f.name)
        file_chunks = chunk_markdown_document(content, meta)
        all_chunks.extend(file_chunks)

    if not all_chunks:
        return 0

    chunk_ids = [c["chunk_id"] for c in all_chunks]
    documents = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    logger.info("Computing embeddings for %d document chunks...", len(documents))
    embeddings = embedder.embed_documents(documents)

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(chunk_ids), batch_size):
        end = min(i + batch_size, len(chunk_ids))
        collection.upsert(
            ids=chunk_ids[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
            embeddings=embeddings[i:end],
        )

    logger.info("Successfully ingested %d chunks from %d documents into Chroma.", len(all_chunks), len(md_files))
    return len(all_chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest business KB into Chroma.")
    parser.add_argument("--mock-embeddings", action="store_true", help="Force deterministic hash embeddings")
    args = parser.parse_args()

    count = ingest_knowledge_base(force_mock_embeddings=args.mock_embeddings)
    print(f"Ingestion complete: {count} chunks indexed.")


if __name__ == "__main__":
    main()
