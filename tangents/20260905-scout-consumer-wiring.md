---
id: 20260905-scout-consumer-wiring
status: queued
priority: medium
budget_cycles: 3
escalate_if: 1 failed cycle
origin: project-ledger proposed step (memory-knowledge:scout-consumer)
---

# Wire scout.candidate events into ledger blockers refresh

## Why
scout.candidate events die in the orphan event stream â€” opportunities never surface
as ledger blockers. Closing this makes the strategic layer's signal actually consumable.

## Done when
- [ ] scout.candidate events surface as ledger blockers with evidence (demonstrated on
      at least one real event)
- [ ] The consumer code path documented in the outcome block

## Out of scope
- Redesigning the event schema
- Touching strategic_review.py proposals logic
- scoper session failed, parked
