# Presentation Script — Perishable Rescue + Equity Coordinator

*9-slide deck, ~4 min + live demo. First-person "we". Every number on screen is cited (slide 8).*
*Live app: **https://rescue.intrudr.io** · Repo: **github.com/Mossab28/perishable-rescue***

---

**Slide 1 — Title**
> "Perishable Rescue + Equity Coordinator. Five specialized AI agents that replace the manual decision bottleneck at a food bank — safety-first, equity-aware, and it learns every run. It's live in production and I'll run it for you in about two minutes."

**Slide 2 — The Problem (1): no shortage of food, a shortage of time**
> "The problem isn't a lack of food. The U.S. had **70 million tons of surplus food in 2024** and only **13% of what could be donated actually is**. Feeding America rescues **4 billion pounds a year** — and **about 80% of wasted food is perishable**: meat, produce, dairy. Alameda's food bank alone moved 60 million pounds and rescued 11.6 million pounds of fresh food. But fresh food is on a clock — berries spoil in **hours**, raw chicken in **1–2 days** — and short on cold storage and reefer trucks, it spoils on the dock, paid for and then thrown away."

**Slide 3 — The Problem (2): the food that spoils is the food people need most**
> "And it's an equity problem. **182,000 people in Alameda — 11% — are food insecure**, and hunger concentrates in historically **redlined** neighborhoods like East Oakland and Fruitvale. Meanwhile agencies re-order bread out of habit, the desk honors the last order, and fresh food expires while the wrong food mix locks into exactly the highest-need blocks. That's **demand drift**. The root cause is a **decision bottleneck** — one person can't weigh spoilage, equity, and trucks at once under time pressure."

**Slide 4 — The Solution (1): five agents, one constraint each**
> "So we split the decision into five agents, each owning one constraint. **Facts go to deterministic code** — spoilage math, truck capacity, cold-chain — same answer every time, safety never reasoned away. **Judgment goes to the LLM** — who needs it most, correcting drift, multilingual notices. And a **learning layer**: Risk and Need read past lessons before deciding, and the system writes new patterns after every run. It never crashes — every step has a rule-based fallback."

**Slide 5 — The Solution (2): live-data ready**
> "Is this real or a demo? Each agent fetches data through a defined interface. Today it reads CSVs — but that's just one adapter. To go live you point four connectors at the food bank's real systems: inventory/WMS, route-dispatch, partner CRM, and USDA FoodKeeper which is already the real feed. The reasoning and the safety gate stay identical — **it's a connector change, not an architecture change.**"

**Slide 6 — The Demo (do it live)**
> "Let me show you. *(Open rescue.intrudr.io, hit Run pipeline.)* Watch each agent light up and explain itself with a real example, the data flows, and at the end you get the plan, the multilingual notices, and a live side-by-side against the status quo — twenty seconds, a fraction of a cent." → **use DEMO_SCRIPT.md for the play-by-play.**

**Slide 7 — The Proof: vs the status quo**
> "And it's not claimed — we compute the status quo on **every run**. Manual approach: 71%, spoils 1,100 pounds on warm trucks, delivers **zero pounds** to the highest-need agencies. Ours: **92%, zero spoiled, 2,600 pounds** to the neighborhoods furthest behind. And notice it's *not* 100% — it refused to put 300 pounds of raw pork on a dry truck and flagged it for manual handling. **Physics wins over vibes.**"

**Slide 8 — Sources**
> "Every number you've seen is grounded in public data — ReFED, Feeding America, ACCFB's annual report, USDA FoodKeeper, and the Map the Meal Gap food-insecurity data. It's all cited."

**Slide 9 — Close / GitHub**
> "The entire build is open on GitHub — five agents, the orchestrator, the learning layer, real cited data. Deployable today, useful tomorrow. Thank you."

---

## Q&A — prepared answers

**"How do you detect *where* the bad / at-risk product is in the supply chain?" (traceability)**
> "Every unit is a **traced lot**, not a bulk pile. Each lot carries an ID, its donor, received date, condition, category — and its location as it moves: warehouse → assigned route/truck → agency. The Risk agent computes **hours-until-unsafe per lot**, continuously, so at any moment we can pinpoint the exact lot, where it is, and how long it has left — and flag it *before* it goes bad, not after. In the demo you'll see it name the specific lot — 'L19, 300 lbs raw pork, on route to ZIP 94704, at risk.' In production those lot IDs are your existing barcodes/SKUs from the WMS, and the truck/route ties to dispatch or GPS — so traceability is exact, not estimated."

**"When it's live, do agents have good enough access to logistics, routes, real data?"**
> "Yes, by design — they read through an adapter. Today it's CSV; in production it's a connector to your inventory, route-dispatch and partner systems. We don't change agent logic — we point the connectors at your systems. FoodKeeper shelf-life is already the real feed."

**"What if the AI hallucinates or the API goes down?"**
> "Safety and capacity are deterministic code, not the LLM — they can't be reasoned away. And every LLM step has a rule-based fallback: with no API at all it produces the *same plan*. We demoed that."

**"Why five agents, not one?"**
> "One agent blurs food-safety with language generation and silently drops a constraint. The split is what lets the Logistics gate veto an equity-optimal match physics won't allow — the 300-lb pork veto."

**"How would a pilot work?"**
> "Low-risk, because it's advisory not autonomous. Run it each morning on the day's inbound, compare its plan to the coordinator's, measure the rescue-rate delta. Connect one data source at a time."

**"How are the equity scores justified?"**
> "Grounded in the real Alameda food-insecurity data — 11%, 182,000 people, with the documented intra-county gradient. In a pilot they'd be validated against the food bank's own equity data."
