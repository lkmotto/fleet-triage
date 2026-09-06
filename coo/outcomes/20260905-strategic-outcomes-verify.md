# Outcome — 20260905-strategic-outcomes-verify

- status: **partial** (environmental: yes — one failed cycle consumed; escalate condition met)
- executor: coo-scoper-approved contract, executed 2026-09-06 UTC (session on Legion)
- artifacts:
  - `coo/tmp/20260905-strategic-outcomes-verify.probe.py` (API health probe)
  - `coo/tmp/20260905-strategic-outcomes-verify.diagnostic.py` (exact-call replication)
  - `coo/tmp/20260905-strategic-outcomes-verify.guard-check.py` (read-only guard verification)
  - this note

## Done-when scoreboard

1. **Inspect always-append, cite line numbers — DONE.**
   `C:\Users\lkmot\.factory\scripts\strategic_review.py` (mtime 2026-08-24 17:11):
   - Always-append IS present: **lines 350–357** — `_append_jsonl(OUTCOMES_PATH, {ts, run_id, assessments, no_prior_to_assess})` with comment "Always write outcomes — even with empty assessments". `OUTCOMES_PATH` defined line 49.
   - Same-day guard: `_same_day_run_exists` lines 96–98; enforcement **lines 295–297** (skips only full runs, before any writes).
   - Critical detail: the append block executes **only after a successful LLM call and JSON parse**. Early exits that leave outcomes unwritten: `--dry-run` (309–312), same-day guard (295–297), missing key (314–316), LLM failure (328–330).

2. **Run once and confirm outcomes file created — NOT MET.**
   Run `strategic_review.py --no-file` (run_id `strategic-review-20260906`) failed:
   `ERROR: Expecting value: line 1 column 1 (char 0)` → exit 1 **before** the append block.
   `strategic_outcomes.jsonl` still absent after the run (verified).

3. **Patch path — N/A.** The "if absent" branch does not apply: the append code IS present.
   The real defect is elsewhere (below), and fixing it is fenced by this contract.

4. **Same-day idempotency guard — VERIFIED (logic-level, read-only).**
   Against real data via module import (no writes):
   - `_same_day_run_exists("strategic-review-20260809")` → True (guard would trigger)
   - `_same_day_run_exists("strategic-review-20260906")` → False (no-op expected)
   - `_all_prior_hypotheses()` → 6 hypotheses across all runs (dedup input correct)
   - `_filed_runs()` → 1 filed run (20260809, 2 prior proposals to assess)
   Runtime end-to-end second-run proof is blocked by defect D1 below; the guard itself
   short-circuits before any file writes (lines 295–297), so duplicate-proposal risk
   from the guard is zero as written.

## Root cause of the failed run (measured, not guessed)

Exact replication of the strategist call (same 8508-char prompt, same params):

- `finish_reason: length`
- `usage.completion_tokens: 4096`, `completion_tokens_details.reasoning_tokens: 4096`
- `content_len: 0` (all budget consumed by reasoning) → `json.loads("")` raises → exit 1

Standalone tiny-prompt probe returned 200 with valid JSON, so key + endpoint + auth are healthy.
The bug is **D1: `REVIEW_AGENT["max_tokens"] = 4096` is too small for deepseek-v4-pro's
reasoning pass on this prompt** (matches the AGENTS.md BYOK note that reasoning models
need generous max_tokens; 4096 was the fix for empty output on small prompts but starves
this 2.3k-token-input reasoning task). Secondary contributing defect **D2: empty/`length`
finish_reason is unguarded** — the script treats a truncated response as an LLM failure and
exits before writing anything.

## Why "done" never produced an artifact

Two independent reasons, both now evidenced:
1. **No runner:** strategic-review automation archived 2026-08-28 (SCHEDULES.md),
   `\Factory-Strategic-Review` Task Scheduler task Disabled → the 2026-08-24 patch was
   never executed post-land, so nothing could create the file. All REVIEW-20260824…
   20260905 signals correctly kept reporting `exists: False`.
2. **D1/D2:** even a manual run today fails before the append (measured above), burning
   $0.35 spend (spend-ledger row for `strategic-review-20260906`) with no output row.

## Side findings

- `strategic_proposals.jsonl` has a UTF-8 BOM; `_load_jsonl` (plain `utf-8`) silently
  drops row 1 (a 20260809 run with 3 proposals) from guard/dedup inputs. One-line fix:
  decode with `utf-8-sig`. Minor, separate from D1/D2.
- No duplicate-proposal or double-filing risk observed from the verify path itself.

## Rescope recommendation (needs a new tangent — fenced here)

New bounded tangent: **"Fix strategic_review LLM truncation so outcomes always land"**
- Fix D1: raise `REVIEW_AGENT.max_tokens` (8192) in `strategic_review.py`.
- Fix D2: on `finish_reason == "length"` or empty content, retry once at higher budget,
  else write a failure record to `strategic_outcomes.jsonl` (so the measure loop sees
  failures instead of silence) and exit non-zero.
- Optional micro-fix: `utf-8-sig` decode in `_load_jsonl`.
- Then re-run this contract's steps: one `--no-file` run (outcomes file must appear),
  one full run same UTC day (guard must no-op, no duplicate proposals).
- Operator decision afterwards (out of scope here): whether to un-archive the Sunday
  schedule so the fix stays proven.

## Spend / governance disclosure

- Failed run recorded $0.35 to spend-ledger (`strategic-review-20260906`, outcome allowed).
- Governance record for this execution appended to agent-governance.jsonl (outcome: partial).
