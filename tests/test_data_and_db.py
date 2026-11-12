"""Unit Tests for Phase 1: Data Generation, Schema, and Database Context."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from app.config import settings
from app.db.connection import get_engine
from app.db.schema_context import get_schema_context_prompt


@pytest.fixture(scope="module")
def project_dirs():
    base = Path(__file__).resolve().parent.parent
    return {
        "base": base,
        "data": base / "data",
        "docs_kb": base / "docs_kb",
    }


def test_data_generation_row_counts(project_dirs):
    """Test that synthetic data generator generates >= 10,000 orders and expected tables."""
    data_dir = project_dirs["data"]
    orders_csv = data_dir / "orders.csv"
    items_csv = data_dir / "order_items.csv"
    categories_csv = data_dir / "categories.csv"
    products_csv = data_dir / "products.csv"

    assert orders_csv.exists(), "orders.csv must exist"
    assert items_csv.exists(), "order_items.csv must exist"

    orders_df = pd.read_csv(orders_csv)
    items_df = pd.read_csv(items_csv)
    products_df = pd.read_csv(products_csv)

    assert len(orders_df) >= 10000, f"Expected >= 10,000 orders, got {len(orders_df)}"
    assert len(items_df) >= 20000, f"Expected >= 20,000 items, got {len(items_df)}"
    assert len(products_df) >= 40, f"Expected >= 40 products, got {len(products_df)}"


def test_seeded_sourdough_recall_anomaly(project_dirs):
    """Test that Sourdough sales experience a steep decline in Q3 (July-September)."""
    orders_df = pd.read_csv(project_dirs["data"] / "orders.csv")
    items_df = pd.read_csv(project_dirs["data"] / "order_items.csv")

    merged = items_df.merge(orders_df, on="order_id")
    merged["order_timestamp"] = pd.to_datetime(merged["order_timestamp"])

    # PROD-017 is Artisanal Sourdough Country Loaf 400g
    sourdough = merged[merged["product_id"] == "PROD-017"]

    # Compare Q2 (Apr-Jun: months 4,5,6) to Q3 (Jul-Sep: months 7,8,9)
    q2_count = len(sourdough[sourdough["order_timestamp"].dt.month.isin([4, 5, 6])])
    q3_count = len(sourdough[sourdough["order_timestamp"].dt.month.isin([7, 8, 9])])

    assert q2_count > 0, "Expected positive Q2 sourdough orders"
    # Q3 should be down by at least 60% due to the batch recall
    assert q3_count < (q2_count * 0.4), (
        f"Expected Q3 sourdough ({q3_count}) to be < 40% of Q2 ({q2_count}) due to recall"
    )


def test_seeded_monsoon_delivery_delays(project_dirs):
    """Test that monsoon period in Mumbai/Delhi exhibits elevated delivery delays and rain conditions."""
    deliveries_df = pd.read_csv(project_dirs["data"] / "deliveries.csv")
    orders_df = pd.read_csv(project_dirs["data"] / "orders.csv")
    stores_df = pd.read_csv(project_dirs["data"] / "dark_stores.csv")

    m = deliveries_df.merge(orders_df, on="order_id").merge(stores_df, on="store_id")
    m["order_timestamp"] = pd.to_datetime(m["order_timestamp"])

    # Check Mumbai and Delhi in July-August
    monsoon = m[
        (m["city"].isin(["Mumbai", "Delhi-NCR"]))
        & (m["order_timestamp"].dt.month.isin([7, 8]))
        & (m["order_status"] == "Delivered")
    ]
    dry_season = m[
        (m["city"].isin(["Mumbai", "Delhi-NCR"]))
        & (m["order_timestamp"].dt.month.isin([1, 2, 3]))
        & (m["order_status"] == "Delivered")
    ]

    monsoon_avg_duration = monsoon["delivery_duration_minutes"].mean()
    dry_avg_duration = dry_season["delivery_duration_minutes"].mean()

    assert monsoon_avg_duration > dry_avg_duration + 5.0, (
        f"Monsoon avg delivery time ({monsoon_avg_duration:.1f}m) should be significantly higher "
        f"than dry season ({dry_avg_duration:.1f}m)"
    )


def test_seeded_festive_diwali_surge(project_dirs):
    """Test that Confectionery / Dry Fruits surge significantly in October-November."""
    orders_df = pd.read_csv(project_dirs["data"] / "orders.csv")
    items_df = pd.read_csv(project_dirs["data"] / "order_items.csv")

    merged = items_df.merge(orders_df, on="order_id")
    merged["order_timestamp"] = pd.to_datetime(merged["order_timestamp"])

    # PROD-031 is Kaju Katli Heritage Gold Box
    kaju = merged[merged["product_id"] == "PROD-031"]
    sep_count = len(kaju[kaju["order_timestamp"].dt.month == 9])
    oct_count = len(kaju[kaju["order_timestamp"].dt.month == 10])

    assert oct_count > (sep_count * 2.0), (
        f"Diwali October Kaju Katli orders ({oct_count}) should be at least 2x September ({sep_count})"
    )


def test_database_tables_and_row_counts():
    """Verify that the database has all tables and matches loaded dataset."""
    settings.DB_TYPE = "sqlite"
    engine = get_engine(readonly=True)

    expected_tables = [
        "categories", "products", "dark_stores", "customers",
        "orders", "order_items", "deliveries", "inventory", "customer_ratings"
    ]

    with engine.connect() as conn:
        for tbl in expected_tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            assert result > 0, f"Table {tbl} should not be empty"


def test_schema_context_prompt():
    """Test schema context prompt generator includes tables, keys, and glossary."""
    settings.DB_TYPE = "sqlite"
    prompt = get_schema_context_prompt(force_refresh=True)

    assert "=== DATABASE SCHEMA CONTEXT ===" in prompt
    assert "Table: orders" in prompt
    assert "Table: products" in prompt
    assert "order_status" in prompt
    assert "BUSINESS GLOSSARY & DOMAIN RULES:" in prompt
    assert "Average Order Value (AOV)" in prompt
    assert "Q3: '2025-07-01' to '2025-09-30'" in prompt


def test_docs_kb_files_exist(project_dirs):
    """Test that all business context documents exist in docs_kb."""
    docs_kb_dir = project_dirs["docs_kb"]
    files = list(docs_kb_dir.glob("*.md"))
    assert len(files) >= 6, f"Expected at least 6 KB markdown docs, found {len(files)}"
