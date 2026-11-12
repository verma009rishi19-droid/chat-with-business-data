"""SQL Security Guardrails and AST Validation using SQLGlot.

Enforces zero-trust query sanitization:
- Rejects multiple statements and semicolon chaining
- Rejects comments (-- and /* */) commonly used in SQL injection payloads
- Restricts AST strictly to a single SELECT statement (blocks DDL, DML, DCL)
- Blocks access to system catalogs and metadata schemas
- Injects or clamps row LIMITs (default 100, max 500)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

# Prohibited schema prefixes and system tables
RESTRICTED_SCHEMAS_OR_TABLES = {
    "information_schema",
    "pg_catalog",
    "pg_tables",
    "pg_views",
    "pg_stat",
    "pg_database",
    "pg_roles",
    "pg_user",
    "pg_shadow",
    "sqlite_master",
    "sqlite_schema",
    "sqlite_temp_master",
    "sqlite_sequence",
}

# AST expression types that are strictly forbidden
DISALLOWED_EXPRESSION_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Command,
    exp.Commit,
    exp.Rollback,
    exp.Set,
    exp.Merge,
    exp.Transaction,
    exp.TruncateTable,
)


@dataclass(frozen=True)
class SQLValidationResult:
    is_valid: bool
    sanitized_sql: str
    error: str | None = None


class SQLGuardrailError(Exception):
    """Raised when an incoming SQL query violates security policies."""


def validate_and_sanitize_sql(
    raw_query: str,
    dialect: str = "postgres",
    default_limit: int = 100,
    max_limit: int = 500,
) -> SQLValidationResult:
    """Validate query with SQLGlot AST and enforce read-only and limit rules."""
    if not raw_query or not raw_query.strip():
        return SQLValidationResult(is_valid=False, sanitized_sql="", error="Query cannot be empty.")

    cleaned_query = raw_query.strip()

    # Rule 1: Reject markdown backticks if LLM outputs markdown formatting
    if cleaned_query.startswith("```"):
        cleaned_query = re.sub(r"^```(?:sql)?\s*", "", cleaned_query, flags=re.IGNORECASE)
        cleaned_query = re.sub(r"\s*```$", "", cleaned_query)
        cleaned_query = cleaned_query.strip()

    # Rule 2: Block SQL comments to defeat injection evasion payloads
    if "--" in cleaned_query or "/*" in cleaned_query:
        return SQLValidationResult(
            is_valid=False,
            sanitized_sql="",
            error="Security violation: SQL comments ('--' or '/* */') are strictly prohibited.",
        )

    # Rule 3: Block multiple statements (semicolon chaining)
    trimmed_trailing_semicolon = cleaned_query.rstrip(";").strip()
    if ";" in trimmed_trailing_semicolon:
        return SQLValidationResult(
            is_valid=False,
            sanitized_sql="",
            error="Security violation: Multi-statement execution (semicolon chaining) is forbidden.",
        )

    # Rule 4: Parse with SQLGlot AST
    try:
        parsed_expressions = sqlglot.parse(trimmed_trailing_semicolon, read=dialect)
    except Exception:
        # Retry with generic dialect if dialect parsing failed
        try:
            parsed_expressions = sqlglot.parse(trimmed_trailing_semicolon)
        except Exception as e2:
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql="",
                error=f"SQL syntax parse error: {e2!s}",
            )

    if not parsed_expressions:
        return SQLValidationResult(is_valid=False, sanitized_sql="", error="Failed to parse SQL AST.")

    if len(parsed_expressions) > 1:
        return SQLValidationResult(
            is_valid=False,
            sanitized_sql="",
            error="Security violation: Exactly one statement allowed per execution.",
        )

    expression = parsed_expressions[0]

    # Rule 5: Root statement MUST be a SELECT (or Union of Selects)
    if not isinstance(expression, (exp.Select, exp.Union)):
        return SQLValidationResult(
            is_valid=False,
            sanitized_sql="",
            error=f"Security violation: Only SELECT queries are permitted. Found: {expression.key.upper()}",
        )

    # Rule 6: Check for nested prohibited AST nodes
    for node in expression.walk():
        if isinstance(node, DISALLOWED_EXPRESSION_TYPES):
            return SQLValidationResult(
                is_valid=False,
                sanitized_sql="",
                error=f"Security violation: Prohibited clause or operation detected: {node.key.upper()}",
            )

        # Rule 7: Guard against internal metadata and system catalog access
        if isinstance(node, exp.Table):
            table_name = (node.name or "").lower()
            db_name = (node.db or "").lower()
            if table_name in RESTRICTED_SCHEMAS_OR_TABLES or db_name in RESTRICTED_SCHEMAS_OR_TABLES:
                return SQLValidationResult(
                    is_valid=False,
                    sanitized_sql="",
                    error=f"Security violation: Direct access to system table/schema '{node.sql()}' is blocked.",
                )
            if table_name.startswith("pg_") or db_name.startswith("pg_"):
                return SQLValidationResult(
                    is_valid=False,
                    sanitized_sql="",
                    error=f"Security violation: Access to PostgreSQL system catalogs ('{table_name}') is blocked.",
                )

    # Rule 8: Enforce row limit
    limit_node = expression.find(exp.Limit)
    if limit_node is None:
        expression = expression.limit(default_limit)
    else:
        # Check current limit value
        limit_expr = limit_node.expression
        try:
            limit_val = int(str(limit_expr))
            if limit_val > max_limit:
                limit_node.set("expression", exp.Literal.number(max_limit))
            elif limit_val <= 0:
                limit_node.set("expression", exp.Literal.number(default_limit))
        except (ValueError, TypeError):
            limit_node.set("expression", exp.Literal.number(default_limit))

    # Generate sanitized SQL output
    sanitized_sql = expression.sql(dialect=dialect)
    return SQLValidationResult(is_valid=True, sanitized_sql=sanitized_sql, error=None)
