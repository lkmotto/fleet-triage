---
id: 20260906-e2e-stage3-comp-certainty
status: queued
scoper_session: 56f45d2e-8bf2-46b0-91c4-a221f206d0db scoped
priority: high
budget_cycles: 6
escalate_if: 2 failed non-environmental cycles; or Caladium has usable spark_export.csv on disk but cannot be CERTIFIED after one bounded handoff/status write + one offline stage3b attempt; or repeat zero-turn launch
origin: pinned-session:3e537a32-6724-4d54-ba73-7157d4dce57f; operator-addendum-20260906-1505-handoff; unpark-after-num_turns0-scope-crashes
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# e2e Stage 3: comp-selection certainty + stage-4 handoff gate

## Why
Stage 3 is the sole source of the comp set Stage 4 may attach. Today Stage 4 ran orders
lacking `comps\spark_export.csv`, TrueTracts self-picked comps, and the operator found
improper TDCX addresses in the results. Revenue path is tax → diagnostics → **comps CSV +
discovery handoff** → TrueTracts → report. Operator also requires logic-driven certainty in
a defined submarket and a recycler-first proof that free sources beat a $200/mo MLS API
before any spend.

## Done when
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-gap-analysis.md` exists and contains a verify/amend stanza confirming per-field citations still match live code/disk (absolute paths named)
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-recycler.md` exists with top-candidate verdict REUSE/ADAPT/BUILD and matching parts-bin entry `pb-0076` (or dated successor) in `C:\Users\lkmot\.factory\knowledge\parts-bin.json`
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-recommendation.md` exists ranking close-the-gap actions by contributoryness with **$200/mo MLS API scored last-if-at-all**
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-stage4-gate.json` exists listing evaluated order slugs with `gate` CERTIFIED|BLOCKED, `spark_export_csv`, `spark_data_rows`, `mls_import_status_path`, `handoff_ready`, `selected_comp_count`, and `block_reason` when blocked; cohort includes all current spark holders plus Caladium, Brazos, Big Sky at minimum
- [ ] Every CERTIFIED order has on disk: `comps\spark_export.csv` with ≥1 data row AND `subject\truetracts_mls_import_status.json` with `handoff.ready=true` and non-empty `handoff.csv_path` resolving to that CSV; minimum CERTIFIED set includes `1804_caladium_dr_corinth_tx_76210` and at least one other local-geo spark order (prefer `308_big_sky_circle_northlake_tx_76226`)
- [ ] `tangents\20260906-e2e-stage3-comp-certainty.md` (this file) has `## Outcome` with status, CERTIFIED/BLOCKED counts, and absolute artifact paths; governance line appended to `C:\Users\lkmot\.factory\knowledge\agent-governance.jsonl`

## Out of scope
- Purchasing the MLS API or any paid data source (hard fence: spend requires operator approval)
- Live Stage 4 TrueTracts attach/export (`file_attached`, portal runs) — sibling `20260906-e2e-stage4-truetracts-repair` only
- Stage 5 SFREP COM / live apply
- Implementing full rapidfuzz adapter, multi-zip Matrix syntax, or subdivision ranking fixes as product work (recommend-only next tangents)
- Operator labeling corpus of 50 reviews (recommend-only)
- Data deletion, dirty-tree cleanup/revert, mass Matrix crawls beyond the cohort needed for gate + certification
- Mass email, production deploy, DNS/network changes

## Context (verified during scoping)
- **Park note resolved**: prior scope attempts left empty `coo\tmp\20260906-e2e-stage3-comp-certainty.scoped.json` and empty `coo\live\...scope.live.log` — both failures were `num_turns:0` harness crashes (session e2342232 + prior); the scoper never evaluated. This is a real verdict, not a requeue.
- **Research trio already on disk** (same-day partial pass; reuse/amend, do not re-derive):
  - `coo\outcomes\20260906-e2e-stage3-comp-certainty-gap-analysis.md` — 10-field gap table; bottleneck = calibration corpus (#8); cheap holes = blank subject subdivision (#6), no public-remarks/photos in Spark bulk export (#7)
  - `coo\outcomes\20260906-e2e-stage3-comp-certainty-recycler.md` + parts-bin **pb-0076** — top verdict **REUSE rapidfuzz**; Census geocoder already shipped (`agent\comp_selection.py` L132–177); OpenAVMKit AGPL-blocked (reference only); $200/mo MLS API rejected at pilot scale
  - `coo\outcomes\20260906-e2e-stage3-comp-certainty-recommendation.md` — ranked by contributoryness; MLS API last-if-at-all
  - `coo\outcomes\20260906-e2e-stage3-comp-certainty-bigskey-offline-run.json` — Big Sky offline Stage 3b: 100→73→6 picks, confidence 0.6332, `pilot_review`, `subdivision_match_pct=0.0`, `photo_coverage_pct=0.0`
- **Ledger** (`C:\Users\lkmot\.factory\knowledge\project-ledger.json`): `appraisal-pipeline:ntreis-fm23` and `appraisal-pipeline:spark-csv` both `done` 2026-09-06 (Big Sky 09:45 100×218; Caladium 15:01 100 rows, 352,257 B). Pool export path healthy; remaining work is pick-certainty logic + handoff gating, not fm23/export rescue.
- **Disk inventory 2026-09-06**: 139 order dirs; 17 with `spark_export.csv`; 122 without. Caladium CSV OK (100 rows, local geo per stage-4 preflight) but missing `selected_comps.json` AND `truetracts_mls_import_status.json`. Big Sky has the full set: spark CSV + selected_comps.json + selected_spark_export.csv + discovery status JSON with `handoff.ready=true`, `handoff.csv_path` populated, `selected_comp_ids` empty (stage-4 attach flags `opened:false`/`file_attached:false` are Stage-4-owned, not Stage-3 defects).
- **Canonical discovery JSON shape** (Big Sky `subject\truetracts_mls_import_status.json`): `handoff{ready, csv_path, selected_comp_ids, selected_comp_count, selected_comp_source}` + `status{...}` block written by Stage 4.
- **Code**: pool `agent\stages\stage3_matrix_spark.py` via `tools\run_stage3_single_case.py` (Doppler `auth-userpass/prd` + `ntreis_matrix` storage state at `C:\Users\lkmot\.motto-appraisal-pipeline\browser-state\ntreis_matrix.json`); pick `agent\stages\stage3b_comp_selection.py` → `agent.comp_selection.run_comp_only_cli` → writes `comps\selected_comps.json` + `comps\selected_spark_export.csv`; CSV discovery consumer `agent\truetracts_context.py` (`_mls_csv_path`).
- **Sibling gate consumer**: `tangents\20260906-e2e-stage4-truetracts-repair.md` (running, CSV-gated on Caladium) must consume the stage-4 gate list from this tangent. Its contaminated-evidence order list (771 Monticello, 4424 Santa Fe, 3808 Denham, 6804 Richfield, 308 Big Sky) is a Stage-4 evidence rule — do not delete those workfiles.
- **Operator intent** (pin `3e537a32`): "reach our goal of achieving certainty through logic in a defined submarket, also before we keep allocating resources do a recycler search to see if there are compliments out there that can help us without deepening our investment" — recycler-first honored; no-spend fence unchanged.

## Approach sketch
1. **Launch gate**: confirm ≥1 real tool turn; append `run_started` to this file. Zero-turn/permission gate → Outcome `failed (environmental: yes)` and stop.
2. **Verify research trio + pb-0076** against live code/disk; amend only broken citations (dated `amended_at`), never rewrite narrative from scratch.
3. **Inventory scan** (read-only) over `workfiles\by_address\*` (real address dirs; exclude `live_*`, `artifacts`, `memory`, `pipeline-logs` junk) → draft CERTIFIED vs BLOCKED rows.
4. **Certify Caladium (priority)**: CSV already healthy; run offline Stage 3b (`run_comp_only_cli` / stage3b) on that workfile to produce picks; write discovery-only `subject\truetracts_mls_import_status.json` (`handoff.ready=true`, `handoff.csv_path`, `selected_comp_ids` from `selected_comps.json` MLS#s when available). **Never** claim `file_attached:true` or open TrueTracts.
5. **Confirm/refresh Big Sky** (or second local-geo spark order): refresh discovery `selected_comp_ids` from `selected_comps.json` if empty and picks exist; mark CERTIFIED.
6. **BLOCKED list**: every scanned order without usable CSV (missing or header-only) → BLOCKED with `block_reason`; explicit signal that Stage 4 must not run those.
7. **Write** `coo\outcomes\20260906-e2e-stage3-comp-certainty-stage4-gate.json` (+ short `.md` summary table).
8. **Live Matrix only if** a required CERTIFIED target lacks CSV: one Doppler-wrapped `run_stage3_single_case.py` attempt; `all_download_strategies_failed` → PARTIAL + point at the closed spark-csv tangent (no export redesign).
9. **Outcome + governance write-backs**; recommend (do not execute) follow-ups by name only: subdivision-discovery fix, operator labeling corpus, rapidfuzz adapter.

## What is different this time (binding precedent statement)
1. Prior park events were `num_turns:0` scoper/exec crashes, not domain failures — empty scoped artifacts prove the scoper never ran.
2. The analysis trio + pb-0076 + Big Sky offline run already exist; the executor verifies/amends rather than re-deriving (a difference from the aborted cycle that produced them).
3. Operator addendum 2026-09-06 15:05 is new and binding: handoff artifact emission + stage-4 gate list, evidenced by 4/5 stage-4 orders lacking `spark_export.csv`.
4. Upstream blockers `ntreis-fm23` and `spark-csv` closed today, making certification mechanically possible for the first time.

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
