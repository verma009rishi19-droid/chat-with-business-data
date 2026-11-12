"""Unit Tests for SQL Security Guardrails and AST Sanitization."""

from __future__ import annotations

import pytest

from app.db.guardrails import validate_and_sanitize_sql


def test_valid_select_query():
    """Test that standard analytical SELECT queries pass and format correctly."""
    query = "SELECT product_name, unit_price FROM products WHERE unit_price > 50 ORDER BY unit_price DESC"
    result = validate_and_sanitize_sql(query, dialect="postgres")
    assert result.is_valid is True
    assert result.error is None
    assert "LIMIT 100" in result.sanitized_sql.upper()


def test_markdown_stripping():
    """Test that markdown backticks emitted by LLMs are safely stripped."""
    query = "```sql\nSELECT order_id, total_amount FROM orders WHERE order_status = 'Delivered'\n```"
    result = validate_and_sanitize_sql(query, dialect="postgres")
    assert result.is_valid is True
    assert "orders" in result.sanitized_sql


def test_auto_limit_injection():
    """Test that queries without LIMIT get default LIMIT 100 injected."""
    query = "SELECT * FROM dark_stores"
    result = validate_and_sanitize_sql(query, dialect="postgres", default_limit=100)
    assert result.is_valid is True
    assert "LIMIT 100" in result.sanitized_sql.upper()


def test_limit_clamping():
    """Test that excessively large LIMITs are clamped to max_limit."""
    query = "SELECT * FROM orders LIMIT 5000"
    result = validate_and_sanitize_sql(query, dialect="postgres", max_limit=500)
    assert result.is_valid is True
    assert "LIMIT 500" in result.sanitized_sql.upper()


def test_block_sql_comments():
    """Test that inline comments (-- and /* */) are blocked to prevent injection evasion."""
    query_line = "SELECT * FROM products -- malicious bypass comment"
    res1 = validate_and_sanitize_sql(query_line)
    assert res1.is_valid is False
    assert "comments" in res1.error.lower()

    query_block = "SELECT * FROM products /* comment */ WHERE unit_price > 10"
    res2 = validate_and_sanitize_sql(query_block)
    assert res2.is_valid is False
    assert "comments" in res2.error.lower()


def test_block_multi_statement_semicolon_chain():
    """Test that multi-statement queries separated by semicolons are blocked."""
    query = "SELECT * FROM products; DROP TABLE customers;"
    result = validate_and_sanitize_sql(query)
    assert result.is_valid is False
    assert "multi-statement" in result.error.lower() or "exactly one" in result.error.lower()


@pytest.mark.parametrize(
    "prohibited_query",
    [
        "DROP TABLE orders",
        "TRUNCATE TABLE deliveries",
        "DELETE FROM customers WHERE customer_id = 'CUST-0001'",
        "UPDATE products SET unit_price = 0 WHERE product_id = 'PROD-001'",
        "INSERT INTO categories (category_id, category_name, department) VALUES ('CAT-99', 'Fake', 'Test')",
        "ALTER TABLE orders ADD COLUMN hack_col TEXT",
        "CREATE TABLE backdoor (id INT)",
    ],
)
def test_block_ddl_and_dml(prohibited_query: str):
    """Test that all DDL and DML operations are strictly blocked by the AST validator."""
    result = validate_and_sanitize_sql(prohibited_query)
    assert result.is_valid is False
    assert "security violation" in result.error.lower()


@pytest.mark.parametrize(
    "catalog_query",
    [
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM pg_tables",
        "SELECT * FROM sqlite_master",
        "SELECT * FROM sqlite_schema",
    ],
)
def test_block_system_catalogs(catalog_query: str):
    """Test that system catalogs and internal metadata schemas are blocked."""
    result = validate_and_sanitize_sql(catalog_query)
    assert result.is_valid is False
    assert "system" in result.error.lower() or "blocked" in result.error.lower()


def test_empty_query():
    """Test that empty queries are gracefully rejected."""
    result = validate_and_sanitize_sql("   ")
    assert result.is_valid is False
    assert "empty" in result.error.lower()
