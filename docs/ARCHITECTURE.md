# Architecture

## Design goals

1. **Reproducible and production-oriented**, not a scripted demo. Clean module boundaries, real config (`config.py`), documented interfaces so each agent could be repointed at ACCFB's live systems instead of our CSVs.
2. **One constraint per agent.** Each agent has a single testable responsibility. You can understand or replace one without reading the others.
3. **Deterministic where correctness is non-negotiable, LLM where judgment is genuinely required.**
4. **Never crashes on the model.** Every LLM step degrades to a rule-based fallback.
5. **Learns.** A skills/rules layer that agents read before reasoning and write after every run.

## Why LangGraph (orchestrator choice)

We evaluated three options the brief called out:

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Hand-rolled** sequential calls | Most predictable, zero dependency risk, trivial to stream | We'd re-implement state passing + per-node streaming by hand | Viable backup |
| **LangGraph** `StateGraph` | Graph maps 1:1 onto our fixed pipeline *and* the live node-graph viz; built-in typed shared state; per-node execution is easy to stream | One dependency to install | **Chosen** |
| **Strands Agents** (AWS) | `Pipeline`/`GraphAgent` primitives fit well, built-in observability | Newer, less documented — risk given a same-day deadline | Rejected on time risk |

We chose **LangGraph** because the five fixed nodes and their sequential edges map directly onto a `StateGraph`, the typed `PipelineState` gives us a single shared object every agent reads/writes, and the same node structure drives the frontend's node-graph animation. Critically, we do **not** use any dynamic/agentic sub-agent spawning: the five roles are fixed and known in advance (`orchestrator.PIPELINE`), which is exactly the predictability a live demo needs. If LangGraph were unavailable, `run_pipeline()` could fall back to a plain sequential loop over the same node functions — the agents don't depend on the framework.

## Pipeline & shared state

`orchestrator.build_graph()` wires: `START → intake → risk → need_equity → logistics → coordinator → END`.

The edges are sequential because the constraints genuinely depend on each other — you cannot rank agencies for a lot you have not yet risk-scored, and you cannot check truck feasibility for a match that does not exist yet.

State is a single `PipelineState` TypedDict (`state.py`). Each node returns a partial dict that LangGraph merges. A `_emit` callback rides in the state so every agent can stream progress events (`agent_start`, `reasoning`, `agent_done`, `final_report`) to the frontend over SSE — the same events print nothing extra in CLI mode.

## The agents

### 🧾 Intake — deterministic
Parses `inventory.csv`, `shelf_life_rules.csv`, `agencies.csv`, `routes.csv` into typed records. No model: parsing is not a judgment call. Output: `lots`, `shelf_life`, `agencies`, `routes`.

### ⏱️ Risk — deterministic core + LLM explanation
Deterministic and auditable:
- `effective_shelf_days = typical_shelf_life × condition_factor` (condition factor from `config.CONDITION_FACTOR`, grounded in learned rule `R-001`).
- `hours_until_unsafe = max(0, (effective_shelf_days − age_days)) × 24`.
- Network movement velocity per category = Σ (agency daily capacity × that category's share of the agency's recent orders). A lot is **at risk** if it cannot clear at current velocity before it goes unsafe, or has ≤ `AT_RISK_DAYS_BUFFER` days left.

The numeric flags are fixed *before* the LLM sees them. The LLM only interprets edge cases (Fair-condition produce, sub-48h protein, slow-moving categories) and explains each flag in one plain-language sentence. If unavailable, a rule-based template explains instead. Reads learned `risk` rules first.

### ⚖️ Need & Equity — LLM judgment + deterministic fallback
The one genuinely hard judgment call. Ranks agencies over unmet need, product fit, refrigeration, capacity, **and demand drift** — the signal that an agency's recent orders have diverged from its neighborhood's need (e.g., a need-92 pantry ordering 55% bread). A deterministic equity score (`_score`) is always computed as an auditable fallback and to seed the candidate ranking. Reads learned `need_equity` rules first. Produces a top-5 ranked candidate list per lot so Logistics can cascade.

### 🚚 Logistics — deterministic hard gate (by design)
Not an LLM, on purpose — documented as a deliberate design choice, not a limitation. A vehicle's capacity and a cold-chain requirement are facts. For each at-risk lot it tries the equity-preferred agency, then its runner-up, then the rest of the ranked list, checking: zip reachability, cold-chain (refrigerated route required for refrigerated categories), route remaining capacity, agency daily intake capacity, and delivery-window overlap. **Route capacity and agency capacity are shared resources that deplete as lots are assigned** — two big lots can't both claim the same slack. It can **veto** an equity-optimal match and cascade, or flag a lot as un-rescuable (surfacing the real fleet constraint).

### 📋 Coordinator — LLM synthesis + templated fallback
Groups feasible moves by agency, computes the Rescue Rate, and drafts a short warm notification per agency in English, Spanish, and Chinese. Missing languages are always backfilled from a template, so a notification always goes out.

## Learning layer

`skills/learned_rules.json` holds rules tagged by `agent` and `scope`, each with `confidence` and `times_reinforced`. `skills/learning.py`:
- `rules_as_text()` injects the relevant rules into Risk / Need & Equity prompts *before* they reason.
- `learn()` runs after the pipeline: a discovery whose `(agent, scope)` already exists **reinforces** it (bumps `times_reinforced` and confidence); a novel one is **appended** as a new rule. `runs_completed` increments.

This makes improvement measurable, not rhetorical: `runs_completed` and `times_reinforced` are the receipts. `--fresh` runs with an empty rules layer to show the "run #1" baseline.

## Failure & degradation

`llm.chat()` raises `LLMUnavailable` on missing key, auth failure, rate limit, network error, or malformed JSON. Each reasoning agent catches it and switches to its rule-based path, recording `mode = "fallback"`. The deterministic Risk math, Logistics gate, equity score, and multilingual templates mean the **plan and Rescue Rate are identical with or without the LLM** — the model adds natural-language nuance, not correctness.
