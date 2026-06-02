from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.agents.state import AxonState
from app.agents.nodes import collector, analyst, insight, action
from app.config import settings
from app.models import AgentRun
from app.database import async_session_factory
from sqlalchemy import select
import datetime


async def build_graph(checkpointer, interrupt_on_critical: bool = True):
    """
    Build and compile the LangGraph state machine.

    Topology: collect → analyze → insight → (conditional retry) → action → END

    With interrupt_on_critical=True, the graph pauses BEFORE the 'action' node
    so the Celery task can catch GraphInterrupt and set status='awaiting_human'.
    The 'insight' node persists Insight rows to DB so they survive the interrupt.
    The 'action' node creates AgentAction rows and calls interrupt() for HITL.
    """
    graph = StateGraph(AxonState)
    graph.add_node("collect", collector.run)
    graph.add_node("analyze", analyst.run)
    graph.add_node("insight", insight.run)
    graph.add_node("action", action.run)

    graph.set_entry_point("collect")
    graph.add_edge("collect", "analyze")
    graph.add_edge("analyze", "insight")

    # Retry insight node up to 2 times if no insights were generated
    graph.add_conditional_edges(
        "insight",
        lambda s: "action" if (s.get("retry_count", 0) >= 2 or len(s.get("insights", [])) > 0) else "insight",
        {"action": "action", "insight": "insight"},
    )
    graph.add_edge("action", END)

    kwargs: dict = {"checkpointer": checkpointer}
    if interrupt_on_critical:
        # Pause BEFORE 'action' node — celery_worker catches GraphInterrupt
        kwargs["interrupt_before"] = ["action"]

    return graph.compile(**kwargs)


async def run_graph(
    tenant_id: str,
    org_id: str,
    agent_run_id: str,
    thread_id: str,
) -> dict:
    """
    Invoke the agent graph for a single org.

    Returns the final state dict, or raises on unrecoverable failure.
    GraphInterrupt is NOT caught here — it propagates to the Celery task.
    """
    from app.models import TenantSettings

    async with async_session_factory() as db:
        stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        res = await db.execute(stmt)
        t_settings = res.scalar_one_or_none()
        window_days = t_settings.analysis_window_days if t_settings else 7

    now = datetime.datetime.now(datetime.timezone.utc)
    window_start = now - datetime.timedelta(days=window_days)

    initial_state = {
        "tenant_id": tenant_id,
        "org_id": org_id,
        "agent_run_id": agent_run_id,
        "window_start": window_start,
        "window_end": now,
        "analysis_window_days": window_days,
        "retry_count": 0,
        "errors": [],
        "insights": [],
        "actions_queued": [],
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
    }

    conn_string = settings.database_url_sync
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        graph = await build_graph(checkpointer)
        result = await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )
    return result
