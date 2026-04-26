# DevPulse Architecture

**Status:** Week 1 Foundation — Final architecture doc in week 4

## Overview

DevPulse is a multi-tenant SaaS that ingests GitHub/GitLab activity, runs agentic analysis on developer patterns, and autonomously surfaces weekly insights with human-in-the-loop escalation for critical actions.

## High-Level Components

### Backend

- **FastAPI** — REST API + WebSocket for agent status streaming
- **SQLAlchemy** — Async ORM with PostgreSQL + TimescaleDB for time-series
- **LangGraph** — Stateful multi-agent orchestration with crash recovery
- **Celery** — Async job queue + scheduled analysis runs
- **Redis** — Job queue, caching, rate limiting

### Frontend

- **Next.js** — Dashboard, developer insights, HITL approval UI
- **Recharts** — Activity visualizations
- **TailwindCSS** — Styling

### Observability

- **OpenTelemetry** — Distributed tracing
- **Prometheus** — Metrics collection
- **Grafana** — Dashboards

## Database Schema

See `backend/alembic/versions/001_initial_schema.py` for full DDL.

Key tables:

- **tenants** — Multi-tenant isolation anchor
- **users** — Authenticated users per tenant
- **orgs** — GitHub organizations per tenant
- **repos** — Repositories
- **developers** — Tracked contributors (upserted from commits)
- **commit_events** — Hypertable for time-series commits
- **pr_events** — Pull request metrics
- **agent_runs** — LangGraph execution history
- **insights** — Agent-generated findings
- **agent_actions** — HITL-gated actions (Jira, Slack, email)
- **audit_log** — Immutable append-only log

## Agent Architecture (LangGraph)

```
Collector Agent
  └→ reads DB, emits normalized events

Analyst Agent
  └→ computes metrics, detects anomalies (no LLM)

Insight Agent
  └→ Claude generates human-readable summaries

Action Agent
  └→ queues actions, applies HITL gate
```

Checkpointing: `AsyncPostgresSaver` → survives crashes, resumable on failure.

## Multi-Tenancy

- **Application-layer RLS** (not Postgres RLS) via `tenant_id` filtering in all queries
- Every table has `tenant_id` FK to anchor
- Rate limiting per tenant tier: free (60 req/min), pro (300), enterprise (1000)

## Security

- **JWT** access + refresh tokens
- **Fernet** encryption for sensitive data at rest (GitHub PAT, SMTP password, Jira API token)
- **GitHub OAuth** for user onboarding
- **Bounded autonomy** — Action Agent cannot delete/modify code, only create tickets + notify
- **Audit log** — Every agent action recorded for compliance

## Deployment

- **Docker Compose** (local dev) → Postgres, Redis, TimescaleDB, FastAPI, Celery, Grafana
- **GitHub Actions** (CI) → lint, test, build
- **TBD** (production) — likely Docker + Kubernetes or managed PaaS

## Week-by-Week Build

- **Week 1** — Schema, auth, health check ✓ (in progress)
- **Week 2** — LangGraph agents, Celery tasks
- **Week 3** — API endpoints, HITL flow, webhooks
- **Week 4** — Frontend, OTel, tests, demo

---

Full spec: See project root `idea.md` and `pitch.md`.
