"""Coordinator Agent — owns exactly one job: fuse the four upstream outputs into ONE
rescue plan (which lots -> which agencies -> which routes) and draft a short, plain-language,
multilingual notification for each receiving agency. Real LLM synthesis, with a templated
multilingual fallback so a notification always goes out even if the model is down.
"""
from collections import defaultdict
import config
from state import PipelineState, emit
import llm

AGENT = "coordinator"


def _group_by_agency(moves) -> dict:
    by = defaultdict(list)
    for m in moves:
        by[m["agency_id"]].append(m)
    return by


def _fallback_message(agency_name, items) -> dict:
    lines = ", ".join(f"{i['quantity_lbs']:.0f} lbs {i['product']}" for i in items)
    total = sum(i["quantity_lbs"] for i in items)
    return {
        "en": (f"Hello {agency_name} — Alameda County Community Food Bank has {total:.0f} lbs of "
               f"time-sensitive food reserved for you today ({lines}). Please confirm same-day "
               f"pickup/delivery so it reaches your neighbors while fresh."),
        "es": (f"Hola {agency_name}: el Banco de Alimentos del Condado de Alameda tiene {total:.0f} "
               f"libras de alimentos perecederos reservados para usted hoy ({lines}). Confirme la "
               f"entrega el mismo día para distribuirlos frescos."),
        "zh": (f"您好 {agency_name}：阿拉米达县社区食物银行今天为您预留了约 {total:.0f} 磅易腐食物"
               f"（{lines}）。请确认当天取货/送货，以便新鲜发放给社区居民。"),
    }


def run(state: PipelineState) -> PipelineState:
    emit(state, type="agent_start", agent=AGENT, title="Coordinator")

    moves = state["logistics"]["moves"]
    by_agency = _group_by_agency(moves)
    agencies = {a["agency_id"]: a for a in state["agencies"]}
    lbs_at_risk = state["risk"]["lbs_at_risk"]
    lbs_moved = state["logistics"]["lbs_moved"]
    rescue_rate = (lbs_moved / lbs_at_risk) if lbs_at_risk else 0.0

    emit(state, type="reasoning", agent=AGENT,
         text=f"Assembling plan: {len(moves)} moves to {len(by_agency)} agencies. "
              f"Rescue rate {rescue_rate:.0%} ({lbs_moved:,.0f}/{lbs_at_risk:,.0f} lbs).")

    mode = "fallback"
    messages = {}
    if by_agency:
        blocks = []
        for aid, items in by_agency.items():
            it = ", ".join(f"{i['quantity_lbs']:.0f}lbs {i['product']}" for i in items)
            blocks.append(f"{aid} {agencies[aid]['name']} ({agencies[aid]['city']}): {it}")
        system = ("You are the Coordinator for the Alameda County food bank. For each agency, "
                  "write a SHORT (2 sentences max) warm notification that it has time-sensitive "
                  "rescued food reserved today and to confirm same-day pickup. Provide English, "
                  "Spanish, and Chinese (the main languages ACCFB serves). Return JSON "
                  "{\"messages\":{\"AGENCY_ID\":{\"en\":\"\",\"es\":\"\",\"zh\":\"\"}}}.")
        user = "Agencies and their reserved lots:\n" + "\n".join(blocks)
        try:
            data = llm.chat_json(system, user, max_tokens=1100, temperature=0.6)
            messages = data.get("messages", {}) or {}
            mode = "llm"
        except llm.LLMUnavailable as e:
            emit(state, type="reasoning", agent=AGENT,
                 text=f"LLM unavailable ({e}); using templated multilingual messages.")

    plan_rows = []
    for aid, items in by_agency.items():
        msg = messages.get(aid) or _fallback_message(agencies[aid]["name"], items)
        # guarantee all three languages exist even if the model returned a partial object
        fb = _fallback_message(agencies[aid]["name"], items)
        for k in ("en", "es", "zh"):
            msg.setdefault(k, fb[k])
        plan_rows.append({
            "agency_id": aid, "agency_name": agencies[aid]["name"],
            "city": agencies[aid]["city"], "need_score": agencies[aid]["current_need_score"],
            "lots": items, "lbs": sum(i["quantity_lbs"] for i in items),
            "rationale": state["ranking"]["assignments"].get(items[0]["lot_id"], {}).get("rationale", ""),
            "message": msg,
        })
    plan_rows.sort(key=lambda r: r["need_score"], reverse=True)

    emit(state, type="agent_done", agent=AGENT,
         summary=f"Plan ready · rescue rate {rescue_rate:.0%} · {mode}")
    modes = dict(state.get("modes", {})); modes[AGENT] = mode
    plan = {"rows": plan_rows, "rescue_rate": rescue_rate, "lbs_at_risk": lbs_at_risk,
            "lbs_moved": lbs_moved, "vetoed": state["logistics"]["vetoed"],
            "n_moves": len(moves), "n_agencies": len(by_agency)}
    emit(state, type="final_report", plan=plan, modes=modes)
    return {"plan": plan, "modes": modes}
