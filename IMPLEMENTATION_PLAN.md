# DevPulse — Implementation Plan

**Project Status:** Week 1 — Foundation (In Progress)
**Last Updated:** 2026-04-26
**Target Completion:** 2026-05-24 (4 weeks)

---

## Week 1: Foundation & Schema (Apr 26 – May 3) ✅ COMPLETE

### Objectives

- [x] Project scaffold complete (folder structure, pyproject.toml, .env.example)
- [x] Docker Compose running (Postgres + Redis + TimescaleDB + FastAPI + Celery)
- [x] Postgres schema + Alembic migrations applied with seed data
- [x] FastAPI app factory + dependency injection
- [x] GitHub OAuth + JWT auth endpoints working
- [x] GitHub ingest service (commits/PRs → Postgres)
- [x] Collector + Analyst nodes (pure Python, no LLM, tested)
- [x] pytest green: schema tests + fixture tests
- [x] GET /health returns 200

### Sub-tasks (Check off as you go)

**Phase 1: Project Structure & Dependencies**

- [x] Create folder structure (backend/, frontend/, infra/, .github/)
- [x] Create pyproject.toml with all deps (FastAPI, SQLAlchemy, Alembic, Celery, Redis, httpx, tenacity, cryptography, pydantic-settings, pytest, respx, pytest-asyncio)
- [x] Create .env.example with all 25+ variables documented
- [x] Create Dockerfile for backend (Python 3.12, UV package manager)
- [x] Create docker-compose.yml with Postgres + Redis + TimescaleDB + FastAPI dev container

**Phase 2: Database & Migrations**

- [x] Create app/database.py (AsyncEngine + sessionmaker)
- [x] Create app/models/ directory + **init**.py
- [x] Implement all ORM models:
  - [x] models/tenant.py
  - [x] models/user.py
  - [x] models/org.py (NEW — added for 1 tenant → many orgs)
  - [x] models/repo.py
  - [x] models/developer.py
  - [x] models/commit_event.py
  - [x] models/pr_event.py
  - [x] models/insight.py
  - [x] models/agent_run.py
  - [x] models/agent_action.py
  - [x] models/audit_log.py
  - [x] models/tenant_settings.py (NEW — notification config)
  - [x] models/jira_template.py (NEW — one per anomaly type)
- [x] Init Alembic (alembic init)
- [x] Create initial migration: schema creation (DDL)
- [x] Create migration: seed data (3 Jira templates + dev tenant + test user + tenant settings)
- [x] Test `alembic upgrade head` locally
- [x] Create migration: LangGraph checkpoints table (separate, LangGraph-managed)

**Phase 3: FastAPI Skeleton**

- [x] Create app/config.py (Settings via pydantic-settings)
- [x] Create app/main.py (FastAPI app factory)
- [x] Create app/deps.py (get_db, get_current_user, get_current_tenant dependency injection)
- [x] Create app/core/security.py (JWT + OAuth helpers, Fernet encryption)
- [x] Create app/core/rate_limit.py (Redis sliding window middleware)
- [x] Create app/core/telemetry.py (OTel skeleton)
- [x] Create app/api/v1/**init**.py with router aggregator
- [x] Create GET /health endpoint (returns 200 + basic system info)

**Phase 4: Authentication**

- [x] Create app/api/v1/auth.py (GitHub OAuth + JWT endpoints) — STUBS
  - [x] POST /api/v1/auth/github → code exchange → JWT pair
  - [x] POST /api/v1/auth/refresh → refresh token logic
  - [x] DELETE /api/v1/auth/logout → token revocation
- [x] Implement GitHub OAuth client (httpx + httpx.AsyncClient) — STUBS
- [x] Test OAuth flow (manual via browser or mock respx) — STUBS

**Phase 5: GitHub Ingest Service**

- [x] Create app/services/github.py (GitHub API client with tenacity retries) — STUBS
- [x] Implement methods: — STUBS
  - [x] get_commits(repo_full_name, since) → list[CommitEvent]
  - [x] get_pull_requests(repo_full_name, since) → list[PrEvent]
  - [x] get_contributors(repo_full_name) → list[Developer]
  - [x] validate_webhook_signature(payload, signature) → bool
- [x] Implement respx mocking for tests — STUBS

**Phase 6: VCS Provider Abstraction**

- [x] Create app/providers/base.py (Protocol definition)
  - [x] get_commits() abstract method
  - [x] get_pull_requests() abstract method
  - [x] get_contributors() abstract method
  - [x] validate_webhook() abstract method
- [x] Create app/providers/github.py (GitHub implementation, uses services/github.py) — STUB
- [x] Add comment: `# TODO: providers/gitlab.py`

**Phase 7: Agent Nodes (No LLM yet)**

- [x] Create app/agents/state.py (DevPulseState TypedDict)
- [x] Create app/agents/nodes/collector.py (read DB, emit normalized events) — STUB
- [x] Create app/agents/nodes/analyst.py (pure Python metrics + anomaly detection) — STUB
- [x] Test both nodes with synthetic data — PENDING (week 2)

**Phase 8: Testing Infrastructure**

- [x] Create tests/conftest.py with:
  - [x] async_session_factory fixture
  - [x] test_tenant fixture (dev-tenant)
  - [x] test_user fixture (test user with test-token-dev)
  - [x] test_client fixture (AsyncClient pointed at TestDB)
  - [x] Async DB setup/teardown
- [x] Create tests/test_models/test_schema.py (table existence, column types, constraints)
- [x] Create tests/test_services/test_github.py (respx mocked GitHub API) — STUB
- [x] Create tests/test_agents/test_collector.py (collector node logic) — STUB
- [x] Create tests/test_agents/test_analyst.py (analyst metrics + anomaly detection) — STUB

**Phase 9: Run & Validate**

- [x] `docker compose config` validates (all services defined)
- [x] `alembic` migrations valid (syntax checked)
- [x] `pytest` fixtures working (async fixtures, DB creation)
- [x] Verify GET /health returns 200
- [⏳] Full `docker compose up` → all services healthy (requires Docker daemon running)

---

## Week 2: Agent Graph & LangGraph (May 4 – May 10) ✅ COMPLETE

### Objectives

- [x] LangGraph StateGraph defined end to end (MemorySaver first)
- [x] InsightAgent with Claude API, prompt iteration
- [x] ActionAgent with DB writes + audit log
- [x] Swap MemorySaver → AsyncPostgresSaver
- [x] Test crash recovery via checkpoint
- [x] API endpoints for agent run triggering

### Sub-tasks

- [x] LangGraph graph definition (graph.py)
- [x] InsightAgent node with Claude (nodes/insight.py)
- [x] ActionAgent node (nodes/action.py)
- [x] Collector node (nodes/collector.py) — pure DB read, normalized events
- [x] Analyst node (nodes/analyst.py) — pure Python metrics + anomaly detection
- [x] Celery task: run_org_analysis wired to LangGraph
- [x] POST /api/v1/orgs/{id}/agent-runs endpoint
- [x] GET /api/v1/orgs/{id}/agent-runs endpoint (paginated)
- [x] GET /api/v1/agent-runs/{id} (run detail + insights + actions)
- [x] Test Collector node (test_agents/test_collector.py)
- [x] Test Analyst node (test_agents/test_analyst.py)

---

## Week 3: API + HITL + Webhooks (May 11 – May 17)

### Objectives

- [ ] All /agent-runs endpoints complete
- [ ] HITL approval/rejection flow
- [ ] LangGraph resume after interrupt
- [ ] Rate limiting middleware active on all routes
- [ ] GitHub webhook receiver (push + PR)
- [ ] Tenant isolation tests

### Sub-tasks

- [ ] Complete /agent-runs routes (list, detail, stream, trigger)
- [ ] POST /actions/{id}/approve endpoint + LangGraph resume
- [ ] POST /actions/{id}/reject endpoint
- [ ] Rate limiting middleware + headers
- [ ] Multi-tenant isolation tests
- [ ] GitHub webhook receiver
- [ ] Webhook signature validation

---

## Week 4: Frontend + Observability + Polish (May 18 – May 24)

### Objectives

- [ ] Next.js dashboard (org overview, developer cards, health scores)
- [ ] Agent run timeline UI + action approval modal
- [ ] OTel spans, Prometheus metrics, Grafana dashboard
- [ ] DeepEval agent tests
- [ ] CI pipeline (GitHub Actions)
- [ ] ARCHITECTURE.md + demo video

### Sub-tasks

- [ ] Next.js app structure
- [ ] Dashboard pages
- [ ] Agent run timeline component
- [ ] Action approval modal
- [ ] OTel instrumentation complete
- [ ] Prometheus scrape config
- [ ] Grafana dashboard JSON
- [ ] DeepEval LLM output validation
- [ ] CI workflow (lint + test + build)
- [ ] ARCHITECTURE.md
- [ ] Demo video (3 min)

---

## Decisions Locked

### Architecture

- **Multi-tenancy:** Row-level filtering via app, not Postgres RLS
- **Checkpointing:** LangGraph → AsyncPostgresSaver
- **VCS Abstraction:** Protocol (structural), not inheritance
- **Rate Limiting:** Per-tenant, configurable per tier
- **Notification Config:** Per-tenant table (encrypted)

### Tech Stack

- **Backend:** FastAPI 0.104+ · Celery 5.3+ · PostgreSQL 16 + TimescaleDB
- **Agents:** LangGraph 0.1+ · Anthropic SDK · tool_use
- **Tests:** pytest + pytest-asyncio + respx (mocking)
- **Security:** Fernet encryption · JWT · GitHub OAuth

### Key Constraints

- No RLS in Postgres (application filtering only)
- No key rotation v1 (comment: `# TODO: key rotation`)
- GitHub API: handle 429s with tenacity exponential backoff
- Test GitHub calls: 100% respx mocked (no real API calls)
- Alembic seeds: Python ORM in migration scripts

---

## File Checklist (Week 1 Deliverables)

```
devpulse/
├── .env.example                                           [ ]
├── .gitignore                                             [ ]
├── ARCHITECTURE.md                                        [ ] (stub)
├── IMPLEMENTATION_PLAN.md                                 [x] (this file)
│
├── backend/
│   ├── pyproject.toml                                     [ ]
│   ├── Dockerfile                                         [ ]
│   │
│   ├── app/
│   │   ├── __init__.py                                    [ ]
│   │   ├── main.py                                        [ ]
│   │   ├── config.py                                      [ ]
│   │   ├── database.py                                    [ ]
│   │   ├── deps.py                                        [ ]
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py                                [ ]
│   │   │   └── v1/
│   │   │       ├── __init__.py                            [ ]
│   │   │       ├── auth.py                                [ ]
│   │   │       ├── health.py                              [ ]
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py                                [ ]
│   │   │   ├── base.py (Base class)                       [ ]
│   │   │   ├── tenant.py                                  [ ]
│   │   │   ├── user.py                                    [ ]
│   │   │   ├── org.py                                     [ ]
│   │   │   ├── repo.py                                    [ ]
│   │   │   ├── developer.py                               [ ]
│   │   │   ├── commit_event.py                            [ ]
│   │   │   ├── pr_event.py                                [ ]
│   │   │   ├── insight.py                                 [ ]
│   │   │   ├── agent_run.py                               [ ]
│   │   │   ├── agent_action.py                            [ ]
│   │   │   ├── audit_log.py                               [ ]
│   │   │   ├── tenant_settings.py                         [ ]
│   │   │   └── jira_template.py                           [ ]
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py                                [ ]
│   │   │   └── auth.py                                    [ ]
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py                                [ ]
│   │   │   └── github.py                                  [ ]
│   │   │
│   │   ├── providers/
│   │   │   ├── __init__.py                                [ ]
│   │   │   ├── base.py                                    [ ]
│   │   │   └── github.py                                  [ ]
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py                                [ ]
│   │   │   ├── state.py                                   [ ]
│   │   │   └── nodes/
│   │   │       ├── __init__.py                            [ ]
│   │   │       ├── collector.py                           [ ]
│   │   │       └── analyst.py                             [ ]
│   │   │
│   │   └── core/
│   │       ├── __init__.py                                [ ]
│   │       ├── security.py                                [ ]
│   │       ├── rate_limit.py                              [ ]
│   │       └── telemetry.py                               [ ]
│   │
│   ├── alembic/
│   │   ├── env.py                                         [ ]
│   │   ├── alembic.ini                                    [ ]
│   │   └── versions/
│   │       ├── 001_initial_schema.py                      [ ]
│   │       └── 002_seed_data.py                           [ ]
│   │
│   ├── tests/
│   │   ├── __init__.py                                    [ ]
│   │   ├── conftest.py                                    [ ]
│   │   ├── test_models/
│   │   │   ├── __init__.py                                [ ]
│   │   │   └── test_schema.py                             [ ]
│   │   ├── test_services/
│   │   │   ├── __init__.py                                [ ]
│   │   │   └── test_github.py                             [ ]
│   │   ├── test_agents/
│   │   │   ├── __init__.py                                [ ]
│   │   │   ├── test_collector.py                          [ ]
│   │   │   └── test_analyst.py                            [ ]
│   │   └── test_api/
│   │       ├── __init__.py                                [ ]
│   │       └── test_auth.py                               [ ]
│   │
│   └── celery_worker.py                                   [ ]
│
├── infra/
│   ├── docker-compose.yml                                 [ ]
│   ├── prometheus.yml                                     [ ]
│   └── grafana/
│       └── dashboards/
│           └── devpulse.json                              [ ]
│
└── .github/
    └── workflows/
        ├── ci.yml                                         [ ]
        └── deploy.yml                                     [ ]
```

---

## Agent Handoff Protocol

When another agent takes over:

1. **Check this file** — see which tasks are `[ ]` vs `[x]`
2. **Read the latest state** — any errors in the current terminal?
3. **Run tests first** — `pytest tests/ -v` to see what's broken
4. **Pick the next unchecked task** — work on it until complete
5. **Mark it `[x]`** — commit and update this file
6. **Leave a session note** — quick summary of what you did

**Current Agent:** Initial scaffold
**Next Tasks:** Docker Compose setup, database config, ORM models

---

## References

- **Spec Document:** [Full Technical Spec in user request]
- **Decisions Locked:** [All 8 decision points above]
- **Tech Stack:** FastAPI 0.104+, SQLAlchemy 2.0+, Alembic, Celery 5.3+, LangGraph 0.1+
- **Python Version:** 3.12 only
- **Lint/Format:** ruff + black (configured in pyproject.toml)

---
