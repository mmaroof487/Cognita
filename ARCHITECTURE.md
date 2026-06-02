# Axon Architecture

**Status:** v1 Foundation Complete

## Overview

Axon is a multi-tenant SaaS that ingests GitHub/GitLab activity, runs agentic analysis on developer patterns, and autonomously surfaces weekly insights with human-in-the-loop escalation for critical actions.

## High-Level Components

### Backend

- **FastAPI** — REST API + SSE for agent status streaming
- **SQLAlchemy** — Async ORM with PostgreSQL + TimescaleDB for time-series
- **LangGraph** — Stateful multi-agent orchestration with crash recovery
- **Celery** — Async job queue + scheduled analysis runs
- **Redis** — Job queue, caching, rate limiting

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
- **commit_events** — Time-series commits
- **pr_events** — Pull request metrics
- **agent_runs** — LangGraph execution history
- **insights** — Agent-generated findings
- **agent_actions** — HITL-gated actions (Jira, Slack, email)
- **audit_log** — Immutable append-only log

## Agent Architecture (LangGraph)

The agents operate as a StateGraph sharing a TypedDict (`AxonState`), which tracks state like `insights`, `actions_queued`, `errors`, and token tracking.

```
Collector Node
  └→ reads DB directly using SQLAlchemy, gathers PRs & commits within window
     Outputs to state: `commits`, `prs`

Analyst Node
  └→ computes metric aggregations pure Python (no LLM).
     Outputs to state: `metrics` (grouped by developer)

Insight Node
  └→ Claude (via LangChain ChatAnthropic) generates human-readable insights & identifies burnout/churn/slow-review.
     Outputs to state: `insights` + LLM tokens usage

Action Node
  └→ generates concrete `AgentAction` records. Halts via `interrupt_before` for HITL.
     Outputs to state: `actions_queued`
```

Checkpointing: `AsyncPostgresSaver` ensures state survives crashes and allows resumption upon HITL approval.

## Multi-Tenancy

- **Application-layer RLS** (not Postgres RLS) via `tenant_id` filtering in all queries via FastAPI dependencies (`get_current_tenant`).
- Rate limiting per tenant tier using Redis sliding window implementation.

## Security

- **JWT** access + refresh tokens
- **Fernet** symmetric encryption for sensitive data at rest (GitHub PAT). Key rotation not implemented in v1.
- **GitHub OAuth** for user onboarding
- **Bounded autonomy** — Action Agent cannot delete/modify code, only create tickets + notify.
- **Audit log** — Every agent action recorded.

## Deployment

- **Docker Compose** (local dev) → Postgres, Redis, FastAPI, Celery, Grafana.
- Testing is done mocking HTTP calls via `respx` and skipping real GitHub interaction.
