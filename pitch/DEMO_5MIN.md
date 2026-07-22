# 5-min Demo — Perishable Rescue (no deck)

*Format: no slides. You talk + you drive the live app at **https://rescue.intrudr.io**.*
*Open the tab BEFORE you start, on the pipeline view (not mid-run). Repo tab ready as second: github.com/Mossab28/perishable-rescue.*
*Timing: ~1 min framing → ~2 min live demo → ~1 min proof → ~30 s close. Then Q&A.*

---

## 0:00 — 0:20 · Hook
> "A food bank's problem isn't a lack of food — it's a lack of **time**. The U.S. had 70 million tons of surplus in 2024, and **80% of the waste is perishable**: meat, produce, dairy. Berries last a few **hours**, raw chicken 1 to 2 days. And the fresh food that spoils is exactly the food the hardest-hit neighborhoods need most."

## 0:20 — 0:50 · The real problem: a decision bottleneck
> "In Alameda, 182,000 people — 11% — are food insecure, concentrated in historically **redlined** neighborhoods like East Oakland and Fruitvale. And today, all of this is done **by hand**: every lot is typed in one by one into a spreadsheet, row by row, under pressure — so it's **slow, and it gets things wrong**: a mistyped date, a forgotten truck, and the product is already dead before anyone sees it. Every morning, one person at the dispatch desk has to weigh, all at once: what's about to expire, who needs it most, and which truck can actually deliver in time. Nobody can do that well under pressure. The result: fresh food rots on the dock, and 'habit' orders — the bread that always gets re-ordered — lock the wrong mix into exactly the highest-need blocks. That's **demand drift**."

## 0:50 — 1:10 · What our solution does (the statement)
> "So here's what we built. The hard part at a food bank isn't typing the record into a system — it's **the decision**: what's about to spoil, who needs it most, and what a truck can actually carry in time, made safely under pressure. We split that decision into **five agents, one constraint each**. **Facts go to deterministic code** — spoilage math, truck capacity, cold-chain — same answer every time, safety is never reasoned away. **Judgment goes to the LLM** — who needs it most, correcting drift, writing the multilingual notices. And a **learning layer**: the system reads its past lessons before deciding, and writes new ones after every run. Now let me show you — because it's live."

---

## 1:10 — 3:10 · LIVE DEMO (the core)

**→ Tab already on rescue.intrudr.io, pipeline view. You click "Run pipeline".**

> "This is running in production, on a real server. On the left, the five agents + the learning loop; on the right, they narrate their reasoning in real time. The data at the bottom — inventory, agencies, routes — is sourced: **USDA FoodKeeper** for shelf life, **Feeding America / Map the Meal Gap** for the Alameda need scores. Let me run it."

**🧾 Intake lights up**
> "**Intake** — no AI, just parsing. Each raw receiving line becomes a **traced lot**: an ID, the donor, the date, the condition, the category. That word matters — *traced*. Every unit has an identity, it's not a bulk pile. This is exactly what someone typed in by hand before — here it's parsed and traced in one pass. 20 lots, 8,630 pounds."

**⏱️ Risk lights up — the traceability moment**
> "**Risk** does the math — deterministic, from real USDA FoodKeeper shelf life. For each lot it computes **hours-until-unsafe**: strawberries in 'Fair' condition, already two days old, ~18 hours; raw chicken flips to 'at-risk' in under a day. This is the answer to *'where is the product that's about to be lost?'* — the system pinpoints the **exact lot, its remaining window, and where it's headed**, before it spoils. 8 lots at risk, 3,750 pounds. And it read two learned rules before scoring — that's the learning layer."

**⚖️ Need & Equity lights up**
> "**Need & Equity** — the real judgment. It ranks agencies by unmet need and catches **demand drift**: East Oakland, high need but bread-heavy orders, gets bumped up for produce and protein specifically because it's under-served. Watch the packets read from the learned-rules store."

**🚚 Logistics lights up — the hard gate**
> "**Logistics** — the hard gate. Cold-chain, truck capacity, delivery windows: deterministic, no vibes. Watch here — it **vetoes** the raw pork lot: it would need a refrigerated route, there's none for that ZIP, so it's pulled from the automated plan and flagged for manual handling. Physics wins."

**📋 Coordinator + the report appears**
> "**Coordinator** assembles the plan and writes each agency's pickup notice in **English, Spanish and Chinese** — the languages ACCFB serves. The outcome: **92% rescue rate.**"
> *(scroll to the contrast table)* "And the row that matters — the **status quo**, computed on the same data: 71%, spoils 1,100 pounds on non-refrigerated trucks, and delivers **zero pounds** to the highest-need agencies. We steer **2,600 pounds** to them. Same day, same data — that's the difference the agents make."

**Optional closers (if time allows)**
> "Total cost of that run: about a tenth of a cent." *(point to the LLM-calls chip)*
> "And if the API went down, it produces the exact same plan on the rule-based fallback — it degrades, it never crashes."
> *(optional 2nd run)* "Run it again and the learning counter ticks up — run #1 is good, run #100 is sharper."

---

## 3:10 — 4:10 · The proof (vs status quo)
> "And this isn't a claim — we compute the status quo on **every run**. The manual desk: 71%, spoils 1,100 pounds on warm trucks, delivers **zero** to the highest need. Us: **92%, zero spoiled, 2,600 pounds** to the neighborhoods furthest behind. And notice it's **not** 100% — it refused to put 300 pounds of raw pork on a dry truck and flagged it for manual handling. **Physics beats vibes.** A 100% would be a red flag, not a win."

## 4:10 — 4:40 · Close
> "The whole build is open on GitHub — the five agents, the orchestrator, the learning layer, real cited data. Today it reads CSVs; going to production is wiring four connectors to the food bank's real systems — inventory, dispatch, partner CRM — without touching the agent logic. **A connector change, not an architecture change.** Deployable today, useful tomorrow. Thank you."

---

## Safety net (if it's slow / offline)
- **Slow network / API hiccup:** "It's making real LLM calls over the network — one second… and there's the plan." (If it truly stalls, the fallback still produces a plan.)
- **Wifi dead:** show `examples/example_run_report.md` in the repo — "here's a saved run; the live one behaves identically."
- **Projector too small:** narrate from the nodes lighting up + the final 92% + the contrast table (large on screen).

## If you only get 15 seconds
> "Press run — five agents flag every at-risk **lot** by ID and hours-left, route it to the highest-need agency a truck can actually reach, refuse the unsafe move, and draft the notice in three languages. 92% vs 71% for the manual desk, live, for a tenth of a cent."

---

# THE LEARNING LAYER — principle, usage, utility (know this cold)

**Principle (how it works, in one breath).** It's a **read-before / reason / write-after** loop around an explicit rules file (`skills/learned_rules.json`), *not* model training. After every run, the **Risk** and **Need & Equity** agents emit *discoveries* — patterns they just saw ("Fair-condition Fresh Produce keeps surfacing as at-risk"; "agency A03 keeps drifting bread-heavy despite high need"). A small `learn()` step merges them: a brand-new pattern becomes a rule; a recurring one **reinforces** an existing rule (its confidence / times-seen goes up). On the **next** run, Risk and Need & Equity **read that file first** and use it as priors — pre-flagging that category, pre-correcting that agency's drift. Same code, sharper priors each run.

**Usage in a food bank's process.** It runs each morning on the day's inbound. Over weeks it accumulates **institution-specific** knowledge: which donors send near-expiry produce, which agencies chronically under-order protein, which categories always go critical same-day. The tacit knowledge a veteran coordinator carries in their head ("the Tuesday Safeway drop is always borderline") gets captured **explicitly**.

**Utility — why it matters for food banks specifically.**
- **Captures tribal knowledge before it walks out the door.** Food banks run on a few veteran coordinators' memory; when they leave, it's lost. This makes that knowledge explicit, persistent, and survivable across staff turnover.
- **Adapts to *this* food bank.** Alameda's drift patterns aren't Fresno's. It learns the local reality instead of shipping generic rules.
- **Transparent & auditable.** Rules are human-readable JSON a coordinator can read, edit, or delete — not opaque model weights. That's essential for a safety-sensitive, accountable nonprofit: nothing changes silently.
- **It compounds, with no retraining.** Run #1 is good; run #100 has confirmed which patterns are real and discovered new ones (two rules, `E-003`/`E-004`, didn't exist in the seed — the system wrote them itself). More valuable the longer it's deployed, for a tenth of a cent a run.

**One-liner:** "It's not the model learning — it's the *operation* learning. Every morning it writes down what it saw, reads it back tomorrow, and gets sharper — and every rule is plain text a human can audit."

---

# THE Q&A FIELDS — after the demo

*Ordered most-likely to least-likely. Short answer first, detail if pushed.*

### 1. "How are the agents orchestrated? And what happens if one goes down?"  ⭐ (asked)
> **Orchestration:** "It's a **LangGraph** graph — a linear `StateGraph`: Intake → Risk → Need & Equity → Logistics → Coordinator. Each agent is a node that reads a **typed shared state** and writes its contribution into it; the next one consumes clean data and doesn't care where it came from. That loose coupling is what lets us swap an agent's internals — e.g. point Need & Equity at the real CRM — without touching the others."
>
> **If an agent goes down:** "Two cases. (1) An LLM agent — Risk, Need & Equity, Coordinator — has its API go down or hallucinate: each has a **deterministic rule-based fallback**, so it produces the *same plan* without the API. We showed it: zero API key = same result. (2) The safety-critical agents — Risk (spoilage) and Logistics (cold-chain, capacity) — are **already** deterministic code, not LLM: they can't be 'reasoned' away. So the worst case is degrading to deterministic, never a crash and never an unsafe plan. It's advisory, not autonomous: a human validates the final plan."

### 1b. "How is this different from an agent that just automates data entry into a system?"  (only if asked — don't raise it yourself)
> "Those are two different layers. Automating a form is **execution** — and it's the commoditized part, and the *dangerous* part if an LLM writes to a system of record with no guardrail: one hallucinated field and the data's wrong. The part a food bank actually can't do is the **decision** — which perishable lot, to which highest-need agency, on which truck that won't break the cold chain, refusing the unsafe move — with a deterministic safety gate and a measurable rescue rate. We own the decision. Writing it into whatever system you run is just one of our output connectors. **Execution without a decision is faster typing; a decision without a safety gate is dangerous — we're the part that's hard to get right.**"

### 2. "When it's live, do the agents have good enough access to real data (routes, logistics)?"
> "Yes, by design — they read through an **adapter**. Today it's CSV; in production it's a connector to inventory (WMS), route-dispatch, and the partner CRM. We don't change agent logic — we point the connectors. FoodKeeper is already the real feed. **Intake is the single data entry-point**; everything downstream consumes clean, typed lots."

### 3. "How do you detect *where* the at-risk product is?" (traceability)
> "Every unit is a **traced lot**, not a pile: ID, donor, received date, condition, category — and its location as it moves: warehouse → assigned route/truck → agency. Risk computes **hours-until-unsafe per lot**, so at any moment we pinpoint the exact lot, where it is, how long it has left — and flag it *before* it turns. In the demo it names the lot: 'L19, 300 lbs raw pork, en route to ZIP 94704, at risk.' In production those IDs are your barcodes/SKUs from the WMS, and the truck link comes from dispatch or GPS."

### 4. "What if the AI hallucinates / the API goes down?"
> "Safety and capacity are deterministic code, not the LLM — impossible to 'reason' away. And every LLM step has a rule-based fallback: with no API at all, same plan. Demonstrated."

### 5. "Why five agents, not one?"
> "One agent judging spoilage + equity + capacity + writing in a single prompt dilutes a constraint and silently drops one. The split is exactly what lets the Logistics gate veto an equity match that physics forbids — the 300-lb pork veto. Each agent has a single, testable responsibility."

### 6. "How are the equity scores justified?"
> "Grounded in the real Alameda food-insecurity data — 11%, 182,000 people, with the documented intra-county gradient. In a pilot they'd be validated against the food bank's own equity data."

### 7. "What would a pilot look like?"
> "Low-risk, because it's **advisory, not autonomous**. Each morning, run it on the day's inbound, compare our plan to the human coordinator's, measure the rescue-rate delta. Connect one data source at a time."

### 8. "Does it really learn, or is it cosmetic?"
> "Real: after every run, the agents write their discoveries into `skills/learned_rules.json`, and Risk + Need read them *before* reasoning on the next run. Two rules (E-003, E-004) didn't exist at the start — the system discovered on its own that agencies A01 and A03 drift and wrote itself a standing correction. Run `--fresh` vs a warmed-up state to see the difference live."

### 9. "The cost / does it scale?"
> "~a tenth of a cent per run with gpt-4o-mini. At a food bank's scale it's one decision per morning, not a massive stream — cost is negligible, and the deterministic fallback is free."
