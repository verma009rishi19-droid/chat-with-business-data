"""Database Schema & Data Loader.

Creates database schema and loads synthetic quick commerce data from CSV files.
Supports both PostgreSQL and SQLite fallback.
"""

from __future__ import annotations

import argparse
import logging
import re

import pandas as pd
from sqlalchemy import text

from app.config import BASE_DIR, settings
from app.db.connection import get_engine
from data.generate_synthetic_data import generate_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = BASE_DIR / "data"
SCHEMA_SQL_PATH = DATA_DIR / "schema.sql"

TABLE_LOAD_ORDER = [
    ("categories", "categories.csv"),
    ("products", "products.csv"),
    ("dark_stores", "dark_stores.csv"),
    ("customers", "customers.csv"),
    ("orders", "orders.csv"),
    ("order_items", "order_items.csv"),
    ("deliveries", "deliveries.csv"),
    ("inventory", "inventory.csv"),
    ("customer_ratings", "customer_ratings.csv"),
]


def prepare_csvs_if_missing() -> None:
    """Ensure synthetic data CSVs exist before loading."""
    first_file = DATA_DIR / "categories.csv"
    if not first_file.exists():
        logger.info("CSV files not found in %s. Generating synthetic dataset...", DATA_DIR)
        counts = generate_dataset(output_dir=DATA_DIR)
        logger.info("Generated %d files.", len(counts))
    else:
        logger.info("Existing CSV data found in %s.", DATA_DIR)


def create_schema(is_sqlite: bool = False) -> None:
    """Execute schema creation DDL."""
    if not SCHEMA_SQL_PATH.exists():
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_SQL_PATH}")

    sql_content = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    engine = get_engine(readonly=False)

    if is_sqlite:
        logger.info("Adapting schema DDL for SQLite...")
        # Strip PostgreSQL-specific DO blocks
        sql_content = re.sub(r"DO\s*\$do\$.*?\$do\$;", "", sql_content, flags=re.DOTALL)
        # Strip CASCADE in DROP TABLE
        sql_content = re.sub(r"DROP TABLE IF EXISTS (\w+) CASCADE;", r"DROP TABLE IF EXISTS \1;", sql_content)
        # Split into individual statements
        statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

        with engine.begin() as conn:
            for stmt in statements:
                # Skip role or postgres specific syntax
                if "readonly_analyst" in stmt or "pg_catalog" in stmt:
                    continue
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    logger.warning("Warning executing DDL statement [%s...]: %s", stmt[:40], e)
    else:
        logger.info("Executing standard PostgreSQL schema DDL...")
        with engine.begin() as conn:
            # Split by semicolons avoiding comments
            for stmt in sql_content.split(";"):
                clean_stmt = stmt.strip()
                if clean_stmt:
                    conn.execute(text(clean_stmt))

    logger.info("Schema created successfully.")


def load_data(is_sqlite: bool = False) -> dict[str, int]:
    """Bulk load CSVs into database tables using pandas and SQLAlchemy."""
    prepare_csvs_if_missing()
    create_schema(is_sqlite=is_sqlite)

    engine = get_engine(readonly=False)
    results = {}

    for table_name, csv_filename in TABLE_LOAD_ORDER:
        csv_path = DATA_DIR / csv_filename
        if not csv_path.exists():
            logger.warning("CSV file missing: %s", csv_path)
            continue

        df = pd.read_csv(csv_path)

        # Standardize dates and nulls
        if "order_timestamp" in df.columns:
            df["order_timestamp"] = pd.to_datetime(df["order_timestamp"])
        if "delivery_time" in df.columns:
            df["delivery_time"] = pd.to_datetime(df["delivery_time"])
        if "dispatch_time" in df.columns:
            df["dispatch_time"] = pd.to_datetime(df["dispatch_time"])
        if "last_restocked_at" in df.columns:
            df["last_restocked_at"] = pd.to_datetime(df["last_restocked_at"])
        if "signup_date" in df.columns:
            df["signup_date"] = pd.to_datetime(df["signup_date"]).dt.date

        # In deliveries, handle NaNs in duration/ratings
        if table_name == "deliveries":
            df["delivery_duration_minutes"] = df["delivery_duration_minutes"].where(
                df["delivery_duration_minutes"].notnull(), None
            )
            df["delivery_rating"] = df["delivery_rating"].where(
                df["delivery_rating"].notnull(), None
            )

        logger.info("Loading %d rows into %s...", len(df), table_name)
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",
            index=False,
            chunksize=2000,
            method="multi" if not is_sqlite else None,
        )
        results[table_name] = len(df)

    logger.info("All tables successfully populated.")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Load business data into database.")
    parser.add_argument("--sqlite", action="store_true", help="Force load into local SQLite")
    parser.add_argument("--postgres", action="store_true", help="Force load into PostgreSQL")
    args = parser.parse_args()

    if args.sqlite:
        settings.DB_TYPE = "sqlite"
    elif args.postgres:
        settings.DB_TYPE = "postgres"

    is_sqlite = (settings.DB_TYPE == "sqlite")
    loaded = load_data(is_sqlite=is_sqlite)
    print("\nData loading summary:")
    for tbl, count in loaded.items():
        print(f"  {tbl}: {count:,} rows")


if __name__ == "__main__":
    main()
