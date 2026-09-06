---
id: 20260906-e2e-stage3-comp-certainty
status: scoping
park_note: un-parked by operator session 2026-09-06 15:2x - both scope failures were num_turns:0 exec crashes (e2342232 + prior), scoper never evaluated; requeue until a real verdict lands
priority: high
budget_cycles: 6
escalate_if: 2 failed cycles
origin: pinned-session:3e537a32-6724-4d54-ba73-7157d4dce57f
filed_by: coo-pin-bridge
filed_at: 2026-09-06
---
# e2e Stage 3: comp-selection certainty in a defined submarket

## Why
Stage 3 (comp picking) needs to reach certainty on which comps to choose within a
defined submarket. Operator wants logic-driven certainty and explicitly ordered a
RECYCLER-FIRST approach: prove whether existing/free sources close the gap before
any new spend (the MLS API option costs $200/month and the operator suspects low
marginal improvement over the UI).

## Done when
- [ ] Gap analysis artifact: what stage 3 needs for certainty vs what current sources provide (cited per field)
- [ ] Recycler search executed and recorded (parts-bin entry + verdict: REUSE/ADAPT/BUILD for the top candidate)
- [ ] Recommendation memo: close-the-gap plan ranked by contributoryness, with the $200/mo MLS API explicitly scored last-if-at-all

## Out of scope
- Purchasing the MLS API or any paid data source (hard fence: spend requires operator approval)
- Stage 4 TrueTracts repair (separate tangent, same day)
- Stage 5 SFREP wiring

## Context (operator intent from pinned session)
- Operator: "reach our goal of achieving certainty through logic in a defined
  submarket, also before we keep allocating resources do a recycler search to see
  if there are compliments out there that can help us without deepening our
  investment"
- Legacy session transcript:
  C:\Users\lkmot\.factory\sessions\-C-Users-lkmot-factory-context-code\3e537a32-6724-4d54-ba73-7157d4dce57f.jsonl

## OPERATOR ADDENDUM 2026-09-06 15:05 — BINDING ON RE-SCOPE (handoff artifact)

Today's evidence: stage-4 ran against 5 orders, 4 of which had NO comps\spark_export.csv — TrueTracts
self-picked comps and the operator found improper addresses in the resulting TDCX. Stage 3 is the source
of the comp set; without its artifact stage 4 must not run.

Binding additions on re-scope:
1. Done-when: for every order stage 3 certifies, EMIT the handoff artifact in the Big Sky shape:
   `comps\spark_export.csv` (>=1 data row) + `subject\truetracts_mls_import_status.json` (discovery fields).
2. Done-when: an explicit stage-4 gate list — orders certified (CSV emitted) vs orders BLOCKED for
   stage 4 (no CSV) — recorded in the outcome artifact so the sibling stage-4 tangent consumes it.
3. Recycler-first ordering and the no-spend fence (MLS API $200/mo) are unchanged.
- scoper returned no contract twice, parked for operator review
