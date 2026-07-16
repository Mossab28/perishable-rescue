"""Need & Equity Agent — owns exactly one constraint: which underserved agency SHOULD
get each at-risk lot?

This is a genuine judgment call, so it reasons with a real LLM over need, capacity,
refrigeration, hours, product fit, AND how far each agency's recent order pattern has
drifted from its neighborhood's expected need. A deterministic equity score is the
fallback when the LLM is unavailable. Reads the learned-rules layer first.
"""
import config
from state import PipelineState, emit
from skills import learning
import llm

AGENT = "need_equity"
NUTRITIOUS = {"Fresh Produce", "Meat & Poultry", "Dairy", "Eggs"}


def _order_shares(agency) -> dict:
    shares = {}
    for part in agency["recent_order_pattern"].split(";"):
        if "=" in part:
            cat, pct = part.split("=")
            shares[cat.strip()] = float(pct)
    return shares


def _drift_flag(agency) -> bool:
    """Order pattern has drifted from nutritional need: high-need agency loading up on
    Bakery & Bread while under-ordering nutritious categories (learned rule E-002)."""
    shares = _order_shares(agency)
    bakery = shares.get("Bakery & Bread", 0)
    return agency["current_need_score"] >= 75 and bakery >= 45


def _score(lot, agency) -> float:
    shares = _order_shares(agency)
    need = agency["current_need_score"] / 100.0
    fit = 1.0 if lot["category"] in agency["preferred_categories"] else 0.4
    # Equity boost: agency needs this nutritious category but has been under-ordering it.
    under = lot["category"] in NUTRITIOUS and shares.get(lot["category"], 0) < 20
    drift_boost = 0.3 if (_drift_flag(agency) and lot["category"] in NUTRITIOUS) else 0.0
    equity = (0.15 if under else 0.0) + drift_boost
    # Soft refrigeration preference (Logistics enforces cold-chain as the hard gate).
    fridge_pen = -0.2 if (lot["category"] != "Bakery & Bread" and not agency["refrigeration_available"]) else 0.0
    return round(0.55 * need + 0.25 * fit + equity + fridge_pen, 3)


def _rank(lot, agencies) -> list:
    scored = [{"agency_id": a["agency_id"], "name": a["name"], "city": a["city"],
               "zip": a["zip"], "need": a["current_need_score"],
               "refrigerated": a["refrigeration_available"],
               "drift": _drift_flag(a), "score": _score(lot, a)}
              for a in agencies]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def run(state: PipelineState) -> PipelineState:
    emit(state, type="agent_start", agent=AGENT, title="Need & Equity")
    rules = state.get("learned_rules") or learning.load_rules()
    learned_text = learning.rules_as_text(rules, "need_equity")

    at_risk = state["risk"]["at_risk"]
    agencies = state["agencies"]
    drift_agencies = [a["agency_id"] for a in agencies if _drift_flag(a)]
    emit(state, type="reasoning", agent=AGENT,
         text=f"Ranking {len(agencies)} agencies for {len(at_risk)} at-risk lots. "
              f"Demand-drift flags: {', '.join(drift_agencies) or 'none'}.")

    # Deterministic ranking always computed (auditable + fallback).
    base_rank = {l["lot_id"]: _rank(l, agencies) for l in at_risk}

    mode = "fallback"
    assignments = {}
    if at_risk:
        lot_lines = "\n".join(
            f"- {l['lot_id']} {l['product']} ({l['category']}, {l['quantity_lbs']:.0f}lbs, {l['urgency']})"
            for l in at_risk)
        ag_lines = "\n".join(
            f"- {a['agency_id']} {a['name']} ({a['city']} {a['zip']}) need={a['current_need_score']:.0f} "
            f"fridge={'Y' if a['refrigeration_available'] else 'N'} cap={a['daily_capacity_lbs']:.0f}lbs "
            f"prefers={'/'.join(a['preferred_categories'])} orders=[{a['recent_order_pattern']}]"
            f"{' DRIFT' if _drift_flag(a) else ''}"
            for a in agencies)
        system = ("You are the Need & Equity agent for the Alameda County food bank. For each "
                  "at-risk lot, choose the agency that should receive it to maximize equity: "
                  "weigh unmet need, product fit, refrigeration, and especially demand DRIFT "
                  "(a high-need agency over-ordering bread while under-ordering nutrition should "
                  "be corrected, not honored verbatim). County food-insecurity baseline is 11%. "
                  "No single agency can absorb everything — respect each agency's daily capacity "
                  "and spread lots across several high-need agencies rather than piling them on one. "
                  "Return JSON {\"assignments\":[{\"lot_id\":\"\",\"agency_id\":\"\","
                  "\"runner_up\":\"\",\"equity_rationale\":\"one sentence\"}]}.")
        user = (f"Learned equity rules in force:\n{learned_text}\n\nAt-risk lots:\n{lot_lines}\n\n"
                f"Agencies:\n{ag_lines}")
        try:
            data = llm.chat_json(system, user, max_tokens=900, temperature=0.5)
            for a in data.get("assignments", []):
                if a.get("lot_id"):
                    assignments[a["lot_id"]] = a
            mode = "llm"
            emit(state, type="reasoning", agent=AGENT,
                 text="LLM equity reasoning complete; assignments proposed per lot.")
        except llm.LLMUnavailable as e:
            emit(state, type="reasoning", agent=AGENT,
                 text=f"LLM unavailable ({e}); using deterministic equity score.")

    # Merge: LLM choice if valid, else top of deterministic ranking.
    valid_ids = {a["agency_id"] for a in agencies}
    final = {}
    for l in at_risk:
        lid = l["lot_id"]
        ranked = base_rank[lid]
        chosen = assignments.get(lid, {})
        aid = chosen.get("agency_id") if chosen.get("agency_id") in valid_ids else ranked[0]["agency_id"]
        runner = chosen.get("runner_up") if chosen.get("runner_up") in valid_ids else (
            ranked[1]["agency_id"] if len(ranked) > 1 else None)
        rationale = chosen.get("equity_rationale") or _auto_rationale(l, ranked[0])
        final[lid] = {"agency_id": aid, "runner_up": runner, "rationale": rationale,
                      "ranked": ranked[:5]}

    discoveries = []
    for aid in drift_agencies:
        discoveries.append({"agent": "need_equity", "scope": f"agency:{aid}",
                            "rule": f"{aid} shows recurring demand drift (bread-heavy vs high need); "
                                    f"keep boosting its produce/protein allocation.",
                            "confidence": 0.7})

    emit(state, type="agent_done", agent=AGENT,
         summary=f"{len(final)} lots matched · {mode}")
    modes = dict(state.get("modes", {})); modes[AGENT] = mode
    return {"ranking": {"assignments": final, "drift_agencies": drift_agencies,
                        "discoveries": discoveries}, "modes": modes}


def _auto_rationale(lot, top) -> str:
    r = f"{top['name']} ranks highest (need {top['need']:.0f}/100"
    if top["drift"]:
        r += ", demand-drift correction"
    r += f") for {lot['category'].lower()}."
    return r
