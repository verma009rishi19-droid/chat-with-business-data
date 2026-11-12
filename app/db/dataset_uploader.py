"""Dataset Uploader: Parse and ingest uploaded CSV, Excel, Parquet, or JSON into SQL database."""

from __future__ import annotations

import io
import logging
import re
from typing import Any

import pandas as pd

from app.db.connection import get_engine
from app.db.schema_context import get_schema_context_prompt

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet", ".json"}


def sanitize_identifier(name: str) -> str:
    """Sanitize table or column name into safe SQL identifier."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip().lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    if not clean or clean[0].isdigit():
        clean = f"tbl_{clean}"
    return clean[:48]


def ingest_user_dataset(
    filename: str,
    file_bytes: bytes,
    table_name: str | None = None,
) -> dict[str, Any]:
    """Parse uploaded dataset file and register it into SQL warehouse for immediate querying.
    
    Supported formats: CSV, Excel (.xlsx, .xls), Parquet (.parquet), JSON (.json).
    """
    ext = ("." + filename.split(".")[-1].lower()) if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        return {
            "success": False,
            "error": f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        }

    buffer = io.BytesIO(file_bytes)
    try:
        if ext == ".csv":
            df = pd.read_csv(buffer)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(buffer)
        elif ext == ".parquet":
            df = pd.read_parquet(buffer)
        elif ext == ".json":
            df = pd.read_json(buffer)
        else:
            return {"success": False, "error": f"Cannot parse extension {ext}"}
    except Exception as e:
        logger.error("Failed to parse uploaded dataset %s: %s", filename, e)
        return {"success": False, "error": f"File parsing failed: {str(e)}"}

    if df.empty:
        return {"success": False, "error": "The uploaded dataset contains zero rows."}

    # Clean column names
    df.columns = [sanitize_identifier(str(c)) for c in df.columns]

    # Clean table name
    base_name = table_name or filename.rsplit(".", 1)[0]
    final_table_name = sanitize_identifier(base_name)

    # Ingest into DB with admin engine
    try:
        engine = get_engine(readonly=False)
        df.to_sql(final_table_name, engine, if_exists="replace", index=False)
        logger.info("Successfully ingested table '%s' with %d rows and %d columns", final_table_name, len(df), len(df.columns))

        # Invalidate and re-extract schema context so SQL Agent immediately recognizes the new table!
        get_schema_context_prompt(force_refresh=True)

        col_summary = [{"name": col, "dtype": str(df[col].dtype)} for col in df.columns]

        return {
            "success": True,
            "table_name": final_table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": col_summary,
            "sample_rows": df.head(4).to_dict(orient="records"),
        }
    except Exception as e:
        logger.error("Failed to write dataset to database: %s", e)
        return {"success": False, "error": f"Database ingestion failed: {str(e)}"}
