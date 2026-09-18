# AI-Augmented DB Reliability Platform — AI Agent

This branch (`ai-agent`) extends the original DB Reliability & Incident Response Platform with an LLM-powered troubleshooting agent for PostgreSQL, built from the ground up: real tool-calling, retrieval-augmented generation, a Model Context Protocol server/client, an automated evaluation harness, and full request-level observability.

## Why This Exists

The original platform monitors databases and raises alerts. This agent goes a step further: given a plain-English question about database health, it reasons through the problem using real tools, retrieves guidance from the platform's own runbooks, and produces a grounded, specific answer — the same way a database engineer would investigate an issue manually.

The scope was deliberately narrowed to PostgreSQL only, rather than all three original databases, to keep the AI-specific complexity isolated while learning agent-building concepts for the first time, rather than tripling the surface area for no added benefit.

## Architecture

```
        User
         │
         ▼
     FastAPI (/ask)
         │
         ▼
      AI Agent  ── Reason → Act → Observe loop (Groq LLM)
         │
   ┌─────┼──────────┬─────────────┐
   ▼     ▼          ▼             ▼
Health  Query      Metrics       RAG
Check   Tool       Tool          Tool
 Tool     │          │             │
   │      ▼          ▼             ▼
   │  PostgreSQL  ClickHouse   pgvector
   │  (read-only               (runbook
   │   role)                    retrieval)
   ▼
PostgreSQL
(health checks)
```

Deployed on Kubernetes with PersistentVolumeClaims and Secrets, managed with GitOps continuous delivery via ArgoCD.

## The Four Tools

1. **Health Check Tool** — reuses the original platform's real diagnostic functions (`check_connection_usage`, `check_idle_transactions`).
2. **Query Tool** — lets the agent write and execute its own SQL, protected by two independent safety layers: a regex-based keyword filter (rejecting anything but a plain `SELECT`) and a database role granted `SELECT`-only permissions. Both were adversarially tested, including a direct attempt to have the agent drop a table.
3. **Metrics Tool** — queries historical trend data from ClickHouse.
4. **RAG Tool** — embeds the platform's 7 operational runbooks into a `pgvector` column inside PostgreSQL, chunked along their own natural markdown section boundaries (Symptoms, Causes, Diagnosis, Resolution, Prevention), and retrieves the most relevant chunks via cosine similarity for any given question.

## MCP (Model Context Protocol)

A standalone, genuine MCP server (`mcp_server.py`) exposes the Health Check Tool using the official `mcp` Python SDK, running over stdio. A separate MCP client (`mcp_client_test.py`) launches it as a subprocess, performs a real protocol handshake, discovers the tool dynamically at runtime with zero hardcoded knowledge of what the server offers, and calls it — receiving a real result from a live PostgreSQL database. This is kept as a standalone proof of concept, deliberately separate from the main agent's tool-calling loop.

## Evaluation

A golden dataset of realistic questions (`golden_dataset.py`), each with an expected tool and expected keywords, is run against the live agent (`run_eval.py`) using a non-invasive recorder pattern that wraps each real tool without changing its behavior. This harness caught three genuine defects during development, including a `Decimal` JSON-serialization bug and a text-normalization gap in the test itself (a "smart" curly apostrophe not matching a straight one).

## Observability

Every reasoning step, tool call, token count, and latency measurement is logged into a dedicated ClickHouse table (`agent_traces`), grouped by a unique `trace_id` per question. Logging failures are caught and never allowed to interrupt the actual user-facing answer.

## Real Bugs Found and Fixed

- **The same serialization bug, three times** — `datetime`, then `timedelta`, then `Decimal` objects each broke `json.dumps()` in turn, one per real query touching a different PostgreSQL column type. Eventually resolved with a general-purpose fallback: `json.dumps(obj, default=str)`.
- **A genuine false positive in the security filter** — a legitimate query containing the word "granted" was rejected, since the original filter used plain substring matching against the forbidden keyword `GRANT`. Fixed using a regex word-boundary check (`\bGRANT\b`).
- **A self-referencing diagnostic query** — a query checking `pg_stat_activity` for long-running sessions found only itself, since it hadn't excluded its own PID. Fixed with `pid <> pg_backend_pid()`.
- **A documented case of low groundedness, high correctness** — one real run produced a final answer containing substantially more detail than what RAG actually retrieved, a genuine, observed instance of the model blending retrieved context with general knowledge rather than staying strictly grounded.

## Multi-Cloud Deployment

This same application was independently deployed to both AWS-integrated local/Kubernetes infrastructure and to **Microsoft Azure** (AKS, Azure Container Registry, Key Vault, Azure Monitor), provisioned via Terraform's `azurerm` provider. Real, Azure-specific issues were diagnosed and resolved along the way, including a PostgreSQL storage-initialization conflict on Azure Disk, an AKS-to-ACR image-pull authorization gap resolved via managed identity role assignment, and a container-log schema mismatch between `ContainerLog` and `ContainerLogV2` in Azure Monitor.

## Running This Branch

```bash
git checkout ai-agent
cd agent
pip install -r requirements.txt
python main.py
```

Requires a running PostgreSQL instance with the `vector` extension enabled, a ClickHouse instance, and a `GROQ_API_KEY` set in `.env`. See `k8s/` for Kubernetes manifests and `azure_prac/` for the Azure-specific Terraform configuration.

Test via the interactive API docs at `http://localhost:8000/docs`.

## Known Limitations

- MCP is a standalone proof of concept, not integrated into the main agent's tool-calling loop.
- The agent has no persistent conversation memory across separate questions.
- Evaluation is keyword-based rather than using LLM-as-judge, a deliberate choice given the narrow, predictable vocabulary of database diagnostics — worth revisiting for more nuanced groundedness checks.
