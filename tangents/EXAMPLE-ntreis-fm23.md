---
id: 20260905-ntreis-fm23
status: draft            # set to queued (via PR merge) when ready to run
priority: high
budget_cycles: 6
escalate_if: 2 failed cycles
origin: lkmot
---

# Fix NTREIS fm23 comps blocker (radius/type controls unavailable)

## Why (tie to operational goal)
Comps stage is failing fleet-wide (tangents.json comps FAILED/PARTIAL x3).
Every active order stalls at comps until this is fixed. Revenue-facing.

## Done when (machine-readable acceptance)
- [ ] A comps run completes search on a real order and produces
      matrix_search_results.jpg + CSV

## Out of scope (scope-drift fence)
- Spark CSV export fix (all_download_strategies_failed) — separate tangent
- Any NTREIS portal auth/session work unless it is the direct blocker

## Context pointers (expanded live at run time from the DBs)
- Ledger blocker: appraisal-pipeline:ntreis-fm23 (project-ledger.json, status: proposed)
- Evidence: tangents.json comps FAILED x3; business-state missing_comps
- KB: `kb-query.py service "NTREIS"`, `kb-query.py error "comps"`

## Outcome (filled by coo-loop, never by hand)
- (pending)
