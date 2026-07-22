# Live Demo Script — Perishable Rescue

*Play-by-play for running the demo at **https://rescue.intrudr.io** on Slide 6. ~90 seconds.*
*Open the tab BEFORE you present. Have it on the pipeline view, not mid-run.*

---

## Before you press Run
> "This is running live on a real server. On the left, the five agents and the learning loop; underneath, a one-line summary of what each does. On the right, the agents will narrate their reasoning as they go. Everything below the pipeline — inventory, agencies, routes — comes from committed data grounded in real sources: **USDA FoodKeeper** for shelf life, **Feeding America / Map the Meal Gap** for the Alameda need scores. Let me run it."

**→ Click "Run pipeline".**

## Intake lights up
> "**Intake** — no AI, just parsing. It turns each raw receiving line into a clean, traced lot: an ID, the donor, the date, the condition, the category. Note that word — **traced**. Every unit is a lot with an identity, not a bulk pile. Twenty lots, 8,630 pounds."

## Risk lights up (the traceability moment)
> "**Risk** does the math — deterministic, from real USDA FoodKeeper shelf life. For each lot it computes exact **hours-until-unsafe**: strawberries in Fair condition, already two days old, have about 18 hours; raw chicken flips to at-risk within a day. This is your answer to *'where is the bad product?'* — the system pinpoints the **exact lot, its remaining safe window, and where it's headed**, before it spoils. Eight lots at risk, 3,750 pounds. And it read two learned rules before scoring — that's the learning layer."

## Need & Equity lights up
> "**Need & Equity** — this is the real judgment. It ranks agencies by unmet need and catches **demand drift**: East Oakland, high need but bread-heavy orders, gets bumped up for produce and protein specifically because it's under-served. Watch the packets read from the learned-rules store."

## Logistics lights up
> "**Logistics** — the hard gate. Cold-chain, truck capacity, delivery windows — deterministic, no vibes. Watch here — it **vetoes** the raw pork lot: it needs a refrigerated route, none is available for that ZIP, so it's pulled from the automated plan and flagged for manual handling. Physics wins."

## Coordinator + report appears
> "**Coordinator** assembles the plan and writes each agency's pickup notice in **English, Spanish and Chinese**. And here's the outcome: **92% rescue rate**. Then the row that matters —" *(scroll to the contrast table)* "— the **status quo**, computed on the same data: 71%, spoils 1,100 pounds on warm trucks, and delivers **zero pounds** to the highest-need agencies. Ours steers **2,600 pounds** to them. Same day, same data — that's the difference the agents make."

## Optional closers
> "Total cost of that run: about a tenth of a cent." *(point to the LLM-calls chip)*
> "And if the API were down, it produces the exact same plan on the rule-based fallback — it degrades, it never crashes."
> *(Optional second run)* "Run it again and the learning counter ticks up — run #1 is good, run #100 is sharper."

---

## Recovery lines (if something is slow / offline)
- **Slow network / API hiccup:** "It's making real LLM calls over the network — give it a second… and there's the plan." (If it truly stalls, the fallback still produces a plan.)
- **Venue wifi dead:** show the committed `examples/example_run_report.md` in the repo, or the recorded screenshots — "here's a saved run; the live one behaves identically."
- **Projector too small to read the stream:** narrate from the nodes lighting up + the final 92% and the contrast table, which are large.

## The one-liner if you only get 15 seconds
> "Press run — five agents flag every at-risk **lot** by ID and hours-left, route it to the highest-need agency a truck can actually reach, refuse the unsafe move, and draft the notice in three languages. 92% vs 71% for the manual desk, live, for a tenth of a cent."
