---
id: 20260906-e2e-stage4-truetracts-repair
status: scoping
priority: high
budget_cycles: 6
escalate_if: 2 failed cycles
origin: pinned-session:c8b23b5d-e1be-452c-b9b4-3eb073b825e6
filed_by: coo-pin-bridge
filed_at: 2026-09-06
---
# e2e Stage 4: TrueTracts repair after site remodel

## Why
Stage 4 of the e2e automated appraisal pipeline (TrueTracts data acquisition) went
offline when TrueTracts remodeled their site. Stage 3 is in its best state yet;
stage 4 is the next domino. Operator pinned this as high priority.

## Done when
- [ ] Stage 4 daemon completes a full TrueTracts acquisition pass against the NEW site UI without manual intervention (artifact: run log + acquired data for a test submarket)
- [ ] e2e chain document updated to reflect the new UI flow (selectors/steps that changed)
- [ ] Verified: one end-to-end stage 3 -> stage 4 handoff produces non-empty stage-4 output

## Out of scope
- Stage 3 comp-selection logic changes
- Stage 5 SFREP report assembly
- Any TrueTracts account changes, purchases, or credential rotation

## Context (operator intent from pinned session)
- Operator: "truetracts remodeled their site so daemon needs to go back and look at
  the new UI process to get stage 4 truetracts back online with the e2e stages
  especially now that stage 3 is in a better place then it ever has been"
- Legacy session transcript (mine it for the old working flow + what broke):
  C:\Users\lkmot\.factory\sessions\-C-Users-lkmot-factory-context-code\c8b23b5d-e1be-452c-b9b4-3eb073b825e6.jsonl
