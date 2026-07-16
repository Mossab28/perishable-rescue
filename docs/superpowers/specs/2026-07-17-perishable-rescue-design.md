# Perishable Rescue + Equity Coordinator — Design Spec

**Date:** 2026-07-17
**Context:** AISCO Hackathon (AI Objectives Institute — food banks + AI agents). Judging tomorrow AM. Real operational problem for Alameda County Community Food Bank (ACCFB). Built as production-oriented software, not a throwaway demo.

## Problem

Two real problems from ACCFB's challenge brief, fused into one pipeline:
1. Perishable inventory ages past its safe distribution window before anyone reallocates it.
2. Partner-agency orders drift from what their neighborhood actually needs, making allocation manual guesswork.

## Solution

A five-agent pipeline that, for a given day's inbound food, decides: which lots are at expiry risk, which underserved agency should get them, whether a route can carry them in time, and drafts the agency notification. A Skills/Rules learning layer makes each run sharper than the last.

## Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| LLM provider | OpenAI (`gpt-4o`, via `OPENAI_MODEL` config) | User has an OpenAI key on the demo machine |
| Orchestrator | LangGraph `StateGraph` | Built-in per-node state streaming maps onto the live node-graph viz + the fixed pipeline |
| Frontend | FastAPI + SSE + single-page SVG node graph | Full visual demo; no build step = nothing to break live |
| Logistics + core shelf-life math | Deterministic (no LLM) | Hard constraints don't get a "vibe" — deliberate design choice |
| Language | Python 3.10+ | LangGraph requirement |

## Architecture

```
Intake → Risk → Need&Equity → Logistics → Coordinator → Report
                   ↑______ skills/learned_rules.json ______↑  (written after each run)
```

- LangGraph `StateGraph` over a typed `PipelineState`.
- Each node pushes progress/reasoning events onto an `asyncio.Queue`; FastAPI drains it to the browser over SSE → animated packets + live reasoning panel.
- Sequential edges: constraints genuinely depend on each other (can't rank agencies for a lot not yet risk-scored).

## Components (one constraint per module)

1. **`agents/intake_agent.py`** — deterministic. Parse `inventory.csv` → `Lot` records (product, qty, received_date, condition, donor). No LLM.
2. **`agents/risk_agent.py`** — deterministic core math: `hours_until_unsafe` from shelf-life (`shelf_life_rules.csv`) − age, vs. movement velocity → flags lots that won't be consumed before expiry. **OpenAI call** interprets edge cases + explains each flag in plain language. Reads `learned_rules.json` first.
3. **`agents/need_equity_agent.py`** — **OpenAI reasoning**. Ranks agencies by unmet need, capacity, refrigeration, hours, product fit, AND drift of recent orders from neighborhood baseline need. Reads `learned_rules.json`.
4. **`agents/logistics_agent.py`** — **deterministic hard gate**: capacity, cold-chain, delivery windows, incremental stops. Documented as intentional.
5. **`agents/coordinator_agent.py`** — **OpenAI synthesis** → final rescue plan (lot→agency→route) + short multilingual notification per agency.

Every LLM step has a **rule-based fallback** (heuristic ranking / template explanation) so the pipeline degrades gracefully and never crashes if the API is down.

## Learning layer

- `skills/learned_rules.json`, seeded with ~4 starter rules, each with `run_count` and provenance.
- A `learn()` step after each run appends newly discovered patterns (shelf-life exception, chronically-underserved agency).
- Risk + Need&Equity read it before reasoning.
- `--fresh` vs `--experienced` toggle + committed before/after snapshot → "run #1 vs run #100" improvement is visually provable.

## Data (`data/`) — real where a public source exists

| File | Real vs synthetic |
|---|---|
| `shelf_life_rules.csv` | **Real** — USDA FoodKeeper storage-life data |
| `agencies.csv` `current_need_score` | **Real basis** — Feeding America Map the Meal Gap / Census, Alameda County food insecurity |
| `agencies.csv` identities, `inventory.csv`, `routes.csv` | Synthetic (private operational data, no public source) |
| ACCFB backdrop figures (~60M lbs/yr, ~20 trucks/day, 350+ agencies) | **Re-verified** during build, cited in README |

~20 inventory lots, ~10 agencies, ~4 routes, ~5 product categories. All provenance in `docs/DATA_SOURCES.md` with a real-vs-synthetic column.

## Deliverables (repo tree)

`README.md` (Mermaid diagram, Rescue Rate metric = lbs allocated in time ÷ lbs at risk, explicit "why multi-agent" + "why it keeps improving" sections), `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md`, 5 agent modules, `orchestrator.py`, `server.py`, `frontend/index.html`, 4 CSVs, seeded `skills/learned_rules.json`, committed `examples/example_run_report.md`.

## Build order (protects the non-negotiable)

1. Data (fetch real + generate synthetic)
2. 5 agents + LangGraph orchestrator end-to-end, terminal output — **priority 1, non-negotiable**
3. README + Mermaid diagram + docs — priority 2
4. FastAPI backend + SVG node-graph frontend — priority 3 (stretch)
5. Pre-test pipeline several times against committed dataset so tomorrow's live run is known-good

## Success criteria

- `python orchestrator.py` runs all 5 agents end-to-end and always produces a report, even with the API down.
- README + architecture diagram render on GitHub.
- Frontend shows nodes, animated flow, live reasoning, and final report.
- Learning layer demonstrably changes behavior between a fresh and an experienced run.

## Non-goals (YAGNI)

- No dynamic/runtime sub-agent spawning (five roles fixed).
- No live scraping / camera / voice at demo time — everything runs offline against committed CSVs.
- No auth, no persistence DB, no multi-day scheduling.
