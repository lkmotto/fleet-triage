---
id: 20260905-spark-csv-export
status: scoping
priority: high
budget_cycles: 4
escalate_if: 2 failed cycles
origin: project-ledger proposed step (appraisal-pipeline:spark-csv)
---

# Fix NTREIS Spark CSV export (all_download_strategies_failed)

## Why
Spark CSV export fails with all_download_strategies_failed (Playwright download capture
bug) so sfrep MLS import cannot consume comps. Separate from the fm23 controls blocker.

## Done when
- [ ] A Spark CSV export succeeds on a real order and the CSV lands in that order's
      workfiles; sfrep MLS import no longer reports no-CSV skip

## Out of scope
- The fm23 radius/type controls blocker (separate tangent, in flight)
- Auth/session rearchitecture; any portal mass actions
