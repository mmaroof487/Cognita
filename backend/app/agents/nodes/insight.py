"""
Insight Agent Node — Generate human-readable insights using Claude.

Uses Anthropic API to turn metrics and anomalies into narrative insights
and recommended actions. Accumulates insights into state for ActionAgent.
"""

import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from anthropic import Anthropic

from app.agents.state import DevPulseState


async def insight_node(
    state: DevPulseState,
    anthropic_client: Anthropic,
    session: AsyncSession,
) -> dict:
    """
    Insight agent node: Generate insights using Claude.

    Args:
        state: DevPulseState with anomalies, metrics populated
        anthropic_client: Anthropic Anthropic client
        session: Async database session

    Returns:
        Dict with insights to update state
    """
    anomalies = state.get("anomalies", [])
    developer_metrics = state.get("developer_metrics", {})
    team_metrics = state.get("team_metrics", {})

    if not anomalies:
        print("[InsightAgent] No anomalies detected, skipping insight generation")
        return {"insights": []}

    # ─────────────────────────────────────────────────────────────────────────
    # Prepare context for Claude
    # ─────────────────────────────────────────────────────────────────────────
    anomaly_summary = json.dumps(anomalies, indent=2)
    metrics_summary = json.dumps({
        "team": team_metrics,
        "developers": developer_metrics,
    }, indent=2, default=str)

    prompt = f"""You are an AI DevOps and developer productivity analyst.
Given the following anomalies and metrics from a GitHub organization analysis,
generate 2-3 actionable insights that could improve team productivity and code quality.

For each insight, provide:
- A clear title
- A brief explanation
- A recommended action

FORMAT YOUR RESPONSE AS JSON with this structure:
{{
  "insights": [
    {{
      "title": "...",
      "explanation": "...",
      "recommended_action": "...",
      "severity": "high|medium|low"
    }}
  ]
}}

ANOMALIES:
{anomaly_summary}

TEAM METRICS:
{metrics_summary}

Generate 2-3 insights based on the patterns above."""

    # ─────────────────────────────────────────────────────────────────────────
    # Call Claude
    # ─────────────────────────────────────────────────────────────────────────
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        response_text = response.content[0].text

        # Parse JSON from response
        # Claude might include markdown code blocks, so strip them
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        insights_data = json.loads(response_text)
        insights = insights_data.get("insights", [])

        print(f"[InsightAgent] Generated {len(insights)} insights from {len(anomalies)} anomalies")

        # Add insight records to DB (will be done by ActionAgent or separate service)
        return {"insights": insights}

    except Exception as e:
        print(f"[InsightAgent] Error calling Claude: {e}")
        return {
            "insights": [
                {
                    "title": "Error generating insights",
                    "explanation": str(e),
                    "recommended_action": "Check InsightAgent logs",
                    "severity": "high",
                }
            ]
        }
