---
id: 20260905-strategic-outcomes-verify
status: scoping
priority: medium
budget_cycles: 2
escalate_if: 1 failed cycle
origin: COO v1 audit (REVIEW-20260905 signals: outcomes file exists=False)
---

# Verify strategic_outcomes.jsonl always-write fix actually landed

## Why
project-ledger-daily marked the always-append fix "done" but the 09-05 signals still
reported "strategic_outcomes.jsonl exists: False". A "done" fix that didn't land is
exactly the failure mode this pipeline exists to catch.

## Done when
- [ ] strategic_review.py inspected: the always-append code path verified present or
      absent (cite line numbers)
- [ ] If present: run strategic_review.py once and confirm strategic_outcomes.jsonl
      is created/appended (file exists after run)
- [ ] If absent: minimal patch applied, then run once and confirm file created; patch
      documented in the outcome block
- [ ] Same-day idempotency guard confirmed working (second run = no duplicate proposals)

## Out of scope
- Rewriting strategic_review.py beyond the minimal append fix
- Touching proposals content or the Sunday schedule
