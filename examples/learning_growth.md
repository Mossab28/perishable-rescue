# Learning Growth — Run #1 vs Run #100

The Skills/Rules layer is read by the Risk and Need & Equity agents *before* they reason, and written after every run. Same pipeline, sharper priors over time.

| Metric | Fresh (seed) | After 100 runs |
|---|--:|--:|
| runs_completed | 0 | 100 |
| total rules | 4 | 6 |

## Rule reinforcement (times a rule was confirmed by real runs)

| Rule | Scope | Fresh | After 100 |
|---|---|--:|--:|
| R-001 | category:Fresh Produce | 3 | 103 |
| R-002 | category:Meat & Poultry | 5 | 105 |
| E-001 | zips:94621,94607,94601 | 4 | 4 |
| E-002 | pattern:demand-drift | 2 | 2 |
| E-003 | agency:A01 | — | 100 |
| E-004 | agency:A03 | — | 100 |

**Newly discovered rules** (did not exist in the seed): E-003, E-004

