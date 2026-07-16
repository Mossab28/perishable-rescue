"""Logistics Agent — owns exactly one constraint: can a truck actually carry this move
in time? DELIBERATELY deterministic and rule-based. A vehicle's capacity and a cold-chain
requirement are facts, not judgment calls, so they do NOT get an LLM 'vibe'. This is a
hard feasibility GATE: it can veto an equity-optimal match that physics won't allow.

Route remaining-capacity is a genuine shared resource — it depletes as lots are assigned,
so two big lots can't both claim the same slack.
"""
import re
from state import PipelineState, emit

AGENT = "logistics"


def _time_range(s: str):
    times = re.findall(r"(\d{1,2}):(\d{2})", s)
    if len(times) < 2:
        return None
    (h1, m1), (h2, m2) = times[0], times[1]
    return int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)


def _windows_overlap(agency_hours: str, route_window: str) -> bool:
    a, r = _time_range(agency_hours), _time_range(route_window)
    if not a or not r:
        return True  # unknown → don't block on it
    return r[0] < a[1] and a[0] < r[1]


def _find_route(agency, lot, needs_cold, routes_state):
    """Return (route, reason) for a feasible route, or (None, reason) explaining the veto."""
    zip_matches = [r for r in routes_state if agency["zip"] in r["service_zips"]]
    if not zip_matches:
        return None, f"no route serves {agency['city']} ({agency['zip']})"
    cold_ok = [r for r in zip_matches if r["refrigerated"] or not needs_cold]
    if not cold_ok:
        return None, f"{lot['category']} needs cold-chain; no refrigerated route to {agency['zip']}"
    cap_ok = [r for r in cold_ok if r["remaining_capacity_lbs"] >= lot["quantity_lbs"]]
    if not cap_ok:
        best = max(cold_ok, key=lambda r: r["remaining_capacity_lbs"])
        return None, (f"insufficient capacity ({lot['quantity_lbs']:.0f}lbs needed, "
                      f"{best['remaining_capacity_lbs']:.0f}lbs free on {best['route_id']})")
    win_ok = [r for r in cap_ok if _windows_overlap(agency["opening_hours"], r["delivery_windows"])]
    pool = win_ok or cap_ok
    route = min(pool, key=lambda r: r["remaining_capacity_lbs"])  # tightest fit first
    reason = "feasible" if win_ok else "feasible (delivery window is tight)"
    return route, reason


def run(state: PipelineState) -> PipelineState:
    emit(state, type="agent_start", agent=AGENT, title="Logistics")

    # Work on mutable copies so allocations deplete both shared resources:
    # route capacity AND each agency's remaining daily intake capacity.
    routes_state = [dict(r) for r in state["routes"]]
    agencies = {a["agency_id"]: a for a in state["agencies"]}
    shelf = state["shelf_life"]
    assignments = state["ranking"]["assignments"]
    agency_remaining = {aid: a["daily_capacity_lbs"] for aid, a in agencies.items()}

    moves, vetoed = [], []
    for lot in state["risk"]["at_risk"]:
        lid = lot["lot_id"]
        assign = assignments.get(lid, {})
        needs_cold = shelf.get(lot["category"], {}).get("refrigerated", False)
        # Cascade: equity-preferred agency, its runner-up, then the rest of the ranked
        # list. Logistics can veto the equity-optimal pick and fall to the next feasible one.
        ordered, seen = [], set()
        for aid in ([assign.get("agency_id"), assign.get("runner_up")]
                    + [r["agency_id"] for r in assign.get("ranked", [])]):
            if aid and aid in agencies and aid not in seen:
                ordered.append(aid); seen.add(aid)
        preferred = assign.get("agency_id")
        placed = None
        veto_reason = "no candidate agency"
        for aid in ordered:
            if agency_remaining[aid] < lot["quantity_lbs"]:
                veto_reason = f"{agencies[aid]['name']} daily intake capacity reached"
                continue
            route, reason = _find_route(agencies[aid], lot, needs_cold, routes_state)
            if route:
                route["remaining_capacity_lbs"] -= lot["quantity_lbs"]
                agency_remaining[aid] -= lot["quantity_lbs"]
                placed = {"lot_id": lid, "product": lot["product"],
                          "quantity_lbs": lot["quantity_lbs"], "agency_id": aid,
                          "agency_name": agencies[aid]["name"], "route_id": route["route_id"],
                          "vehicle_id": route["vehicle_id"], "needs_cold": needs_cold,
                          "note": reason, "used_runner_up": aid != preferred}
                break
            veto_reason = reason
        if placed:
            moves.append(placed)
            emit(state, type="reasoning", agent=AGENT,
                 text=f"{lid} → {placed['agency_name']} on {placed['route_id']} ({placed['note']}).")
        else:
            vetoed.append({"lot_id": lid, "product": lot["product"],
                           "quantity_lbs": lot["quantity_lbs"], "reason": veto_reason})
            emit(state, type="reasoning", agent=AGENT,
                 text=f"VETO {lid} ({lot['product']}): {veto_reason}.")

    lbs_moved = sum(m["quantity_lbs"] for m in moves)
    emit(state, type="agent_done", agent=AGENT,
         summary=f"{len(moves)} feasible · {len(vetoed)} vetoed · {lbs_moved:,.0f} lbs")
    return {"logistics": {"moves": moves, "vetoed": vetoed, "lbs_moved": lbs_moved,
                          "routes_after": routes_state}}
