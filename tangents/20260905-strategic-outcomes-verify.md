---
id: 20260905-strategic-outcomes-verify
status: queued
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

## Outcome (filled by executor)
- status: partial (environmental: yes — 1 failed cycle, escalate condition met)
- artifacts: coo/outcomes/20260905-strategic-outcomes-verify.md (full findings);
  coo/tmp/20260905-strategic-outcomes-verify.{probe,diagnostic,guard-check}.py
- what was done: Always-append code verified PRESENT (strategic_review.py lines 350–357;
  guard 96–98/295–297). Real run with --no-file failed before append: DeepSeek reasoning
  consumed all 4096 max_tokens (finish_reason=length, content empty) → json.loads("") exit 1.
  Reproduced exactly via diagnostic script; key/endpoint healthy via minimal probe.
  Same-day guard logic verified read-only against real data (20260809→True trigger,
  20260906→False; dedup set 6 hypotheses; filed-run filter correct). No patch applied —
  the required fix (raise max_tokens / handle length-finish) is fenced by this contract.
- what remains: New tangent needed: "Fix strategic_review LLM truncation so outcomes
  always land" (max_tokens 8192 + length-finish retry/failure-record + optional
  utf-8-sig BOM fix), then re-run this contract's proof steps. Root cause of the
  prolonged False signal: automation archived 2026-08-28, so the 08-24 patch never ran.
- rescope note: Mid-flight bail not required; contract executed to its verifiable edge.
  D1 (max_tokens starvation) and D2 (unguarded empty/length content) documented in
  outcome note for scoping the follow-up.
