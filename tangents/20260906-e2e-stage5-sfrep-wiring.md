---
id: 20260906-e2e-stage5-sfrep-wiring
status: scoping
priority: high
budget_cycles: 6
escalate_if: 2 failed cycles
origin: pinned-session:3c80cca2-de30-481c-8be7-de57ba1df66e
filed_by: coo-pin-bridge
filed_at: 2026-09-06
---
# e2e Stage 5: SFREP report assembly wired to real workfile data

## Why
Stage 5 (SFREP report assembly) is the last domino for e2e automated appraisal
report production. It currently displays placeholder data despite the workfiles
having essentially all fields needed. Either not wired correctly or not wired in
at all. Operator pinned this as high priority.

## Done when
- [ ] Diagnosis artifact: root-cause memo stating exactly where stage 5 gets its field data and why placeholders appear (path cited)
- [ ] Stage 5 renders a test report from a real workfile with zero placeholder fields (artifact: exported/printed report + field checklist diff)
- [ ] SFREP session safety rules followed (AGENTS.md): single agent-owned session, resource gate before/after

## Out of scope
- Stage 3/4 data acquisition changes
- Any SFREP report DELIVERY to clients (hard fence: no delivery)
- Switching appraisal form software

## Context (operator intent from pinned session)
- Operator: "stage 5 on the e2e... last domino to fall to establish e2e automated
  appraisal report production and right now either its not wired correctly or its
  not wired in at all displays place holder data dispite us having basically a full
  boat in terms of workfile data"
- Legacy session transcript:
  C:\Users\lkmot\.factory\sessions\-C-Users-lkmot-factory-context-code\3c80cca2-de30-481c-8be7-de57ba1df66e.jsonl
