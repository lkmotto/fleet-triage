# Outcome — 20260905-strategic-outcomes-verify

- status: **success** (closed as classified; creation of `strategic_outcomes.jsonl` remains blocked upstream — follow-up tangent required, see below)
- executor: post-RESCOPE cycle, 2026-09-06, LEGION, harness `--auto` confirmed preflight
- artifacts:
  - `coo/tmp/20260905-strategic-outcomes-verify.run.log` (controlled proof run, full stdout/stderr)
  - `coo/tmp/20260905-strategic-outcomes-verify.guard-check.py` + `.out` (import-level guard proof)
  - `coo/tmp/20260905-strategic-outcomes-verify.diagnostic.py` + `diagnostic-rerun.out` (refreshed exact-call diagnostic)
  - prior-cycle `probe.py` retained (API health: 200 OK, key/endpoint healthy)
  - this note

## Done-when scoreboard

1. **Preflight harness check — PASS.**
   Execute path launches with `--auto`: `coo/coo-loop-v4.sh` L202 `local EXEC_AUTO="${COO_EXECUTE_AUTO:-medium}"` and L206/L208 `run_droid execute exec -o json --auto "$EXEC_AUTO"` (comment L200–201 documents the 2026-09-06 num_turns:0 fix). This cycle's executor ran multi-turn with unrestricted tool use (reads, writes, LLM-invoking scripts — none permission-aborted), so the final exec.log result will not be `num_turns:0`/insufficient-permission. Preflight passed → LLM spend authorized.
2. **Always-append code cited with exact line numbers — PRESENT (re-verified live this cycle).**
   `C:\Users\lkmot\.factory\scripts\strategic_review.py` (mtime 2026-08-24 17:11:47, 402 lines):
   - L48–49: `PROPOSALS_PATH` / `OUTCOMES_PATH = KNOWLEDGE / "strategic_outcomes.jsonl"`
   - L81–84: `_append_jsonl(path, record)` (mkdir parent, open append, json line)
   - L96–98: `_same_day_run_exists(run_id)` — any proposals row with matching run_id
   - L295–297: same-day guard fires only when `not dry_run and not no_file` (before any writes)
   - L309–330 early exits **before** append: `--dry-run` (309–312), missing DEEPSEEK_API_KEY (314–316), LLM falsy → `return 1` (328–330)
   - **L349–356: always-append IS present and unconditional relative to assessments** — comment L349 "Always write outcomes — even with empty assessments — so the measure loop is real, not phantom." then `_append_jsonl(OUTCOMES_PATH, {ts, run_id, assessments, no_prior_to_assess})`. (Contract cited 350–357; same block, verified exact.)
   - Note: `REVIEW_AGENT["max_tokens"] = 4096` at L57 (`deepseek-v4-pro`).
3. **Controlled proof run — DONE.** `python strategic_review.py --no-file` → exit 1, full console at `run.log`: snapshot 3619 chars, prompt 8540 chars, 2 priors to assess, `Calling deepseek-v4-pro...` → `[strategic-review] ERROR: The read operation timed out` → `ERROR: LLM call failed.` → exit 1 **before** the append block.
4. **Post-run artifact check — file still absent; failure proven upstream of append (evidence below).** No claim made that the append fix is missing.
5. **Same-day idempotency guard — VERIFIED** (import-level, read-only, `guard-check.out`):
   - `_same_day_run_exists("strategic-review-20260809")` → **True** (known historical id)
   - `_same_day_run_exists("strategic-review-20260906")` → **False** (never-seen id)
   - `_filed_runs()` → 1 (20260809); `_prior_proposals()` → 2; `_all_prior_hypotheses()` → 6
   - Loader side-finding re-measured: `_load_jsonl` parses **3 of 4** physical rows (BOM row dropped, `utf-8` decode)
   - Per contract: guard does **not** fire under `--no-file` (L295–297), so no full-run skip was claimed and no second full (filing) run was performed — filing is out of scope.
6. **Final note + root-cause class — this document.**
7. **Minimal patch branch — N/A / NOT TRIGGERED:** always-append code is present; the "if absent" patch clause does not apply. No code changes were made this cycle.

## Root cause — class: **upstream-LLM** (reproduced fresh this cycle)

Two independent measurements, both failures land **before** the L349–356 append:

- **Proof run (production path):** client-side read timeout. `strategic_agents.py` `_call_llm` L161: `urllib.request.urlopen(req, timeout=60)` — the server takes longer than 60s for this 2.3k-token-input reasoning workload, so production aborts ("The read operation timed out") before any response arrives. Call it **D3**.
- **Diagnostic rerun (same exact call, timeout=90):** HTTP 200 returned, but `finish_reason: length`, `usage.completion_tokens: 4096` with `completion_tokens_details.reasoning_tokens: 4096` (100% of budget consumed by reasoning), `reasoning_len: 18477` (mid-sentence tail), `content_len: 0` → `json.loads("")` raises `JSONDecodeError` → `_call_llm` returns None → run exits 1 at L328–330. This is **D1** (`max_tokens: 4096` starves deepseek-v4-pro's reasoning on this prompt), with **D2** still standing: empty/`length` finish_reason is unguarded.

Historical artifact-absence (why the file never existed between 08-24 and now) remains fully explained by **schedule-never-ran**: `\Factory-Strategic-Review` is Disabled (Last Result 267011) since the 2026-08-28 archive; the 08-24 patch never executed post-land. That class applies to history, not to this cycle's proof run.

Eliminated: `append-missing` (code present, L349–356) and `harness-permission-gate` (preflight passed this cycle; exec.log's three `num_turns:0` rows are pre-rescope sessions ff46aaab / dac3138a / 74b7e17c, dated 2026-09-05 22:51, predating the post-patch 12:22 runner).

## Ledger fairness judgment — append code specifically

The ledger step `memory-knowledge:outcomes-always-write` (status done, completed_at 2026-08-24) is **FAIR as scoped**: the unconditional append exists exactly as claimed, is reachable on any successful LLM path, and has never had one (schedule disabled + D1/D3 failures). The live metric `outcomes_file_exists: False` is also accurate. No false-done on the append claim itself; the gap is upstream and belongs to a different ledger step. `strategic-idempotency` (done) is likewise fair — guard verified True/False as designed, with the known `--no-file` carve-out.

## Spend disclosure

- 1 budgeted proof run (`--no-file`, flat $0.35 recorded to spend-ledger, run_id `strategic-review-20260906`) — failed upstream, no output row.
- 1 unbudgeted diagnostic call (same prompt, 6415 tokens total, est. <$0.35; refresh justified: proof-run log differed materially from prior cycle — timeout vs `length` — per contract's refresh-if-differs clause). No further LLM spend; no second starvation probe.
- Governance record appended to `agent-governance.jsonl` (internal research/verification, outcome success, risk low).

## Follow-up tangent (required — fenced here, do not implement in this tangent)

**Recommended id:** `20260906-fix-strategic-review-llm-truncation`
- D1: raise `REVIEW_AGENT["max_tokens"]` to 8192 in `strategic_review.py` (L57) and matching `deepseek-pro` config in `strategic_agents.py`; AGENTS.md BYOK note already documents reasoning models needing generous budgets.
- D3: raise production `_call_llm` client timeout from 60s (`strategic_agents.py` L161) to ≥180s for pro-class agents (measured server latency for this prompt: >60s, ≤90s).
- D2: guard `finish_reason == "length"` / empty content — retry once at higher budget, else `_append_jsonl` a **failure record** to `strategic_outcomes.jsonl` (so the measure loop sees failures, not silence) and exit non-zero.
- Micro: decode with `utf-8-sig` in `_load_jsonl` (BOM row drop re-measured this cycle).
- Exit criteria for that tangent: one `--no-file` run creates `strategic_outcomes.jsonl` with today's `run_id` (re-running this contract's steps 3–5 is sufficient).
- Operator decision (out of tangent scope): whether to re-enable `\Factory-Strategic-Review` so the fix stays proven weekly.
