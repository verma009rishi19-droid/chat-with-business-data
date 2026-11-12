"""Schema Context Extractor & Business Glossary for Text-to-SQL Agent.

Dynamically inspects tables, column types, foreign keys, and distinct sample values,
and bundles them with a business glossary to prevent LLM hallucination in SQL generation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, text

from app.db.connection import get_engine

BUSINESS_GLOSSARY = """
BUSINESS GLOSSARY & DOMAIN RULES:
1. Fiscal Quarters (Calendar Year 2025):
   - Q1: '2025-01-01' to '2025-03-31'
   - Q2: '2025-04-01' to '2025-06-30'
   - Q3: '2025-07-01' to '2025-09-30' (Monsoon period & Supplier recalls)
   - Q4: '2025-10-01' to '2025-12-31' (Festive season: Diwali peak in October-November)

2. Key Metrics & Formulas:
   - Average Order Value (AOV): AVG(total_amount) or SUM(total_amount) / COUNT(DISTINCT order_id)
   - Gross Merchandise Value (GMV): SUM(total_amount) for orders with order_status = 'Delivered'
   - Delivery Delay: delay_minutes > 0 (or delivery_duration_minutes > 15.0)
   - On-Time Delivery Rate: 100.0 * COUNT(CASE WHEN delay_minutes <= 0 THEN 1 END) / COUNT(*)
   - Gross Margin / Profit: SUM(order_items.quantity * (products.unit_price - products.cost_price))
   - Cancellation Rate: 100.0 * COUNT(CASE WHEN order_status = 'Cancelled' THEN 1 END) / COUNT(*)
   - Out of Stock / Stockout: stock_on_hand <= 0 in inventory table

3. Anomaly Reference SKUs / Products:
   - Artisanal Sourdough: 'SKU-BAK-001' (Loaf 400g) and 'SKU-BAK-004' (Olive & Rosemary)
   - Imported Hass Avocados: 'SKU-PROD-007'
   - Organic Farm Fresh Whole Milk 1L: 'SKU-DAI-001'
   - Festive Dry Fruits / Sweets: 'SKU-DRY-002' (Royal Afghan Dry Fruits), 'SKU-SWT-001' (Kaju Katli)
"""


class SchemaContext:
    def __init__(self, readonly: bool = True):
        self.engine = get_engine(readonly=readonly)
        self.inspector = inspect(self.engine)

    def get_table_names(self) -> list[str]:
        return self.inspector.get_table_names()

    def get_table_details(self, table_name: str) -> dict[str, Any]:
        columns = self.inspector.get_columns(table_name)
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        foreign_keys = self.inspector.get_foreign_keys(table_name)

        col_defs = []
        for col in columns:
            col_info = f"{col['name']} ({col['type']!s})"
            if col.get("primary_key") or col["name"] in pk_constraint.get("constrained_columns", []):
                col_info += " [PRIMARY KEY]"
            col_defs.append(col_info)

        fk_defs = []
        for fk in foreign_keys:
            fk_defs.append(
                f"{', '.join(fk['constrained_columns'])} -> {fk['referred_table']}({', '.join(fk['referred_columns'])})"
            )

        return {
            "table_name": table_name,
            "columns": col_defs,
            "foreign_keys": fk_defs,
        }

    def get_sample_values(self) -> dict[str, list[str]]:
        """Collect categorical values for enum-like and city columns to guide WHERE clause filters."""
        samples = {}
        queries = {
            "cities": "SELECT DISTINCT city FROM dark_stores ORDER BY city",
            "order_statuses": "SELECT DISTINCT order_status FROM orders ORDER BY order_status",
            "weather_conditions": "SELECT DISTINCT weather_condition FROM deliveries ORDER BY weather_condition",
            "customer_tiers": "SELECT DISTINCT customer_tier FROM customers ORDER BY customer_tier",
            "categories": "SELECT DISTINCT category_name FROM categories ORDER BY category_name",
        }
        with self.engine.connect() as conn:
            for key, q in queries.items():
                try:
                    res = conn.execute(text(q)).scalars().all()
                    samples[key] = [str(x) for x in res if x is not None]
                except Exception:
                    pass
        return samples

    def get_full_schema_prompt(self) -> str:
        """Render complete schema context with types, relationships, sample values, and glossary."""
        lines = ["=== DATABASE SCHEMA CONTEXT ==="]
        for tbl in self.get_table_names():
            details = self.get_table_details(tbl)
            lines.append(f"\nTable: {details['table_name']}")
            lines.append("Columns:")
            for col in details["columns"]:
                lines.append(f"  - {col}")
            if details["foreign_keys"]:
                lines.append("Foreign Keys:")
                for fk in details["foreign_keys"]:
                    lines.append(f"  - {fk}")

        lines.append("\n=== RECOGNIZED VALUES (For WHERE filter clauses) ===")
        sample_vals = self.get_sample_values()
        for k, v in sample_vals.items():
            lines.append(f"{k.upper()}: {', '.join(repr(x) for x in v)}")

        lines.append(BUSINESS_GLOSSARY)
        return "\n".join(lines)


_cached_schema_prompt: str | None = None


def get_schema_context_prompt(force_refresh: bool = False) -> str:
    """Retrieve cached schema context prompt string."""
    global _cached_schema_prompt
    if _cached_schema_prompt is None or force_refresh:
        ctx = SchemaContext(readonly=True)
        _cached_schema_prompt = ctx.get_full_schema_prompt()
    return _cached_schema_prompt
