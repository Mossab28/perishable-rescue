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
    final["baseline"] = naive_baseline(final)
    if emit_cb:
        emit_cb({"type": "run_done", "learning": learn_info, "llm_stats": llm.stats(),
                 "baseline": final["baseline"]})
    return final


def naive_baseline(final: dict) -> dict:
    """Status-quo comparison: what a manual desk does WITHOUT the smart agents —
    honor standing orders (send each lot to whoever already orders that category most),
    first-come-first-served, with NO equity/drift correction and NO cold-chain gate
    (naive dispatch just loads the nearest truck). Cold lots on a non-refrigerated route
    SPOIL in transit. This is the honest baseline the multi-agent plan is measured against.
    """
    at_risk = final["risk"]["at_risk"]
    agencies = final["agencies"]
    shelf = final["shelf_life"]
    routes = [dict(r) for r in final["routes"]]
    lbs_at_risk = final["risk"]["lbs_at_risk"] or 1.0
    agency_rem = {a["agency_id"]: a["daily_capacity_lbs"] for a in agencies}

    def share(a, cat):
        for part in a["recent_order_pattern"].split(";"):
            if "=" in part:
                c, p = part.split("=")
                if c.strip() == cat:
                    return float(p)
        return 0.0

    rescued = spoiled = unplaced = high_need = 0.0
    for lot in at_risk:
        cat, qty = lot["category"], lot["quantity_lbs"]
        needs_cold = shelf.get(cat, {}).get("refrigerated", False)
        placed = False
        for a in sorted(agencies, key=lambda ag: share(ag, cat), reverse=True):
            aid = a["agency_id"]
            if agency_rem[aid] < qty:
                continue
            zr = [r for r in routes if a["zip"] in r["service_zips"]
                  and r["remaining_capacity_lbs"] >= qty]
            if not zr:
                continue
            r = zr[0]  # naive: nearest/first truck, no cold-chain check
            r["remaining_capacity_lbs"] -= qty
            agency_rem[aid] -= qty
            if needs_cold and not r["refrigerated"]:
                spoiled += qty  # loaded on a warm truck → spoils, not rescued
            else:
                rescued += qty
                if a["current_need_score"] >= 75:
                    high_need += qty
            placed = True
            break
        if not placed:
            unplaced += qty

    plan = final["plan"]
    pipe_high_need = sum(r["lbs"] for r in plan["rows"] if r["need_score"] >= 75)
    return {
        "lbs_at_risk": final["risk"]["lbs_at_risk"],
        "naive_rescue_rate": rescued / lbs_at_risk,
        "naive_rescued_lbs": rescued,
        "naive_spoiled_lbs": spoiled,
        "naive_unplaced_lbs": unplaced,
        "naive_high_need_lbs": high_need,
        "pipe_rescue_rate": plan["rescue_rate"],
        "pipe_rescued_lbs": plan["lbs_moved"],
        "pipe_high_need_lbs": pipe_high_need,
        "pipe_spoiled_lbs": 0.0,
        "drift_corrected": len(final["ranking"]["drift_agencies"]),
    }


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

    b = final.get("baseline")
    if b:
        nr = f"{b['naive_rescue_rate']:.0%}"; pr = f"{b['pipe_rescue_rate']:.0%}"
        ns = f"{b['naive_spoiled_lbs']:,.0f} lbs"
        nh = f"{b['naive_high_need_lbs']:,.0f} lbs"; ph = f"{b['pipe_high_need_lbs']:,.0f} lbs"
        print("\n" + _c("▸ VS STATUS QUO (honor standing orders · nearest truck · no smart gating)", C.B))
        print(f"  Rescue rate:            status quo {_c(nr, C.YLW)}  →  multi-agent {_c(pr, C.GRN)}")
        print(f"  Spoiled on warm trucks: status quo {_c(ns, C.RED)}  →  multi-agent {_c('0 lbs (flagged)', C.GRN)}")
        print(f"  To high-need agencies:  status quo {_c(nh, C.YLW)}  →  multi-agent {_c(ph, C.GRN)}")

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
