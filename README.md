# DevPulse — AI-Powered Developer Productivity Intelligence Platform

A multi-tenant SaaS that ingests GitHub/GitLab activity, runs agentic analysis, and autonomously surfaces weekly insights with human-in-the-loop escalation for critical actions.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12 (local dev)
- GitHub OAuth app credentials (get at https://github.com/settings/developers)
- Anthropic API key (get at https://console.anthropic.com/account/keys)

### Local Development (Docker)

```bash
# 1. Copy environment template and fill in required values
cp .env.example .env
# Edit .env and fill in:
#   - GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET (from GitHub OAuth app)
#   - ANTHROPIC_API_KEY (from Anthropic console)
#   - Other optional notification integrations (Slack, Jira, SMTP)

# 2. Start services
docker compose -f infra/docker-compose.yml up

# 3. API is running at http://localhost:8000
# 4. Check health: curl http://localhost:8000/health

# 5. API docs (Swagger): http://localhost:8000/docs
# 6. Prometheus metrics: http://localhost:9090
# 7. Grafana: http://localhost:3001 (admin/admin)
```

### Local Development (Python venv)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Database setup (requires Postgres running separately)
export DATABASE_URL=postgresql://devpulse:devpulse@localhost/devpulse
export DATABASE_URL_SYNC=postgresql://devpulse:devpulse@localhost/devpulse
alembic upgrade head

# Run tests
pytest tests/ -v

# Start FastAPI dev server
uvicorn app.main:app --reload
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for complete architecture overview.

### Tech Stack

**Backend:**

- FastAPI 0.104+
- SQLAlchemy 2.0+ with AsyncPG
- PostgreSQL 16 + TimescaleDB
- Celery 5.3+ + Redis
- LangGraph 0.1+
- Anthropic Claude SDK

**Frontend:**

- Next.js (week 4)
- Recharts
- TailwindCSS

**Observability:**

- OpenTelemetry
- Prometheus
- Grafana

## Project Structure

```
devpulse/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (week 2-3)
│   │   ├── models/          # SQLAlchemy ORM ✓
│   │   ├── services/        # Business logic (GitHub, ingest, etc.)
│   │   ├── agents/          # LangGraph agent nodes (week 2-3)
│   │   ├── core/            # JWT, encryption, rate limiting ✓
│   │   ├── config.py        # Settings ✓
│   │   ├── database.py      # AsyncEngine setup ✓
│   │   ├── main.py          # FastAPI app factory ✓
│   │   └── deps.py          # Dependency injection ✓
│   ├── alembic/             # Database migrations ✓
│   ├── tests/               # Pytest fixtures & tests ✓
│   ├── pyproject.toml       # Dependencies ✓
│   └── Dockerfile           # Container image ✓
├── infra/
│   ├── docker-compose.yml   # Local dev stack ✓
│   ├── prometheus.yml       # Metrics config (week 4)
│   └── grafana/             # Dashboards (week 4)
├── .env.example             # Environment template ✓
├── ARCHITECTURE.md          # Architecture docs ✓
└── IMPLEMENTATION_PLAN.md   # Build timeline & checklist ✓
```

## Development Workflow

### Week 1 — Foundation ✓

- [x] Folder structure
- [x] Docker Compose setup
- [x] PostgreSQL schema + Alembic migrations
- [x] FastAPI app factory + dependencies
- [x] GitHub OAuth + JWT setup
- [x] GitHub ingest service (stub)
- [x] Collector & Analyst nodes (stub)
- [x] Pytest fixtures + schema tests
- [x] GET /health endpoint

### Week 2 — Agents ✓

- [x] LangGraph StateGraph end-to-end
- [x] Collector node (pure DB read, normalized events)
- [x] Analyst node (pure Python metrics + anomaly detection)
- [x] InsightAgent with Claude LLM
- [x] ActionAgent with HITL gate + DB writes
- [x] Celery task: run_org_analysis with LangGraph
- [x] Celery beat: weekly scheduled analysis
- [x] API endpoints: trigger, list, detail agent runs
- [x] Tests: Collector & Analyst nodes

### Week 3 — API + HITL (In Progress)

- [ ] GitHub ingest service (real API calls)
- [ ] HITL approval/rejection endpoints
- [ ] Rate limiting middleware active
- [ ] GitHub webhook receiver
- [ ] Multi-tenant isolation tests

### Week 4 — Frontend + Observability

- [ ] Next.js dashboard
- [ ] Agent timeline UI
- [ ] OTel traces + Prometheus metrics
- [ ] Grafana dashboards
- [ ] DeepEval LLM tests
- [ ] CI/CD pipeline
- [ ] Demo video + ARCHITECTURE.md finalization

## API Endpoints (Plan)

```
Auth
  POST /api/v1/auth/github          GitHub OAuth callback
  POST /api/v1/auth/refresh         Refresh JWT
  DELETE /api/v1/auth/logout        Logout

Orgs
  GET  /api/v1/orgs                 List orgs
  POST /api/v1/orgs                 Connect new GitHub org
  GET  /api/v1/orgs/{id}            Org detail + repos
  DELETE /api/v1/orgs/{id}          Disconnect org

Developers
  GET  /api/v1/developers/{id}      Developer detail + metrics
  GET  /api/v1/developers/{id}/insights  Developer insights

Insights
  GET  /api/v1/orgs/{id}/insights   Paginated insights

Agent Runs
  GET  /api/v1/orgs/{id}/agent-runs      List runs
  POST /api/v1/orgs/{id}/agent-runs      Trigger manual run
  GET  /api/v1/agent-runs/{id}           Run detail
  GET  /api/v1/agent-runs/{id}/stream    SSE stream

Actions (HITL)
  GET  /api/v1/orgs/{id}/actions    Pending actions
  POST /api/v1/actions/{id}/approve Approve action
  POST /api/v1/actions/{id}/reject  Reject action
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models/test_schema.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run async tests
pytest tests/ -v -m asyncio
```

## Contributing

See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for task assignments and build order.

## Key Design Decisions

1. **Multi-tenancy** — Application-layer RLS (not Postgres RLS) for simplicity
2. **Agent Checkpointing** — AsyncPostgresSaver for crash recovery
3. **HITL Gate** — LangGraph interrupts on critical actions for human approval
4. **Rate Limiting** — Redis sliding window per tenant tier
5. **Encryption** — Fernet for tokens/credentials, no key rotation in v1
6. **Tests** — 100% respx mocked (no real GitHub API calls)

## FAQ

**Q: How do I run tests?**
A: `cd backend && pytest tests/ -v` (requires Docker or local Postgres)

**Q: How do I add a new endpoint?**
A: Create endpoint in `backend/app/api/v1/{feature}.py`, import in `backend/app/api/v1/__init__.py`, include router in `app/main.py`.

**Q: How do I trigger an agent run manually?**
A: POST to `/api/v1/orgs/{org_id}/agent-runs` (week 3).

**Q: Where are secrets stored?**
A: In `.env` file (git-ignored). Use Fernet encryption at app layer for sensitive DB data.

---

**Status:** Week 1 Foundation Complete ✓
**Next:** Week 2 — LangGraph agents + Celery tasks
**Demo Video:** Coming week 4

# Cognita
