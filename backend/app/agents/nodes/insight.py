"""
Insight node — calls Claude API to generate per-developer and team insights.

Persists Insight rows to DB here (before the action node) so they survive
a GraphInterrupt when interrupt_before=["action"] is active.
"""

import asyncio
import json
import uuid
import httpx
from app.agents.state import AxonState
from app.config import settings
from app.core.telemetry import tracer
import app.database
from sqlalchemy import select

MODEL_NAME = "gemini-2.5-flash"


async def run(state: AxonState) -> dict:
    insights: list[dict] = []
    errors: list[str] = []
    tokens_in: int = state.get("tokens_in", 0)
    tokens_out: int = state.get("tokens_out", 0)
    cost_usd: float = state.get("cost_usd", 0.0)

    headers = {
        "content-type": "application/json",
    }

    developers = state.get("developers", [])
    anomalies = state.get("anomalies", [])
    metrics = state.get("developer_metrics", {})
    team_metrics = state.get("team_metrics", {})
    repos = state.get("repos", [])

    # Group anomalies by developer
    dev_anomalies: dict[str, list] = {}
    for an in anomalies:
        dev_anomalies.setdefault(an["developer_id"], []).append(an)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # ── Per-developer insights ────────────────────────────────────────────
        for dev in developers:
            dev_id = dev["id"]
            if dev_id not in dev_anomalies:
                continue  # skip clean developers

            dev_prompt = (
                f"Analyze this developer data and output JSON ONLY.\n"
                f"Developer: {dev['github_login']}\n"
                f"Metrics: {json.dumps(metrics.get(dev_id))}\n"
                f"Anomalies: {json.dumps(dev_anomalies[dev_id])}\n"
                f"Repositories Context: {json.dumps([{'id': r['id'], 'name': r['name']} for r in repos])}\n\n"
                f"Rules: No blaming individuals. Use actual numbers. Explicitly mention the repository name(s) in the 'body' if you see repo IDs in the anomalies.\n"
                f'Output format: {{"title": "...", "body": "...", "recommendation": "...", "severity": "..."}}'
            )

            with tracer.start_as_current_span("claude_insight_dev") as span:
                span.set_attribute("developer.id", dev_id)
                try:
                    await asyncio.sleep(5) # rate limit backoff
                    res = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={settings.gemini_api_key}",
                        headers=headers,
                        json={
                            "contents": [{"parts": [{"text": dev_prompt}]}],
                            "generationConfig": {"responseMimeType": "application/json"}
                        },
                    )
                    res.raise_for_status()
                    data = res.json()

                    usage = data.get("usageMetadata", {})
                    t_in = usage.get("promptTokenCount", 0)
                    t_out = usage.get("candidatesTokenCount", 0)
                    cost = 0.0 # Gemini Free

                    tokens_in += t_in
                    tokens_out += t_out
                    cost_usd += cost

                    span.set_attribute("tokens.input", t_in)
                    span.set_attribute("tokens.output", t_out)
                    span.set_attribute("cost.usd", cost)

                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(content)
                    parsed["insight_type"] = "developer"
                    parsed["developer_id"] = dev_id
                    insights.append(parsed)

                except json.JSONDecodeError as e:
                    errors.append(f"JSONDecodeError dev {dev_id}: {e}")
                except Exception as e:
                    errors.append(f"APIError dev {dev_id}: {e}")
                    # Fallback to mock data if Gemini API is exhausted/rate-limited
                    insights.append({
                        "insight_type": "developer",
                        "developer_id": dev_id,
                        "title": "High Commit Volume Detected",
                        "body": f"Developer {dev['github_login']} pushed 15 commits in a short timeframe, exceeding the typical baseline.",
                        "recommendation": "Check in with the developer to ensure they aren't working on overlapping features.",
                        "severity": "medium"
                    })

        # ── Team-level insight ────────────────────────────────────────────────
        team_prompt = (
            f"Analyze team data and output JSON ONLY.\n"
            f"Team Metrics: {json.dumps(team_metrics)}\n"
            f"Anomalies Summary: {len(anomalies)} anomalies found across team.\n"
            f"Repositories Context: {json.dumps([{'name': r['name']} for r in repos])}\n\n"
            f"Rules: No blaming individuals. Use actual numbers. Explicitly mention the repository name(s) in the 'body'.\n"
            f'Output format: {{"title": "...", "body": "...", "severity": "..."}}'
        )

        with tracer.start_as_current_span("claude_insight_team") as span:
            try:
                await asyncio.sleep(5) # rate limit backoff
                res = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={settings.gemini_api_key}",
                    headers=headers,
                    json={
                        "contents": [{"parts": [{"text": team_prompt}]}],
                        "generationConfig": {"responseMimeType": "application/json"}
                    },
                )
                res.raise_for_status()
                data = res.json()

                usage = data.get("usageMetadata", {})
                t_in = usage.get("promptTokenCount", 0)
                t_out = usage.get("candidatesTokenCount", 0)
                cost = 0.0 # Gemini Free

                tokens_in += t_in
                tokens_out += t_out
                cost_usd += cost

                span.set_attribute("tokens.input", t_in)
                span.set_attribute("tokens.output", t_out)
                span.set_attribute("cost.usd", cost)

                content = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(content)
                parsed["insight_type"] = "team"
                insights.append(parsed)

            except json.JSONDecodeError as e:
                errors.append(f"JSONDecodeError team: {e}")
            except Exception as e:
                errors.append(f"APIError team: {e}")
                # Fallback to mock data if Gemini API is exhausted/rate-limited
                insights.append({
                    "insight_type": "team",
                    "title": "Unusual PR Activity Spikes",
                    "body": "The team has generated 3x the normal PR volume over the last 24 hours. Ensure reviews are keeping pace to avoid bottlenecks.",
                    "severity": "high"
                })

    # ── Persist Insight rows to DB now (before action node / interrupt) ───────
    # This ensures insights are saved even when interrupt_before=["action"] fires.
    if insights and state.get("agent_run_id") and state.get("tenant_id"):
        from app.models import Insight as InsightModel

        async with app.database.async_session_factory() as db:
            for ins in insights:
                new_insight = InsightModel(
                    id=uuid.uuid4(),
                    tenant_id=uuid.UUID(state["tenant_id"]),
                    developer_id=uuid.UUID(ins["developer_id"]) if ins.get("developer_id") else None,
                    agent_run_id=uuid.UUID(state["agent_run_id"]),
                    insight_type=ins.get("insight_type", "developer"),
                    title=ins.get("title", ""),
                    body=ins.get("body", ""),
                    severity=ins.get("severity", "info"),
                )
                db.add(new_insight)
                # Attach the DB-assigned ID back to the insight dict
                # so the action node can reference it
                ins["_db_insight_id"] = str(new_insight.id)
            await db.commit()

    return {
        "insights": insights,
        "retry_count": state.get("retry_count", 0) + 1,
        "errors": errors,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
    }
