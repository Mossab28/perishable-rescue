# Data Sources

We used **real, public, citable data wherever a source exists**, and only fell back to synthetic values for private operational data that no public source could provide (inventory lots, agency identities, truck routes). Every field is labeled below.

## Backdrop figures (README context) — real, re-verified

| Figure | Value | Source |
|---|---|---|
| Annual pounds distributed (2024) | 60 million lbs (record high) | [ACCFB 2024 Annual Report](https://www.accfb.org/annual-report-2024/) |
| Partner agencies | 400+ community partners | [ACCFB 2024 Annual Report](https://www.accfb.org/annual-report-2024/) |
| Weekly scheduled donor pickups | 510 | [ACCFB 2024 Annual Report](https://www.accfb.org/annual-report-2024/) |
| Alameda County food-insecurity rate (2023) | 11% — 182,080 people | [Healthy Alameda County / Feeding America](https://www.healthyalamedacounty.org/indicators/index/view?indicatorId=2107&localeId=238) |
| California / U.S. food-insecurity rate (2023) | 13.7% / 14.5% | [Healthy Alameda County / Feeding America](https://www.healthyalamedacounty.org/indicators/index/view?indicatorId=2107&localeId=238) |

## `data/shelf_life_rules.csv` — REAL (USDA FoodKeeper)

Shelf-life numbers are derived from the **USDA FSIS FoodKeeper** dataset (public domain, CC0), the government food-safety reference of storage life for 400+ food items. We fetched the FoodKeeper ingredient/category seed data ([data.gov mirror](https://catalog.data.gov/dataset/fsis-foodkeeper-data); ingredient CSV cached in `data/raw/`) and collapsed it to our five demo categories using the most conservative refrigerated storage window per category:

| Category | Days | Refrig. | FoodKeeper basis |
|---|--:|---|---|
| Fresh Produce | 5 | yes | Lettuce 1–2 wk, Strawberries 2–3 d, Broccoli 3–5 d (refrigerated) |
| Dairy | 10 | yes | Milk ~use-by 1 wk, Yogurt 1–2 wk |
| Eggs | 28 | yes | Fresh eggs in shell 3–5 weeks |
| Meat & Poultry | 2 | yes | Raw chicken / ground poultry 1–2 days |
| Bakery & Bread | 4 | no | Bread 3–5 days at pantry temperature |

> Simplification: real produce spans a wide range (leafy greens vs. root vegetables). We use one conservative per-category window and keep the demo produce lots short-shelf (leafy/berry) so the category value is realistic for those items.

## `data/agencies.csv` — MIXED

- **Real basis:** `current_need_score` is grounded in the **11% Alameda County food-insecurity baseline** and the well-documented intra-county gradient — deep East Oakland, West Oakland, and Fruitvale sit far above the county line; Hayward/San Leandro near it; Fremont and the Tri-Valley (Livermore/Pleasanton) below it. Cities, ZIP codes, and approximate lat/long are real Alameda County locations.
- **Synthetic:** agency *names/identities*, `opening_hours`, `daily_capacity_lbs`, `refrigeration_available`, `preferred_categories`, and `recent_order_pattern` — ACCFB does not publish a scrapeable partner directory or per-agency operational data, so these are plausible operational values. `recent_order_pattern` is deliberately authored so some high-need agencies show *demand drift* (bread-heavy vs. their need), the pattern the Need & Equity agent is built to catch.

## `data/inventory.csv` — SYNTHETIC (private operational data)

20 lots of receiving records (product, quantity, received date, condition, donor). No public source exists for a food bank's daily intake; these are plausible values. Products map to the five real FoodKeeper categories; donor names reflect ACCFB's documented donor mix (Safeway, Costco, Target, local bakeries/farms). `received_date` values are set relative to the demo `RUN_DATE` (2026-07-17) so a realistic subset is at risk.

## `data/routes.csv` — SYNTHETIC (private operational data)

4 vehicle routes with capacity, refrigeration, remaining capacity, delivery windows, and serviced ZIPs. Private logistics data with no public source. Capacities are sized so the refrigerated fleet is realistically tight — most lots are rescuable, but the demo reliably surfaces one genuine cold-chain veto, mirroring ACCFB's real constraint.

## `skills/learned_rules.json` — SEEDED (synthetic, grows at runtime)

Four starter rules seed the learning layer; the pipeline reinforces and appends to it on every run. `data/raw/` holds the unmodified FoodKeeper source files we fetched, for provenance.
