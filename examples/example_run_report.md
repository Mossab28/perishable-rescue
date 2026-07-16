# Example Run — Perishable Rescue + Equity Coordinator

*Committed proof-of-run against the demo dataset. Reference only — the live judging run is a real, fresh run.*

- **Run date:** 2026-07-17
- **Engine:** LLM + rules
- **Agent modes:** `risk=llm`, `need_equity=llm`, `coordinator=llm`
- **LLM calls:** 3 · est. cost $0.0010

## 1. Risk — 8 lots at risk (3,750 lbs)

| Lot | Product | Qty (lbs) | Cond. | Hrs left | Urgency | Reasoning |
|---|---|--:|---|--:|---|---|
| L04 | Strawberries | 400 | Fair | 0 | CRITICAL | The strawberries are in 'Fair' condition and have no safe days left, so they need to be distributed immediately to avoid spoilage. |
| L11 | Baby Spinach | 500 | Fair | 0 | CRITICAL | The baby spinach is also in 'Fair' condition with no safe days left, requiring urgent distribution to prevent waste. |
| L13 | Whole Chicken | 600 | Good | 0 | CRITICAL | The whole chicken is in 'Good' condition but has no safe days left, so it must be prioritized for distribution as it is raw meat. |
| L17 | Kale Bunches | 300 | Fair | 0 | CRITICAL | The kale bunches are in 'Fair' condition and have already expired, necessitating immediate action to prevent loss. |
| L01 | Romaine Lettuce | 800 | Good | 24 | CRITICAL | The romaine lettuce is in 'Good' condition with 1 day left, so it should be distributed soon to ensure freshness. |
| L03 | Chicken Drumsticks | 500 | Good | 24 | CRITICAL | The chicken drumsticks are in 'Good' condition with 1 day remaining, requiring prompt distribution to maintain quality. |
| L07 | Ground Turkey | 350 | Good | 24 | CRITICAL | The ground turkey is in 'Good' condition with 1 day left, so it should be distributed quickly to avoid spoilage. |
| L19 | Pork Sausage | 300 | Good | 24 | CRITICAL | The pork sausage is in 'Good' condition with 1 day remaining, necessitating swift distribution to ensure it is used before it goes bad. |

## 2. Need & Equity — assignments

| Lot | → Agency | Equity rationale |
|---|---|---|
| L04 | A01 | East Oakland Community Pantry has a high need score and a drift towards bakery items, so fresh produce like strawberries will help correct their allocation. |
| L11 | A01 | Allocating baby spinach to East Oakland Community Pantry addresses their drift while meeting their critical need for fresh produce. |
| L13 | A01 | Whole chicken is a protein that fits well with East Oakland Community Pantry's needs, correcting their drift from bakery items. |
| L17 | A02 | Kale bunches are essential fresh produce that will support West Oakland Neighborhood Table's needs while diversifying their order. |
| L01 | A02 | Romaine lettuce will provide necessary fresh produce to West Oakland Neighborhood Table, balancing their order patterns. |
| L03 | A03 | Chicken drumsticks will help address the protein needs of Fruitvale Family Kitchen while correcting their drift from bakery items. |
| L07 | A01 | Ground turkey is a protein that will support East Oakland Community Pantry's high need and correct their order drift. |
| L19 | A02 | Pork sausage will meet the protein needs of West Oakland Neighborhood Table while addressing their drift from fresh produce. |

> **Demand-drift corrected:** A01, A03 (bread-heavy orders vs high neighborhood need).

## 3. Logistics — hard feasibility gate

- ✅ **L04** Strawberries → East Oakland Community Pantry via `R1`
- ✅ **L11** Baby Spinach → East Oakland Community Pantry via `R1`
- ✅ **L13** Whole Chicken → East Oakland Community Pantry via `R1`
- ✅ **L17** Kale Bunches → West Oakland Neighborhood Table via `R1`
- ✅ **L01** Romaine Lettuce → West Oakland Neighborhood Table via `R1`
- ✅ **L03** Chicken Drumsticks → Hayward Meals Collective via `R2` *(runner-up — equity-preferred agency was infeasible)*
- ✅ **L07** Ground Turkey → Hayward Meals Collective via `R2` *(runner-up — equity-preferred agency was infeasible)*
- ⛔ **L19** Pork Sausage (300 lbs) — **Meat & Poultry needs cold-chain; no refrigerated route to 94704** → flagged for manual handling

## 4. Rescue Plan

**Rescue Rate = 92%** (3,450 lbs allocated in time / 3,750 lbs at risk)

### East Oakland Community Pantry — Oakland (need 92/100) · 1500 lbs
- **Lots:** 400 lbs Strawberries, 500 lbs Baby Spinach, 600 lbs Whole Chicken
- 🇺🇸 Hello East Oakland Community Pantry! You have 400lbs of strawberries, 500lbs of baby spinach, and 600lbs of whole chicken reserved for same-day pickup. Please confirm your pickup today!
- 🇲🇽 ¡Hola East Oakland Community Pantry! Tienen reservados 400lbs de fresas, 500lbs de espinacas baby y 600lbs de pollo entero para recogida el mismo día. ¡Por favor, confirmen su recogida hoy!
- 🇨🇳 你好东奥克兰社区食品 pantry！您今天预留了400磅草莓、500磅婴儿菠菜和600磅整鸡可供当天取货。请确认您的取货！

### West Oakland Neighborhood Table — Oakland (need 85/100) · 1100 lbs
- **Lots:** 300 lbs Kale Bunches, 800 lbs Romaine Lettuce
- 🇺🇸 Hello West Oakland Neighborhood Table! You have 300lbs of kale bunches and 800lbs of romaine lettuce reserved for same-day pickup. Please confirm your pickup today!
- 🇲🇽 ¡Hola West Oakland Neighborhood Table! Tienen reservados 300lbs de racimos de col rizada y 800lbs de lechuga romana para recogida el mismo día. ¡Por favor, confirmen su recogida hoy!
- 🇨🇳 你好西奥克兰邻里餐桌！您今天预留了300磅羽衣甘蓝和800磅罗马生菜可供当天取货。请确认您的取货！

### Hayward Meals Collective — Hayward (need 72/100) · 850 lbs
- **Lots:** 500 lbs Chicken Drumsticks, 350 lbs Ground Turkey
- 🇺🇸 Hello Hayward Meals Collective! You have 500lbs of chicken drumsticks and 350lbs of ground turkey reserved for same-day pickup. Please confirm your pickup today!
- 🇲🇽 ¡Hola Hayward Meals Collective! Tienen reservados 500lbs de muslos de pollo y 350lbs de pavo molido para recogida el mismo día. ¡Por favor, confirmen su recogida hoy!
- 🇨🇳 你好海沃德餐饮集体！您今天预留了500磅鸡腿和350磅绞火鸡可供当天取货。请确认您的取货！

## 5. Learning layer (after this run)

- runs_completed: 0 → 1
- rules: 6 → 6
  - `+ [risk]` Fair-condition Fresh Produce keeps surfacing as at-risk; keep the 0.6 condition factor and prioritize same-day rescue.
  - `+ [risk]` Raw Meat & Poultry recurred in the CRITICAL tier; treat same-day as the default expectation for this category.
  - `+ [need_equity]` A01 shows recurring demand drift (bread-heavy vs high need); keep boosting its produce/protein allocation.
  - `+ [need_equity]` A03 shows recurring demand drift (bread-heavy vs high need); keep boosting its produce/protein allocation.
