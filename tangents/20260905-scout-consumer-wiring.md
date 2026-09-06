---
id: 20260905-scout-consumer-wiring
status: validating
assessor_session: 69d072c9-cf0b-4153-a5a1-7d61428aaf3b assess
executor_session: a30fae46-b542-4e9e-997e-27dd010fdff8 running
priority: medium
budget_cycles: 3
escalate_if: 1 failed cycle
origin: project-ledger proposed step (memory-knowledge:scout-consumer)
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# Wire scout.candidate events into ledger blockers refresh

## Why
`scout.candidate` opportunity signals only flip a perpetual presence flag and never
become actionable ledger blockers — the strategic layer emits signal that no operator
surface consumes. Wiring them into the propose-only `project_ledger.py` refresh makes
that signal consumable in the operator review pack (project-ledger.json + REVIEW pack),
closing ledger step `memory-knowledge:scout-consumer` without reviving the archived
GitHub-issue mill.

## Done when
- [ ] `C:\Users\lkmot\.factory\knowledge\project-ledger.json` contains >=1 blocker or
      blocker-evidence update derived from a real `scout.candidate` in
      `strategic_events.jsonl`, with evidence citing a concrete `event_id` and/or
      candidate key (e.g. `factory::consolidation`)
- [ ] A `python C:\Users\lkmot\.factory\scripts\project_ledger.py --propose-only` run
      (dry-run proof plus one forced write `--force` if the same-hour run lock blocks)
      updates `metrics._last_evidence.scout_candidates_unconsumed` using true
      unconsumed logic — consumed candidates no longer keep the flag true solely
      because historical events exist
- [ ] `C:\Users\lkmot\.factory\knowledge\ledger-outcomes.jsonl` gains a run/assessment
      line covering the scout consumption path
- [ ] Outcome documentation names the consumer code path + verification commands,
      written into the tangent Outcome section and/or the ledger step
      `memory-knowledge:scout-consumer.outcome`

## Out of scope
- Redesigning the `scout.candidate` event schema
- Touching `strategic_review.py` proposals logic
- Restoring automated GitHub issue filing from scout (archived consumer behavior)
- Mass email sends, production deploys, DNS/network changes, data deletion (hard fences)
- Building a new always-on scheduler/Task system beyond proving one ledger refresh path
- Clearing/deleting historical `strategic_events.jsonl` rows
- Resolving unrelated blockers (`outcomes-phantom`, `strategic-dupe`, appraisal/sales blockers)

## Context (verified during scoping)
- Step still open: `C:\Users\lkmot\.factory\knowledge\project-ledger.json` → project
  `memory-knowledge` → step `memory-knowledge:scout-consumer` (`status: proposed`,
  `outcome: null`); blocker `scout-orphan` (summary: no downstream consumer) since
  `2026-07-28`; daily outcomes keep assessing `memory-knowledge:scout-orphan
  still-live` through `2026-09-06`.
- The bug: `project_ledger.py` `_gather_evidence()` sets
  `scout_candidates_unconsumed = any(type == "scout.candidate")` over the last 300
  events (presence, not consumption), so `EVIDENCE_RULES["scout-orphan"]` can never
  clear.
- Event bus: `C:\Users\lkmot\.factory\knowledge\strategic_events.jsonl` holds 5 real
  `scout.candidate` events (all 2026-07-28, source `memory-distill`): domains
  `timeout` (event_ids `534afb77993a`, `58fa680c8052`), `factory`
  (`6ee600d48573`, `d7b606140412` — candidate key `factory::consolidation`),
  `ntreis` (`f82212d3178b`). Cursor `strategic_event_cursor.json` is stale at
  `2026-08-06T20:45:22Z`; the ledger refresh path reads the file directly, so the
  cursor is not a prerequisite.
- Prior consumer: live `C:\Users\lkmot\.factory\scripts\scout_consumer.py` does NOT
  exist (only `scripts\__pycache__\scout_consumer.cpython-314.pyc`, 2026-07-28);
  archive copy at
  `C:\Users\lkmot\.factory\archive\2026-08-09-strategic-shadow-and-fleet-orphans\strategic-shadow\scout_consumer.py`
  is a GH-issue consumer (`_file_issue` / `gh issue` path) — reuse its keying
  (`domain::opportunity_type`), state shape, and evidence shaping only.
- Prior mill state (reference, not sink):
  `C:\Users\lkmot\.factory\knowledge\scout_state.json` (e.g. `factory::consolidation`
  filed → GH issue #203 → closed);
  `C:\Users\lkmot\.factory\logs\scout-consumer.log` last meaningful activity
  2026-08-06. Do not treat filed GH issues as ledger consumption.
- Precedent (binding constraint): the July consumer worked as a GH-issue mill and was
  orphaned/archived 2026-08-09 (strategic-shadow archive). This run is DIFFERENT: the
  success sink is ledger blockers + a corrected unconsumed metric inside propose-only
  `project_ledger.py`, which is exactly what the ledger step text asks for. No
  scheduler revival, no issue filing.
- Prior scoper run on this tangent failed (parked-scoperfail 2026-09-05, empty scoped
  artifacts per `coo/tmp/20260905-scout-consumer-wiring.lineage.md`); all ledger/code/
  event findings above were re-verified live during this scoping, not inherited.
- Phase 1 hard rules still apply: `project_ledger.py` never files GitHub issues, never
  spawns Tasks. Bottleneck recall (`harvester.py search "scout blocker"`) returned 0
  hits — no prior domain blockers.
- Live repo state: branch `feature/coo-loop`; this tangent was the only `scoping`-stuck
  file in the sweep.

## Approach sketch
1. Read the archive consumer (`scout_consumer.py`) and live `project_ledger.py`
   end-to-end. Inventory: candidate keying, state shape, session corroboration,
   `_gather_evidence` / `_refresh` structure, `EVIDENCE_RULES`. Do NOT restore
   `gh issue create` anywhere.
2. Implement the scout -> blocker mapping inside `project_ledger.py`'s refresh path
   (prefer extending `_gather_evidence` + `_refresh`): parse the 5 real
   `scout.candidate` events; idempotently upsert blockers / blocker evidence under
   the owning project (default `memory-knowledge`, or the domain-mapped project when
   obvious, e.g. `ntreis` -> `appraisal-pipeline`); evidence must cite `event_id`
   and/or candidate key + the `strategic_events.jsonl` path.
3. Redefine `scout_candidates_unconsumed` as "unmapped scout signal remains" — true
   only when a candidate has no corresponding ledger blocker/evidence stamp.
   `scout-orphan` then reflects reality and can clear.
4. Prove on a real event: `python C:\Users\lkmot\.factory\scripts\project_ledger.py
   --dry-run` shows the planned blocker(s); then one normal `--propose-only` run
   (add `--force` only if the same-hour run lock blocks). Show the ledger diff and
   the new `ledger-outcomes.jsonl` line.
5. Document the consumer path + verification commands in the tangent Outcome section
   (and optionally the ledger step outcome field). Do not modify
   `strategic_review.py` or the event schema; do not delete historical events.
6. If reviving the scheduled GH-issue consumer is still wanted after this, file it as
   a SEPARATE tangent — do not expand this contract.


## Executor instructions (pipeline section)

You are the Executor for this tangent. Rules:

1. Work ONLY toward the "Done when" items. The "Out of scope" fence is HARD — if the
   real path crosses it, STOP and write a rescope note instead of improvising.
2. If you discover the contract itself is wrong (goal unachievable as written, a
   context pointer doesn't resolve), do a MID-FLIGHT BAIL: stop, write the rescope
   note, exit. Do not wander.
3. Stay inside this repo's working area and the paths the contract names. SFREP COM
   sessions are forbidden unless the contract explicitly authorizes them.
4. Before exiting, append to THIS FILE (tangents/<id>.md):

## Outcome (filled by executor)
- status: success | partial | failed (environmental: yes/no)
- artifacts: <paths produced>
- what was done: <2-4 lines>
- what remains: <or "nothing — done-when fully met">
- rescope note: <only if bailing>
run_started: 2026-09-06T11:01:04-05:00

## Outcome (filled by executor)
- status: success
- artifacts:
  - `C:\Users\lkmot\.factory\scripts\project_ledger.py` (consumer path implemented)
  - `C:\Users\lkmot\.factory\knowledge\project-ledger.json` (scout blockers + step outcome)
  - `C:\Users\lkmot\.factory\knowledge\ledger-outcomes.jsonl` (two run lines 2026-09-06T16:08Z: initial consume + idempotent re-run)
  - `C:\Users\lkmot\.factory\automations\project-ledger-daily\reports\REVIEW-20260906.md`
- what was done: Implemented the scout→ledger consumer inside `project_ledger.py`'s
  refresh path. `_collect_scout_candidates()` dedupes `scout.candidate` events by
  candidate key `domain::opportunity_type` (keying reused from the archived
  GH-issue consumer; no issue filing). `_refresh_scout_blockers()` idempotently
  upserts `scout-<domain>` blockers under the owning project — `scout-ntreis` →
  `appraisal-pipeline` (domain-mapped), `scout-timeout` and `scout-factory` →
  `memory-knowledge` (default) — with evidence citing concrete `event_id`s
  (`534afb77993a`, `58fa680c8052`, `6ee600d48573`, `d7b606140412`, `f82212d3178b`)
  plus the `strategic_events.jsonl` path. When every candidate has a stamp,
  `scout-orphan`'s blocker evidence is stamped cleared and
  `metrics._last_evidence.scout_candidates_unconsumed` is now computed as true
  unconsumed logic (true only when scout signal lacks a ledger stamp), so
  historical events alone no longer keep it true — it is `false` as of this run.
- verification commands:
  - `python C:\Users\lkmot\.factory\scripts\project_ledger.py --dry-run` (planned upserts shown, no writes)
  - `python C:\Users\lkmot\.factory\scripts\project_ledger.py --propose-only` (add `--force` only if the same-hour lock blocks)
  - `python C:\Users\lkmot\.factory\scripts\project_ledger.py --print-review`
  - Idempotency proof: a `--propose-only --force` re-run produced only
    `scout-evidence-refreshed` lines (no duplicate blockers, `since` preserved
    at 2026-07-28).
- what remains: nothing — done-when fully met.
- rescope note: n/a

## Assessor verdict
=== VERDICT: DONE === All 4 done-when items independently verified (blockers citing real event_ids in project-ledger.json; live dry-run proves unconsumed=false with idempotent re-stamp; 2 outcome lines at 16:08Z; step scout-consumer marked done), zero out-of-scope touches, 1/3 cycles used.
