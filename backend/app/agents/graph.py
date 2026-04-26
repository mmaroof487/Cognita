"""
LangGraph StateGraph — Defines the agent workflow.

Wires together Collector -> Analyst -> InsightAgent -> ActionAgent nodes
with proper state management and error handling.
"""

from typing import Any, Awaitable, Callable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import AsyncPostgresSaver

from app.agents.state import DevPulseState
from app.agents.nodes.collector import collector_node
from app.agents.nodes.analyst import analyst_node
from app.agents.nodes.insight import insight_node
from app.agents.nodes.action import action_node


def build_graph(
    session: AsyncSession,
    anthropic_client: Any,
    memory_saver: MemorySaver | AsyncPostgresSaver | None = None,
) -> StateGraph:
    """
    Build the LangGraph StateGraph.

    Args:
        session: Async database session
        anthropic_client: Anthropic API client
        memory_saver: Checkpoint memory (MemorySaver for dev, AsyncPostgresSaver for prod)

    Returns:
        Compiled StateGraph ready to invoke
    """
    graph = StateGraph(DevPulseState)

    # ─────────────────────────────────────────────────────────────────────────
    # Add Nodes
    # ─────────────────────────────────────────────────────────────────────────

    # Collector: Read DB, normalize events
    async def collector_wrapper(state: DevPulseState) -> dict:
        return await collector_node(state, session)

    graph.add_node("collector", collector_wrapper)

    # Analyst: Compute metrics, detect anomalies
    graph.add_node("analyst", analyst_node)

    # InsightAgent: Claude LLM, generate insights
    async def insight_wrapper(state: DevPulseState) -> dict:
        return await insight_node(state, anthropic_client, session)

    graph.add_node("insight", insight_wrapper)

    # ActionAgent: Create Jira tickets, format notifications, HITL gate
    async def action_wrapper(state: DevPulseState) -> dict:
        return await action_node(state, session)

    graph.add_node("action", action_wrapper)

    # ─────────────────────────────────────────────────────────────────────────
    # Add Edges
    # ─────────────────────────────────────────────────────────────────────────
    graph.add_edge(START, "collector")
    graph.add_edge("collector", "analyst")
    graph.add_edge("analyst", "insight")
    graph.add_edge("insight", "action")
    graph.add_edge("action", END)

    # ─────────────────────────────────────────────────────────────────────────
    # Compile
    # ─────────────────────────────────────────────────────────────────────────
    if memory_saver is None:
        memory_saver = MemorySaver()

    compiled_graph = graph.compile(checkpointer=memory_saver)

    return compiled_graph
