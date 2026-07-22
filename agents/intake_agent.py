"""Intake Agent — deterministic. Parses raw receiving records (CSV) into structured
lot records the rest of the pipeline consumes. One job: turn messy input into clean data.
No LLM here on purpose: parsing is not a judgment call.
"""
import csv
import io
import config
from state import PipelineState, emit

AGENT = "intake"

REQUIRED_INVENTORY_COLS = {"lot_id", "product", "category", "quantity_lbs",
                           "received_date", "condition", "donor"}


def _read_csv(name: str, override_text: str = None) -> list:
    if override_text is not None:
        return list(csv.DictReader(io.StringIO(override_text)))
    path = config.DATA_DIR / name
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run(state: PipelineState) -> PipelineState:
    emit(state, type="agent_start", agent=AGENT, title="Intake")

    # Optional: an inventory CSV uploaded live in the browser overrides the committed file.
    inv_text = state.get("inventory_csv")
    if inv_text is not None:
        header = (inv_text.splitlines() or [""])[0]
        cols = {c.strip() for c in header.split(",")}
        missing = REQUIRED_INVENTORY_COLS - cols
        if missing:
            raise ValueError(
                "Uploaded CSV is missing required columns: " + ", ".join(sorted(missing))
                + ". Expected header: " + ",".join(sorted(REQUIRED_INVENTORY_COLS)))
    raw = _read_csv("inventory.csv", inv_text)
    lots = []
    for r in raw:
        lots.append({
            "lot_id": r["lot_id"],
            "product": r["product"],
            "category": r["category"],
            "quantity_lbs": float(r["quantity_lbs"]),
            "received_date": r["received_date"],
            "condition": r["condition"],
            "donor": r["donor"],
        })

    shelf = {}
    for r in _read_csv("shelf_life_rules.csv"):
        shelf[r["product_category"]] = {
            "days": float(r["typical_shelf_life_days"]),
            "refrigerated": r["requires_refrigeration"].strip().lower() == "yes",
        }

    agencies = []
    for r in _read_csv("agencies.csv"):
        r["daily_capacity_lbs"] = float(r["daily_capacity_lbs"])
        r["current_need_score"] = float(r["current_need_score"])
        r["refrigeration_available"] = r["refrigeration_available"].strip().lower() == "yes"
        r["preferred_categories"] = [c.strip() for c in r["preferred_categories"].split(";")]
        agencies.append(r)

    routes = []
    for r in _read_csv("routes.csv"):
        r["vehicle_capacity_lbs"] = float(r["vehicle_capacity_lbs"])
        r["remaining_capacity_lbs"] = float(r["remaining_capacity_lbs"])
        r["refrigerated"] = r["refrigerated"].strip().lower() == "yes"
        r["service_zips"] = [z.strip() for z in r["service_zips"].split(";")]
        routes.append(r)

    total = sum(l["quantity_lbs"] for l in lots)
    emit(state, type="reasoning", agent=AGENT,
         text=f"Parsed {len(lots)} lots ({total:,.0f} lbs) across {len(shelf)} categories, "
              f"{len(agencies)} agencies, {len(routes)} routes.")
    emit(state, type="agent_done", agent=AGENT,
         summary=f"{len(lots)} lots · {total:,.0f} lbs")

    return {"lots": lots, "shelf_life": shelf, "agencies": agencies, "routes": routes}
