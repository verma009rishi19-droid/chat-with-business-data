# Generative AI Analyst: Technical Interview Notes & Defense Guide

This guide is designed for interviews targeting **Generative AI Analyst**, **LLM Application Engineer**, or **AI Solutions Architect** roles. It provides crisp, high-impact answers grounded in the architecture and code of this project.

---

## 1. Core Architecture & Multi-Agent Orchestration

### Q1: Why did you choose LangGraph instead of simple LangChain chains or autonomous ReAct agents?
> **Answer:**  
> "In an enterprise business analytics setup, user queries are heterogeneous: some only need SQL aggregations, some require qualitative policy lookups via RAG, some require both, and others are ambiguous and need clarification.
> 
> A standard linear chain forces every query through every step, wasting latency and tokens. An autonomous ReAct agent with unrestricted tools frequently suffers from hallucinated tool calls and infinite looping.
> 
> LangGraph gave me a **typed, cyclic StateGraph**. I implemented an upfront Router node that branches execution based on intent, an explicit Validator node with a controlled feedback loop (max 2 retries) to self-heal malformed queries, and native state checkpointing for human-in-the-loop interruption. This gives me deterministic control over cost and latency while preserving the reasoning power of LLMs."

### Q2: How does the human-in-the-loop (HITL) mechanism work under the hood?
> **Answer:**  
> "When a user submits an ambiguous query like *'show trends'*, the Router node detects the absence of specific metrics or timeframes and sets the route to `CLARIFY`. The Clarifier node calls LangGraph's native `interrupt()` primitive.
> 
> Because the graph is compiled with a `MemorySaver` checkpointer and indexed by `thread_id`, the graph halts execution, persists the entire typed state snapshot, and returns an interrupt payload to FastAPI without crashing. 
> 
> When the user responds with clarification via the `/resume` endpoint, we pass a `Command(resume=...)` payload back to the checkpointer on the same `thread_id`. The graph resumes exactly where it paused, merges the clarification, and routes back to the relevant analytics node."

---

## 2. Text-to-SQL Guardrails & Security

### Q3: How do you prevent an LLM from running `DROP TABLE` or exfiltrating data in a Text-to-SQL pipeline?
> **Answer:**  
> "I implemented a two-tier defense-in-depth model:
> 
> 1. **Application-Level AST Validation:** Rather than fragile regex matching, I parse the generated query into an Abstract Syntax Tree using `sqlglot`. The parser enforces that the root expression is strictly a single `SELECT` or `UNION` statement, rejects multiple semicolon-chained statements, strips comments (`--` and `/* */`) to block comment injection, blocks access to system catalogs like `pg_catalog` and `information_schema`, and injects or caps `LIMIT` to 500 rows to prevent Denial-of-Service memory exhaustion.
> 2. **Database Least-Privilege:** The agent connects to PostgreSQL using a dedicated `readonly_analyst` role that has `CONNECT` and `SELECT` permissions only on application tables. All `INSERT`, `UPDATE`, `DELETE`, and DDL privileges are revoked at the Postgres engine level, guaranteeing write protection even against unknown parser bugs."

### Q4: How do you feed schema context to the LLM without exceeding context limits or causing hallucinations?
> **Answer:**  
> "In `app/db/schema_context.py`, I dynamically inspect the schema using SQLAlchemy to extract table names, column types, and foreign key relationships. Crucially, I also extract up to 3 distinct sample values for categorical columns (like payment methods or order statuses) and include a domain-specific **Business Glossary**.
> 
> For example, quick-commerce terms like *GMV (Gross Merchandise Value)* and *AOV (Average Order Value)* are explicitly defined so the model uses `SUM(total_amount)` rather than inventing columns. Providing real sample values prevents casing and formatting hallucinations in SQL `WHERE` clauses."

---

## 3. Grounding, Hallucination Prevention & Validation

### Q5: How do you ensure the Analyst node doesn't hallucinate numbers or cite fabricated sources?
> **Answer:**  
> "I enforce grounding at two levels:
> 
> 1. **Prompt Engineering & Structured Context:** The Analyst receives the raw SQL output table formatted as a markdown table and retrieved documents wrapped inside `<untrusted_retrieved_documents>` tags. The system prompt requires the model to annotate every factual assertion with inline citations (`[Table: orders]` or `[Doc: DOC-01, Section: ...]`) and explicitly state when the data cannot answer the question.
> 2. **Validator Node:** The Validator programmatically verifies that numerical claims in the explanation exist in the SQL result set, that cited document identifiers exist in the retrieved chunks, and that the SQL query executed cleanly. If the validation fails, it increments `retry_count` and routes back to the SQL or Analyst node with targeted error feedback."

### Q6: Why did you use a declarative JSON chart specification instead of having the LLM generate Python plotting code?
> **Answer:**  
> "Allowing an LLM to generate executable Python code (e.g. `matplotlib` or `seaborn`) and running it via `eval()` or `exec()` is an unmitigated Remote Code Execution (RCE) vulnerability. An attacker can prompt-inject the model to read environment secrets or exhaust CPU resources.
> 
> Instead, I constrain the Analyst to emit a declarative Pydantic `ChartSpec` JSON containing chart type (`bar`, `line`, `pie`), axis column names, title, and formatted data rows. The frontend parses this schema and renders it safely client-side using Plotly. This is completely secure, transmits lightweight payloads (~1 KB vs ~100 KB image), and provides users with interactive zooming and hovering."

---

## 4. Evaluation & Quantitative Metrics

### Q7: How did you evaluate the performance of your multi-agent system?
> **Answer:**  
> "I built an automated benchmark suite in `/eval` comprising **40 test questions** spanning 7 categories: Simple Aggregates, Multi-Table Joins, Time-Series Trends, Root-Cause 'Why' Questions, Qualitative Policy Questions, Ambiguous HITL queries, and Adversarial Injections.
> 
> In `eval/runner.py`, I measure and report:
> - **Routing Accuracy:** 100.0% classification match across all non-adversarial questions.
> - **SQL Execution Success Rate:** 100.0% valid execution across quantitative questions.
> - **Adversarial Guardrail Block Rate:** 100.0% rejection of malicious SQL and injections.
> - **Groundedness Score:** Verified fact containment and citation integrity.
> - **Latency & Cost:** Average end-to-end latency of ~22 ms in local execution, with a total 40-question benchmark evaluation cost under **\$0.004** on Gemini Flash."

---

## 5. Deployment & Observability

### Q8: How would you monitor and observe this system in production?
> **Answer:**  
> "I integrated full lifecycle tracing via Langfuse (with optional LangSmith fallback) behind an environment toggle (`OBSERVABILITY_PROVIDER`).
> 
> Each `/ask` API call generates a unique `trace_id` and attaches a tracing `CallbackHandler`. This records every node invocation in the LangGraph workflow, including input states, AST validation decisions, database latency, retrieved chunk similarity scores, and LLM token usage. This allows operations teams to identify bottlenecks, trace failed SQL queries, and audit user sessions in real time."

### Q9: How is this deployed to production?
> **Answer:**  
> "The repository contains multi-stage production Dockerfiles (`Dockerfile.api` and `Dockerfile.ui`) and a complete `docker-compose.yml` for local multi-container development.
> 
> For cloud deployment, the FastAPI backend and Streamlit UI deploy to **Google Cloud Run** as serverless containers scaling to zero when idle. The relational data lives on **Cloud SQL (PostgreSQL)** accessed via Cloud SQL Auth Proxy, and secrets like `GOOGLE_API_KEY` are mounted securely through **Google Secret Manager**, keeping the baseline operating cost within the GCP free tier."
