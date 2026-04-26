Here's how to explain DevPulse in an interview — covering every angle an interviewer will hit.

---

# DevPulse — Interview Playbook

---

## The 30-Second Pitch (always lead with this)

> "DevPulse is a multi-tenant SaaS platform that ingests GitHub activity — commits, pull requests, code reviews — and runs a four-agent LangGraph pipeline to autonomously detect developer health signals like burnout risk, review bottlenecks, and code quality regressions. It surfaces those as insight cards on a dashboard and can automatically create Jira tickets or send Slack alerts — but only after a human approves critical actions. The backend is FastAPI with Celery for async job processing, TimescaleDB for time-series event storage, and Redis for job queuing and rate limiting. Every agent decision is traced with OpenTelemetry and logged to an immutable audit table."

That's your anchor. Everything else is elaboration.

---

## "Walk me through the architecture."

Start at the edges and work inward.

**Data flows in two ways.**

First, scheduled. Every Monday at 9AM, Celery Beat fires a task for every active tenant. Each task calls the GitHub API — pulls commits, PRs, and review events from the last 7 days — normalizes them into our Postgres schema, and then kicks off the LangGraph agent pipeline.

Second, real-time. GitHub sends webhook events on every push and every PR state change. Our `/webhooks/github` endpoint receives those, validates the HMAC signature, and enqueues a lightweight ingest task in Celery. That keeps the database current between scheduled runs.

**The backend is a FastAPI app.** It's stateless — no in-memory state — so we can run multiple instances behind a load balancer. Celery workers are separate processes connected to the same Redis broker. The API and workers both talk to Postgres and Redis, but nothing else is shared between them. That's what makes it horizontally scalable.

**Multi-tenancy is enforced at the database layer**, not the application layer. Every table has a `tenant_id` column. Every query has `WHERE tenant_id = :current_tenant`. We inject the current tenant from the JWT in a FastAPI dependency, so there's no way to accidentally query across tenant boundaries. No row-level security triggers needed — the ORM just always filters by tenant.

**The agent pipeline is LangGraph.** Four nodes: Collector, Analyst, Insight, Action. Each node receives and returns a typed state object. LangGraph checkpoints that state to Postgres after every node, so if the worker crashes mid-pipeline, the next restart picks up exactly where it left off — that's durable execution, not a retry from scratch.

---

## "Why LangGraph specifically? Why not CrewAI or just calling the API directly?"

Three reasons.

**Durable execution.** LangGraph builds agents that persist through failures and automatically resume from exactly where they left off. Our pipelines run over hundreds of developers' data. A single agent run might take 3–5 minutes. If the worker restarts mid-run, we cannot afford to redo all the GitHub API calls and LLM calls from scratch. LangGraph's PostgresSaver checkpoints state after every node — crash recovery is automatic.

**Human-in-the-loop as a first-class primitive.** When the Action Agent wants to create a Jira ticket — a write operation with real business consequences — we need a human to approve it. LangGraph's `interrupt()` call pauses the graph, serializes the state to Postgres, and waits. The frontend polls for `status: awaiting_human`. When the manager clicks Approve, our API resumes the graph by invoking it with the same `thread_id`. The graph state is saved using LangGraph's persistence layer, so execution can pause safely and resume later. This is not something you can bolt onto a plain async function easily.

**Explicit state and conditional routing.** The graph has a retry loop on the Insight node. If Claude returns malformed JSON — which happens — the node increments `retry_count` and loops back. The conditional edge checks: if `retry_count < 2` and insights are empty, go back to Insight; otherwise proceed to Action. That loop is a first-class citizen in LangGraph's graph model. In a linear chain, you'd have to implement that loop manually with try/except and it becomes untestable.

CrewAI would be faster to prototype but teams that start with CrewAI for prototyping often migrate to LangGraph when they need production-grade state management and conditional routing. We're building for production from day one, so LangGraph was the right call.

---

## "Tell me about the four agents. What does each one actually do?"

**Collector Agent — no LLM call.**

This is a pure database read. It takes the tenant ID and time window from the state, queries Postgres for all commit events, PR events, and developer metadata within that window, and returns them as lists in the state. No reasoning required — just data retrieval. I made a deliberate choice not to use an LLM here because it would be expensive and unnecessary. Deterministic operations should stay deterministic.

**Analyst Agent — no LLM call either.**

This is pure Python computation. It iterates over every developer's commits, calculates metrics: commit frequency, after-hours ratio, high-churn commit count, average PR merge time. Then it applies a scoring algorithm — start at 100, subtract penalties for each risk signal. After-hours ratio above 40% subtracts 25 points. Zero commits subtracts 30. Average merge time above 72 hours subtracts 20. The result is a health score between 0 and 100 per developer, plus a list of typed anomalies.

The reason I kept both these nodes LLM-free is cost and reliability. If I'm running this for 50 tenants with 20 developers each, that's 1000 developer profiles per week. Putting an LLM on data collection and metric computation would burn tokens for zero benefit.

**Insight Agent — this is where Claude runs.**

It takes the metrics and anomalies from state and makes one LLM call per developer who has anomalies, plus one team-level summary call. The prompt gives Claude the exact numbers — commit count, after-hours ratio, score — and asks for a structured JSON response: title, body, recommendation, severity. The prompt explicitly instructs Claude never to frame a developer as the problem — always frame it as a workload or process issue. That's a design decision about how this tool should treat engineers.

I parse the JSON response with a try/except. If parsing fails, I append to the `errors` list in state and increment `retry_count`. The conditional edge then routes back to the Insight node for another attempt. After two retries it proceeds regardless — partial insights are better than no insights.

I also track token usage and cost per run in the state, and write those to Postgres when the run completes. Every agent run has a `cost_usd` column. That's important for multi-tenant SaaS — you need to know your per-tenant AI cost.

**Action Agent — the HITL gate.**

It reads the insights, persists them to the `insights` table, then decides what downstream actions to create. Critical severity insights trigger a `create_jira` action. Warning and critical both trigger a `send_slack` action. These are written to the `agent_actions` table with `status: pending` — they are not executed yet.

Then if there are any critical actions, it calls LangGraph's `interrupt()`. The graph pauses. The frontend sees `status: awaiting_human` on the agent run. A manager reviews the pending actions and clicks Approve or Reject. On approval, our API resumes the graph with the same `thread_id`, the action executes — calls the Jira API, posts to Slack — and the run completes.

This bounded autonomy is intentional. The most successful agentic implementations emphasize orchestrated agents with clear guardrails, policy enforcement, and human-in-the-loop controls. The agent cannot create tickets without a human decision. That's the architecture, not just a feature.

---

## "How does multi-tenancy work?"

Every database table has `tenant_id UUID NOT NULL`. The JWT contains the tenant ID. We have a FastAPI dependency called `get_current_tenant` that validates the JWT, extracts the tenant ID, and injects it into every route handler. Every SQLAlchemy query is constructed with a `WHERE tenant_id = :tenant_id` filter.

The key is that this filter lives in the dependency, not in individual route handlers. Developers writing new endpoints call `Depends(get_current_tenant)` and then use `tenant.id` in their queries. If they forget to filter — that's a code review catch, not a runtime bypass.

Rate limiting is per-tenant, enforced in Redis with a sliding window algorithm. Each tenant gets 100 requests per minute. The key is `ratelimit:{tenant_id}:{minute_bucket}`. We use a Lua script in Redis to atomically increment and check — that's race-condition-safe.

---

## "How does the observability work?"

Three layers.

**OpenTelemetry traces.** Every FastAPI request generates a trace automatically via `FastAPIInstrumentor`. Every SQLAlchemy query is traced via `SQLAlchemyInstrumentor`. Inside the Insight Agent node, I wrap the Claude API calls in a custom span that records `tokens.in`, `tokens.out`, and `cost.usd` as span attributes. Those traces ship to an OTel Collector which forwards to Jaeger for visualization.

**Prometheus metrics.** Four key metrics: `devpulse_agent_runs_total` counts runs by tenant and status, `devpulse_insights_total` counts insights by severity and type, `devpulse_agent_cost_usd` is a histogram of per-run cost, and `devpulse_hitl_pending` is a gauge of how many actions are waiting for human approval. Grafana scrapes Prometheus every 15 seconds. I have an alert rule: if `devpulse_hitl_pending` stays above 5 for more than 30 minutes, it fires a webhook to Slack.

**Immutable audit log.** Every agent action, every human approval, every insight creation writes a row to `audit_log`. The table has Postgres rules that make UPDATE and DELETE no-ops — you literally cannot modify or delete audit log rows at the SQL level. Every row has: actor (who or what did it), action (what happened), entity type and ID, a JSON diff, and a timestamp. This is what you show to a compliance team or an angry engineering manager asking "why did this ticket get created."

---

## "What's your approach to testing agents?"

Two layers.

**Unit tests on the deterministic nodes.** The Collector and Analyst nodes have no LLM calls, so they're fully unit testable with pytest and async fixtures. I test: zero-activity developer gets the right score, after-hours commits trigger the burnout anomaly, high churn commits generate the right anomaly type, health score never goes below zero regardless of how many penalties stack. These are fast, reliable, no API calls.

**Evaluation tests on the LLM nodes using DeepEval.** The Insight node calls Claude, so I test it differently. I use DeepEval's `HallucinationMetric` to verify that the insight body doesn't mention numbers that weren't in the input — if the developer had 3 commits, the insight body should not say 15 commits. I use `AnswerRelevancyMetric` to verify the recommendation is relevant to the detected anomaly type. These run against the real Claude API in CI — they're slower and cost a small amount of tokens, but they catch prompt regressions.

The reason you need both is that `pytest` can tell you if your Python logic is correct, but it can't tell you if Claude started hallucinating after you changed your prompt. DeepEval catches that second class of failure.

---

## "How would you scale this to 10,000 tenants?"

The architecture already supports it with four changes.

**Celery workers scale horizontally.** Right now I run one worker. To handle 10,000 tenants, I'd run a worker pool behind a message queue — each worker picks up one tenant's analysis task and processes it independently. They're stateless, so adding workers is just adding containers.

**Database connection pooling.** AsyncSQLAlchemy with a connection pool per worker. At scale you'd add PgBouncer in front of Postgres to multiplex thousands of connections into a smaller pool.

**TimescaleDB for commit events.** The `commit_events` table is already using TimescaleDB. At scale I'd convert it to a hypertable partitioned by `committed_at`. TimescaleDB automatically chunks the data by time range, so queries over the last 7 days never scan historical partitions. That's the key query — `WHERE committed_at >= now() - interval '7 days'` — and it stays fast as the table grows to billions of rows.

**Cost budgets per tenant plan.** At 10,000 tenants, AI cost becomes a real concern. I'd add a budget cap per tenant based on their plan — free plan gets $0.10 per run, pro gets $1.00. The Insight Agent checks remaining budget before each LLM call and skips lower-priority developers if the budget is exhausted. That's already partially there with the `cost_usd` tracking in state.

---

## "What would you do differently if you built it again?"

Two things.

**Separate the ingest schema from the analytics schema.** Right now commit events go straight into the same Postgres database that the agents query. At scale, you'd want a write-heavy ingest database and a read-optimized analytics store — maybe a materialized view layer or a columnar store like DuckDB for the analyst computation. The Analyst node doing `SELECT *` over raw commit events doesn't scale past a few million rows.

**Prompt versioning.** The Insight Agent's prompts are currently hardcoded strings in `analyst.py`. If a prompt change causes a regression, I can't roll back without a code deploy. I'd store prompts in a database table with version numbers and A/B test them — run two prompt versions in parallel on a subset of tenants and compare DeepEval scores before promoting the new version to 100%.

---

## Handling "I don't know" moments

If they ask about something you haven't built yet — like distributed tracing across Celery tasks, or multi-region Postgres replication — say this:

> "I haven't implemented that in DevPulse yet, but here's how I'd approach it: [give the architectural direction, not a fabricated implementation]."

That's more impressive than a wrong answer and more honest than silence. The failure mode in agentic engineering interviews is not knowing the framework well enough to signal real context — so stay concrete, stay honest about depth, and always connect your answers back to decisions you actually made in the project.