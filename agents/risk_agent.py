"""Risk Agent — owns exactly one constraint: will this lot go unsafe before the
network can move it?

Core math is DETERMINISTIC and auditable (shelf life x condition vs age, and quantity
vs network movement velocity). A real LLM call then interprets edge cases and explains
each flag in plain language. If the LLM is unavailable, a rule-based template explains
instead — the flags themselves never depend on the model.

Reads the learned-rules layer before reasoning.
"""
from datetime import date
import config
from state import PipelineState, emit
from skills import learning
import llm

AGENT = "risk"


def _parse_date(s: str) -> date:
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def _network_velocity(agencies: list) -> dict:
    """lbs/day the whole partner network is currently pulling per category,
    derived from each agency's capacity x its recent order mix."""
    vel: dict = {}
    for a in agencies:
        cap = a["daily_capacity_lbs"]
        for part in a["recent_order_pattern"].split(";"):
            if "=" not in part:
                continue
            cat, pct = part.split("=")
            vel[cat.strip()] = vel.get(cat.strip(), 0.0) + cap * float(pct) / 100.0
    return vel


def _compute(lots, shelf, agencies, run_date):
    velocity = _network_velocity(agencies)
    today = _parse_date(run_date)
    flagged, safe = [], []
    for l in lots:
        base = shelf.get(l["category"], {}).get("days", 5)
        factor = config.CONDITION_FACTOR.get(l["condition"], 1.0)
        eff = base * factor
        age = (today - _parse_date(l["received_date"])).days
        days_left = round(eff - age, 2)
        hours = max(0.0, days_left * 24)
        vel = velocity.get(l["category"], 0.0)
        days_to_move = l["quantity_lbs"] / vel if vel > 0 else float("inf")
        at_risk = days_left <= config.AT_RISK_DAYS_BUFFER or days_to_move > days_left
        rec = {
            **l,
            "effective_shelf_days": round(eff, 2),
            "age_days": age,
            "days_left": days_left,
            "hours_until_unsafe": round(hours, 1),
            "network_velocity_lbs_day": round(vel, 1),
            "days_to_clear": round(days_to_move, 2) if days_to_move != float("inf") else None,
            "urgency": config.urgency_tier(hours),
            "at_risk": at_risk,
        }
        (flagged if at_risk else safe).append(rec)
    flagged.sort(key=lambda r: r["hours_until_unsafe"])
    return flagged, safe, velocity


def _fallback_explanation(lot) -> str:
    bits = [f"{lot['product']} ({lot['quantity_lbs']:.0f} lbs) has ~{lot['hours_until_unsafe']:.0f}h "
            f"of safe window left ({lot['urgency']})."]
    if lot["condition"] == "Fair":
        bits.append("'Fair' condition cut its effective shelf life (learned rule R-001).")
    if lot["category"] == "Meat & Poultry":
        bits.append("Raw protein carries a sub-48h window (learned rule R-002).")
    if lot["days_to_clear"] and lot["days_to_clear"] > lot["days_left"]:
        bits.append(f"Current network velocity would take ~{lot['days_to_clear']:.1f}d to clear it — "
                    f"longer than the {lot['days_left']:.1f}d it stays safe.")
    return " ".join(bits)


def run(state: PipelineState) -> PipelineState:
    emit(state, type="agent_start", agent=AGENT, title="Risk")
    rules = state.get("learned_rules") or learning.load_rules()
    learned_text = learning.rules_as_text(rules, "risk")
    emit(state, type="reasoning", agent=AGENT,
         text=f"Applying {len(learning.rules_for(rules,'risk'))} learned risk rule(s) before scoring.")

    flagged, safe, velocity = _compute(
        state["lots"], state["shelf_life"], state["agencies"], state["run_date"])

    lbs_at_risk = sum(l["quantity_lbs"] for l in flagged)
    emit(state, type="reasoning", agent=AGENT,
         text=f"{len(flagged)} lots at risk ({lbs_at_risk:,.0f} lbs). "
              f"Most urgent: {flagged[0]['product'] if flagged else 'none'}.")

    # LLM edge-case interpretation (one batched call to save cost), with fallback.
    mode = "fallback"
    explanations = {}
    if flagged:
        lot_lines = "\n".join(
            f"- {l['lot_id']} {l['product']} | cat={l['category']} | cond={l['condition']} | "
            f"qty={l['quantity_lbs']:.0f}lbs | days_left={l['days_left']} | "
            f"{l['hours_until_unsafe']:.0f}h | clears_in={l['days_to_clear']}d | {l['urgency']}"
            for l in flagged)
        system = ("You are the Risk agent in a food-bank rescue pipeline. The numeric risk "
                  "flags are already decided and correct — do NOT change them. Explain each "
                  "flagged lot in ONE plain-language sentence a warehouse coordinator can act "
                  "on, noting any edge case (poor condition, sub-48h protein, slow-moving "
                  "category). Return JSON: {\"explanations\": {\"LOT_ID\": \"...\"}}.")
        user = f"Learned rules in force:\n{learned_text}\n\nFlagged lots:\n{lot_lines}"
        try:
            data = llm.chat_json(system, user, max_tokens=600, temperature=0.4)
            explanations = data.get("explanations", {}) or {}
            mode = "llm"
        except llm.LLMUnavailable as e:
            emit(state, type="reasoning", agent=AGENT,
                 text=f"LLM unavailable ({e}); using rule-based explanations.")

    for l in flagged:
        l["explanation"] = explanations.get(l["lot_id"]) or _fallback_explanation(l)

    # Discoveries feed the learning layer after the run.
    discoveries = []
    if any(l["condition"] == "Fair" and l["category"] == "Fresh Produce" for l in flagged):
        discoveries.append({"agent": "risk", "scope": "category:Fresh Produce",
                            "rule": "Fair-condition Fresh Produce keeps surfacing as at-risk; "
                                    "keep the 0.6 condition factor and prioritize same-day rescue.",
                            "confidence": 0.7})
    if any(l["category"] == "Meat & Poultry" for l in flagged):
        discoveries.append({"agent": "risk", "scope": "category:Meat & Poultry",
                            "rule": "Raw Meat & Poultry recurred in the CRITICAL tier; treat "
                                    "same-day as the default expectation for this category.",
                            "confidence": 0.75})

    emit(state, type="agent_done", agent=AGENT,
         summary=f"{len(flagged)} at risk · {lbs_at_risk:,.0f} lbs · {mode}")

    modes = dict(state.get("modes", {})); modes[AGENT] = mode
    return {"risk": {"at_risk": flagged, "safe": safe, "lbs_at_risk": lbs_at_risk,
                     "velocity": velocity, "discoveries": discoveries},
            "modes": modes}
