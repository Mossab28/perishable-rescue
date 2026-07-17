# Perishable Rescue + Equity Coordinator — Presentation Script

*Speaker notes, slide by slide. ~5–6 min. Natural, first-person "we". Live demo at the end.*
*Live app: **https://rescue.intrudr.io** · Repo: **github.com/Mossab28/perishable-rescue***

---

### Slide 1 — Title
> "This is **Perishable Rescue + Equity Coordinator**. In one line: we replace the manual decision bottleneck at a food bank with five specialized AI agents — it's safety-first, equity-aware, and it gets sharper every time it runs. It's already live in production, and I'll run it for you at the end."

### Slide 2 — The operational bottleneck
> "Food banks move **60 million pounds a year** through hundreds of agencies. **95% of what they rescue now is perishable** — fresh produce, protein, dairy. So the constraint isn't *food*, it's **time**: manual sorting and routing are simply too slow for fresh goods."

### Slide 3 — The 48-hour clock
> "Fresh food runs on a clock the manual desk can't beat. Berries and greens go in **hours**; raw meat is safe **1–2 days**. Warehouses are short on cold storage and refrigerated trucks, and there's no automated flagging — so fresh food spoils on the dock while one person juggles everything at once."

### Slide 4 — Two failures, one root cause
> "That creates two failures. **Operationally**, 5–7% of already-rescued food is lost — millions of pounds paid for and thrown away. And an **equity** failure: 1 in 9 Alameda residents — 182,000 people — are food-insecure, concentrated in East Oakland and Fruitvale, tracing decades-old redlining. Both come from the same root cause."

### Slide 5 — Demand drift
> "That root cause is **demand drift**. Agencies re-order bread out of habit; the desk 'honors the last order'; so bread ships while fresh food expires — and the wrong food mix quietly locks into the highest-need neighborhoods. **A standing order is a flawed signal.** Following it blindly is the bug."

### Slide 6 — Why multi-agent (say this one with conviction)
> "So why five agents instead of one big prompt? Because a single agent judging shelf-life, equity, truck capacity *and* writing outreach all at once will **silently drop one constraint** under pressure — usually safety. We split it: **facts go to deterministic code, judgment goes to the LLM**, and strict boundaries mean an AI opinion never blurs with a physical safety rule."

### Slide 7 — Deterministic vs LLM
> "Concretely: the deterministic side calculates reality and enforces safety — spoilage math, truck capacity, route feasibility — same answer every time. The LLM side weighs the genuinely human question: **who needs it most**, and how to correct drift. Physics wins; 'who needs it most' needs judgment."

### Slide 8 — The pipeline + learning layer
> "Five agents in sequence: Intake, Risk, Need, Logistics, Coordinator. And the piece I'm proudest of — the **learning layer**. Risk and Need read past lessons *before* they reason, and the system writes down new patterns — like a recurring drift — after every run. Never crashes: every step has a rule-based fallback. Run #1 is good; run #100 is exceptional."

### Slide 9 — Phase 1 (Intake + Risk)
> "Intake turns a messy receiving line — '120 lbs strawberries, July 15, Fair, Safeway' — into a clean typed lot. Then Risk does the math: effective shelf-life minus age, times 24, gives exact **hours-until-unsafe**, and auto-flags the critical lots. Raw meat at zero hours gets caught immediately."

### Slide 10 — Phase 2 (Need, Logistics, Coordinator)
> "Need ranks agencies and applies a **drift boost** to the under-served ones. Logistics is the **hard gate** — cold-chain, capacity, windows — and it vetoes anything physics won't allow. Coordinator assembles the plan and writes the pickup notice in English, Spanish and Chinese."

### Slide 11 — Proven against the status quo (the money slide)
> "And this isn't just claimed — we **compute the status quo on every run**. The manual approach rescues 71% and, because it ignores the cold chain, **spoils 1,100 pounds on warm trucks** and delivers **zero pounds** to the highest-need agencies. Our pipeline: **92%, zero spoiled, 2,600 pounds** steered to the neighborhoods furthest behind."

### Slide 12 — The 92% outcome
> "92% same-day rescue rate. It corrected drift, cascaded capacity when an agency filled up, and logged what it learned for tomorrow."

### Slide 13 — The 300 lb veto
> "And notice it's **not** 100% — that would mean a dangerous, unconstrained AI. It refused to put 300 lbs of raw pork on a non-refrigerated truck and flagged it for manual handling. **Physics wins over vibes. Safety overrules optimization.**"

### Slide 14 — Live-data ready (answer to 'how does it connect to real systems?')
> "Now — 'is this real, or a demo?' Each agent already fetches its data through a **defined interface**. Today that interface reads our CSVs — but that's just **one adapter**. Intake is the single data-entry point; every downstream agent consumes clean typed records and doesn't care where they came from. To go live at a food bank you don't rewrite anything — you point four connectors at their real systems: the **inventory / warehouse system** for lots, the **route-dispatch system** for trucks and cold-chain, the **partner directory / CRM** for agencies, and USDA FoodKeeper for shelf-life, which is already real. The reasoning, the safety gate, the learning — all unchanged. **It's a connector change, not an architecture change.**"

### Slide 15 — Live demo
> "Let me show you. *(Open rescue.intrudr.io, hit Run pipeline.)* Watch the five agents light up, each explains what it's doing with a real example, the data flows, and at the end you get the rescue plan, the multilingual notices, and that side-by-side against the status quo — live, in about twenty seconds, for a fraction of a cent."

### Slide 16 — Close / GitHub
> "The entire build is open on GitHub — five agents, the orchestrator, the learning layer, real USDA and Alameda data, README and architecture. It's deployable today, and it's genuinely useful tomorrow. Thank you."

---

## Q&A — prepared answers

**"When it's live, do the agents have good enough access to logistics, routes, real data?"** *(the key one)*
> "Yes — and that's by design. The agents don't hard-code data; they read through an adapter interface. Right now the adapter is CSV; in production it's a connector to your inventory system, your route/dispatch system, and your partner CRM. We don't need to change any agent logic — we need to know *which* systems you run, and point the four connectors at them. Shelf-life data is already the real USDA FoodKeeper feed."

**"How do you know the equity scores are right?"**
> "The need scores are grounded in the real Alameda County food-insecurity data — 11%, 182,000 people, with the well-documented intra-county gradient. In a pilot they'd be validated against the food bank's own equity data and partner relationships."

**"What if the AI hallucinates or the API goes down?"**
> "Two safeguards. Safety and capacity are deterministic code, not the LLM — they can't be reasoned away. And every LLM step has a rule-based fallback: with no API at all, it produces the *same plan*. We demoed that."

**"Isn't a single agent simpler?"**
> "Simpler to build, worse to trust. One agent blurs food-safety with language generation and silently drops a constraint. The split is what lets the Logistics gate veto an equity-optimal match that physics won't allow — you saw the 300-lb pork veto."

**"How would a pilot work?"**
> "Low-risk, because it's advisory, not autonomous. Run it each morning on the day's inbound, compare its plan to the coordinator's, and measure the rescue-rate delta. Connect one data source at a time."
