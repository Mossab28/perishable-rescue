"""Orchestrator — runs the five fixed agents as a LangGraph StateGraph, then the
learning step, and always produces a report. The five roles are fixed and known in
advance (no dynamic sub-agent spawning by design). Reusable by the CLI and the server.
"""
import argparse
import json
import sys

from langgraph.graph import StateGraph, START, END

import config
import llm
from state import PipelineState, emit
from skills import learning
from agents import (intake_agent, risk_agent, need_equity_agent,
                    logistics_agent, coordinator_agent)

PIPELINE = [
    ("intake", intake_agent.run),
    ("risk", risk_agent.run),
    ("need_equity", need_equity_agent.run),
    ("logistics", logistics_agent.run),
    ("coordinator", coordinator_agent.run),
]


def build_graph():
    g = StateGraph(PipelineState)
    for name, fn in PIPELINE:
        g.add_node(name, fn)
    g.add_edge(START, "intake")
    for (a, _), (b, _) in zip(PIPELINE, PIPELINE[1:]):
        g.add_edge(a, b)
    g.add_edge("coordinator", END)
    return g.compile()


def run_pipeline(emit_cb=None, fresh: bool = False, persist_learning: bool = True) -> dict:
    rules = {"version": 1, "runs_completed": 0, "rules": []} if fresh else learning.load_rules()
    init: PipelineState = {
        "run_date": config.RUN_DATE,
        "learned_rules": rules,
        "modes": {},
        "_emit": emit_cb,
    }
    if emit_cb:
        emit_cb({"type": "run_start", "run_date": config.RUN_DATE,
                 "llm_enabled": config.LLM_ENABLED, "model": config.OPENAI_MODEL,
                 "fresh": fresh, "runs_completed_before": rules.get("runs_completed", 0)})

    graph = build_graph()
    final = graph.invoke(init)

    # --- Learning step: capture discoveries, reinforce, persist ---
    discoveries = (final.get("risk", {}).get("discoveries", []) +
                   final.get("ranking", {}).get("discoveries", []))
    before = rules.get("runs_completed", 0)
    updated = learning.learn(rules, discoveries)
    learn_info = {
        "runs_completed_before": before,
        "runs_completed_after": updated.get("runs_completed", before),
        "n_rules_before": len(rules.get("rules", [])),
        "n_rules_after": len(updated.get("rules", [])),
        "discoveries": discoveries,
        "persisted": persist_learning and not fresh,
    }
    if persist_learning and not fresh:
        learning.save_rules(updated)
    final["learning"] = learn_info
    final["llm_stats"] = llm.stats()
    if emit_cb:
        emit_cb({"type": "run_done", "learning": learn_info, "llm_stats": llm.stats()})
    return final


# ---------------- Terminal report ----------------
class C:
    R = "\033[0m"; B = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; GRN = "\033[32m"; YLW = "\033[33m"; BLU = "\033[34m"; CYN = "\033[36m"


def _c(txt, col):
    return f"{col}{txt}{C.R}" if sys.stdout.isatty() else str(txt)


TIER_COL = {"CRITICAL": C.RED, "HIGH": C.YLW, "MEDIUM": C.CYN, "LOW": C.DIM}


def print_report(final: dict):
    plan = final["plan"]
    modes = final.get("modes", {})
    print("\n" + _c("═" * 68, C.BLU))
    print(_c(f"  PERISHABLE RESCUE + EQUITY COORDINATOR — {config.RUN_DATE}", C.B))
    print(_c("═" * 68, C.BLU))
    engine = "LLM+rules" if config.LLM_ENABLED else "rule-based fallback (no API key)"
    print(f"  Engine: {_c(engine, C.CYN)}   Agent modes: " +
          " ".join(f"{k}={_c(v, C.GRN if v=='llm' else C.YLW)}" for k, v in modes.items()))

    risk = final["risk"]
    print("\n" + _c(f"▸ RISK — {len(risk['at_risk'])} lots at risk "
                    f"({risk['lbs_at_risk']:,.0f} lbs)", C.B))
    for l in risk["at_risk"]:
        print(f"  {_c(l['urgency'].ljust(8), TIER_COL.get(l['urgency'], C.R))} "
              f"{l['lot_id']} {l['product'][:24].ljust(24)} "
              f"{l['quantity_lbs']:>5.0f}lbs  {l['hours_until_unsafe']:>5.0f}h left")
        print(_c(f"      {l['explanation']}", C.DIM))

    print("\n" + _c("▸ NEED & EQUITY — assignments", C.B))
    assigns = final["ranking"]["assignments"]
    for lid, a in assigns.items():
        print(f"  {lid} → {_c(a['agency_id'], C.GRN)}  {C.DIM}{a['rationale']}{C.R}")
    if final["ranking"]["drift_agencies"]:
        print(_c(f"  demand-drift corrected: {', '.join(final['ranking']['drift_agencies'])}", C.YLW))

    print("\n" + _c("▸ LOGISTICS — hard feasibility gate", C.B))
    for m in final["logistics"]["moves"]:
        tag = " (runner-up)" if m["used_runner_up"] else ""
        print(f"  {_c('✓', C.GRN)} {m['lot_id']} {m['product'][:20].ljust(20)} → "
              f"{m['agency_name'][:26].ljust(26)} via {m['route_id']}{tag}")
    for v in final["logistics"]["vetoed"]:
        print(f"  {_c('✗', C.RED)} {v['lot_id']} {v['product'][:20].ljust(20)} — {v['reason']}")

    print("\n" + _c("▸ RESCUE PLAN", C.B))
    rate = plan["rescue_rate"]
    rc = C.GRN if rate >= 0.7 else (C.YLW if rate >= 0.4 else C.RED)
    print(f"  Rescue Rate = {_c(f'{rate:.0%}', rc)}  "
          f"({plan['lbs_moved']:,.0f} lbs allocated in time / {plan['lbs_at_risk']:,.0f} lbs at risk)")
    for r in plan["rows"]:
        print(f"  • {_c(r['agency_name'], C.B)} ({r['city']}, need {r['need_score']:.0f}) "
              f"← {r['lbs']:.0f} lbs")
        print(_c(f"      EN: {r['message']['en']}", C.DIM))

    lrn = final["learning"]
    print("\n" + _c("▸ LEARNING LAYER", C.B))
    print(f"  runs_completed {lrn['runs_completed_before']} → "
          f"{_c(lrn['runs_completed_after'], C.GRN)}   "
          f"rules {lrn['n_rules_before']} → {_c(lrn['n_rules_after'], C.GRN)}   "
          f"{'(persisted)' if lrn['persisted'] else '(not persisted)'}")
    for d in lrn["discoveries"]:
        print(_c(f"      + [{d['agent']}] {d['rule']}", C.DIM))

    st = final["llm_stats"]
    print(f"\n  {C.DIM}LLM calls: {st['calls']}  est. cost: ${st['cost_usd']:.4f}{C.R}")
    print(_c("═" * 68, C.BLU) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Perishable Rescue + Equity Coordinator")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore learned rules this run (baseline / 'run #1' behavior)")
    ap.add_argument("--no-learn", action="store_true",
                    help="do not persist learning (keeps committed seed unchanged)")
    ap.add_argument("--json", action="store_true", help="dump final state as JSON")
    args = ap.parse_args()

    final = run_pipeline(fresh=args.fresh, persist_learning=not args.no_learn)
    if args.json:
        safe = {k: v for k, v in final.items() if k != "_emit"}
        print(json.dumps(safe, indent=2, default=str))
    else:
        print_report(final)


if __name__ == "__main__":
    main()
