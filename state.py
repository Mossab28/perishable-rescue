"""Shared pipeline state + event emission (used for live streaming to the frontend)."""
from typing import TypedDict, Any, Callable, Optional


class PipelineState(TypedDict, total=False):
    run_date: str
    lots: list              # Intake output: structured lot records
    shelf_life: dict        # category -> {days, refrigerated}
    agencies: list
    routes: list
    learned_rules: dict
    risk: dict              # Risk output: at_risk lots + reasoning
    ranking: dict           # Need & Equity output: ranked agencies + reasoning
    logistics: dict         # Logistics output: feasibility per candidate move
    plan: dict              # Coordinator output: final rescue plan + messages
    modes: dict             # per-agent: "llm" or "fallback"
    _emit: Optional[Callable[[dict], None]]


def emit(state: PipelineState, **event: Any) -> None:
    """Push an event to the live stream if a sink is attached; always harmless offline."""
    cb = state.get("_emit")
    if cb:
        try:
            cb(event)
        except Exception:
            pass
