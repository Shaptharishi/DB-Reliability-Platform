# DB Reliability & Incident Response Platform

A lightweight monitoring and diagnostic system for PostgreSQL, MySQL, and Redis. Instead of just alerting that "something is wrong," it encodes real operational judgment — the same diagnostic steps a support/SRE engineer runs manually — and turns them into automated, continuously-running checks with human-readable root-cause diagnoses and linked runbooks.

This branch (`main`) contains the original, local Docker Compose deployment. See [Other Branches](#other-branches) below for the AWS/Terraform infrastructure, the Kubernetes deployment, and a separate LLM-powered agent built on top of this same platform.

## The Problem

Most database incidents follow repeatable patterns: connection exhaustion, replication lag, table bloat, slow queries, stuck idle-in-transaction sessions. Diagnosing these usually means an engineer manually running the same handful of diagnostic queries every single time an incident occurs. This project automates that diagnostic process itself — not just detection, but the actual reasoning a human would apply.

## What It Does

Every 30 seconds, the collector connects to PostgreSQL, MySQL, and Redis and runs a set of real diagnostic checks against each:

**PostgreSQL** — connection usage, replication lag (via `pg_stat_replication`, using WAL byte-diff rather than wall-clock time to avoid false positives on idle primaries), idle-in-transaction sessions, table bloat (dead tuple ratio).

**MySQL** — connection usage, replication thread status (IO thread vs SQL thread checked separately, since they fail for different reasons), recurring slow query patterns via `performance_schema`, active InnoDB transactions.

**Redis** — memory usage against `maxmemory`, eviction policy configuration, connected clients and replication role.

Each result passes through a rule engine that encodes real operational thresholds and judgment (e.g. distinguishing "no memory limit configured" from "0% memory used" — two very different, easily-confused states). When a rule fires, the system:

1. Writes the alert permanently to ClickHouse (for historical analysis)
2. Sends a formatted Slack notification with severity, message, and a linked runbook
3. Every raw metric — whether or not it triggered an alert — is also stored in ClickHouse, building a continuous historical trend rather than only point-in-time snapshots
4. Grafana reads metrics directly from ClickHouse to provide live dashboards showing connection usage, memory usage, replication health, and historical trends across all monitored databases.

## Architecture

```
 ┌─────────────┐   ┌─────────┐   ┌───────┐
 │ PostgreSQL  │   │  MySQL  │   │ Redis │
 └──────┬──────┘   └────┬────┘   └───┬───┘
        │               │            │
        └───────┬───────┴────────────┘
                │
        ┌───────▼────────┐
        │  Python        │
        │  Collector +   │  ← polls every 30s, applies rules
        │  Rule Engine   │
        └───────┬────────┘
                │
        ┌───────────────┐
        │  ClickHouse   │
        │ Metrics/Alerts│
        └───────┬───────┘
                │
      ┌─────────┴─────────┐
      │                   │
┌─────▼─────┐      ┌──────▼──────┐
│ Grafana   │      │ Slack       │
│ Dashboards│      │Notifications│
└───────────┘      └─────────────┘
```

Every service runs in its own container, orchestrated with Docker Compose, with health checks gating startup order and application-level retry logic handling runtime reconnection if a dependency becomes temporarily unavailable after startup.

## Why These Specific Technology Choices

- **ClickHouse for metrics storage**: this is a genuinely OLAP access pattern — high-volume, timestamped, numeric data, queried mostly via aggregates over time ranges. A row-based OLTP database would work but isn't the right tool for this specific shape of data.
- **Slack webhook for alerting**: the standard, real-world integration point every company in this space actually uses for exactly this kind of ops notification.
- **Docker healthchecks *and* application-level retry logic**: these solve two different problems. Healthchecks ensure clean startup ordering. Retry logic handles a dependency becoming unavailable later, mid-operation, after the system has already been running — healthchecks alone don't cover that case.
- **Runbooks as version-controlled markdown**: every alert links to a specific, structured runbook (symptoms → likely causes → diagnosis steps → resolution → prevention), mirroring how real support/SRE teams document operational knowledge.

## Running It

```bash
git clone https://github.com/Shaptharishi/DB-Reliability-Platform
cd db-reliability-platform
cp .env.example .env   # add your own Slack webhook URL
docker compose up --build
```

That's the entire setup. Docker Compose builds the collector, pulls official images for PostgreSQL/MySQL/Redis/ClickHouse, and starts everything together on a shared network. The collector automatically creates its own ClickHouse schema on first run — no manual database setup required.

## Querying the History

```sql
-- Connection usage trend for PostgreSQL over the last 24 hours
SELECT ts, metric_value
FROM monitoring.metrics
WHERE db_type = 'postgresql' AND metric_name = 'percent_used'
ORDER BY ts DESC
LIMIT 100;

-- All critical alerts in the last week
SELECT ts, rule, message
FROM monitoring.alerts
WHERE severity = 'critical'
ORDER BY ts DESC;
```

## Other Branches

This repository also contains several other deployment approaches for this same platform, plus a separate AI agent extension:

- **[`versions`](../../tree/versions)** — the same platform deployed to real AWS infrastructure (RDS, ElastiCache, EC2), provisioned entirely as code with Terraform, with automated build-and-deploy via GitHub Actions CI/CD.
- **[`version-k3s`](../../tree/version-k3s)** — the same AWS infrastructure as `versions`, deployed to Kubernetes (k3s) instead of Docker Compose, demonstrating container orchestration and self-healing.
- **[`version-ai_integration`](../../tree/version-ai_integration)** — exploratory work extending the monitoring stack with Prometheus and an incident simulator.
- **[`ai-agent`](../../tree/ai-agent)** — a genuine LLM-powered troubleshooting agent built on top of this platform: real tool-calling, retrieval-augmented generation over the platform's own runbooks, a Model Context Protocol server/client, an automated evaluation harness, and full request-level observability. Deployed on Kubernetes with GitOps delivery via ArgoCD, and independently redeployed to Microsoft Azure to prove genuine cloud portability.

Each branch has its own `README.md` with full architecture details and a real, honest record of the production issues hit and fixed while building it.

## What I'd Add Next

- MongoDB as an additional monitored target, extending the same collector/rule pattern
- Explicit SLIs/SLOs and error budget calculations against the real historical metrics already stored in ClickHouse
- Persistent volume storage on the Kubernetes deployment, replacing the current `emptyDir` approach
- Integrating the `ai-agent` branch's troubleshooting capability directly into this platform's alerting flow, rather than as a separate application

## My Role

Solo project — architecture, all collector/rule/storage logic, infrastructure-as-code, container orchestration across Docker Compose and Kubernetes, and the AI agent extension, across both AWS and Azure.
