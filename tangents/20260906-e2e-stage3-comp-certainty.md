---
id: 20260906-e2e-stage3-comp-certainty
status: assess
priority: high
budget_cycles: 6
escalate_if: 2 failed non-environmental cycles; or Caladium has usable spark_export.csv on disk but cannot be CERTIFIED after one bounded handoff/status write + one offline stage3b attempt; or repeat zero-turn launch
origin: pinned-session:3e537a32-6724-4d54-ba73-7157d4dce57f; operator-addendum-20260906-1505-handoff; unpark-after-num_turns0-scope-crashes
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# e2e Stage 3: comp-selection certainty + stage-4 handoff gate

## Why
Stage 3 is the sole source of the comp set Stage 4 may attach. Today Stage 4 ran orders lacking `comps\spark_export.csv`, TrueTracts self-picked comps, and the operator found improper TDCX addresses. Revenue path is tax → diagnostics → **comps CSV + discovery handoff** → TrueTracts → report. Operator also requires logic-driven certainty in a defined submarket and recycler-first proof that free sources beat a $200/mo MLS API before any spend.

## Done when
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-gap-analysis.md` exists and contains a dated `## Verify/Amend` stanza confirming per-field citations still match live code/disk (absolute paths named; amend only broken citations)
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-recycler.md` exists with top-candidate verdict REUSE/ADAPT/BUILD and matching parts-bin entry `pb-0076` (or dated successor) in `C:\Users\lkmot\.factory\knowledge\parts-bin.json`
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-recommendation.md` exists ranking close-the-gap actions by contributoryness with **$200/mo MLS API scored last-if-at-all**
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-stage4-gate.json` exists listing evaluated order slugs with fields `gate` (CERTIFIED|BLOCKED), `spark_export_csv`, `spark_data_rows`, `mls_import_status_path`, `handoff_ready`, `selected_comp_count`, and `block_reason` when blocked; cohort includes **all current spark holders** plus explicit rows for Caladium, Brazos, Big Sky at minimum; companion short summary allowed at `coo\outcomes\20260906-e2e-stage3-comp-certainty-stage4-gate.md`
- [ ] Every CERTIFIED order has on disk: `comps\spark_export.csv` with ≥1 data row AND `subject\truetracts_mls_import_status.json` with `handoff.ready=true` and non-empty `handoff.csv_path` resolving to that CSV; minimum CERTIFIED set includes `1804_caladium_dr_corinth_tx_76210` and at least one other local-geo spark order (prefer `308_big_sky_circle_northlake_tx_76226`)
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\tangents\20260906-e2e-stage3-comp-certainty.md` has `## Outcome` with status, CERTIFIED/BLOCKED counts, and absolute artifact paths; governance line appended to `C:\Users\lkmot\.factory\knowledge\agent-governance.jsonl`

## Out of scope
- Purchasing the MLS API or any paid data source (hard fence: spend requires operator approval)
- Live Stage 4 TrueTracts attach/export (`file_attached`, portal runs) — sibling `20260906-e2e-stage4-truetracts-repair` only
- Stage 5 SFREP COM / live apply
- Implementing full rapidfuzz adapter, multi-zip Matrix syntax, or subdivision ranking fixes as product work (recommend-only next tangents)
- Operator labeling corpus of 50 reviews (recommend-only)
- Data deletion, dirty-tree cleanup/revert, mass Matrix crawls beyond the cohort needed for gate + certification
- Mass email, production deploy, DNS/network changes
- Deleting or "cleaning" contaminated Stage-4 evidence workfiles (771 Monticello, 4424 Santa Fe, 3808 Denham, 6804 Richfield, 308 Big Sky)

## Context (verified during scoping)
### Machine / repos
- Host: Legion. Pipeline repo: `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline`. COO repo: `C:\Users\lkmot\factory-context\code\fleet-triage` (branch `feature/coo-loop`).
- KB notes: no dedicated `spark`/`ntreis` credential rows; auth pattern is Doppler `auth-userpass`/`prd` + browser state files (same as closed spark-csv tangent).

### Park / harness precedent (binding)
- Prior scope attempts left empty artifacts proving scoper never evaluated:
  - `coo\tmp\20260906-e2e-stage3-comp-certainty.scoped.json` (0 B)
  - `coo\live\20260906-e2e-stage3-comp-certainty.scope.live.log` (0 B)
- Failures were `num_turns:0` harness crashes, not domain failures. Executor must confirm ≥1 real tool turn; zero-turn → Outcome `failed (environmental: yes)` and stop.
- Related closed precedent: `tangents\20260905-spark-csv-export.md` SUCCESS 2026-09-06 (Caladium live export 100×218). Assessor DONE. Ledger `appraisal-pipeline:spark-csv` and `appraisal-pipeline:ntreis-fm23` both `done` 2026-09-06.

### Research trio already on disk (verify/amend only — do not re-derive)
- `coo\outcomes\20260906-e2e-stage3-comp-certainty-gap-analysis.md` — 10-field gap table; bottleneck = calibration corpus (#8); cheap holes = blank subject subdivision (#6), no public-remarks/photos in Spark bulk export (#7). Note: memo cites `bigsky-offline-run.json` but file on disk is `...-bigskey-offline-run.json` (typo filename) — amend citation if verifying.
- `coo\outcomes\20260906-e2e-stage3-comp-certainty-recycler.md` + parts-bin **pb-0076** (`C:\Users\lkmot\.factory\knowledge\parts-bin.json`, date 2026-09-06T14:59:45) — top verdict **REUSE rapidfuzz**; Census geocoder already shipped; OpenAVMKit AGPL-blocked (reference only); $200/mo MLS API rejected at pilot scale. Prior **pb-0065** 2026-08-29.
- `coo\outcomes\20260906-e2e-stage3-comp-certainty-recommendation.md` — ranked by contributoryness; MLS API last-if-at-all.
- `coo\outcomes\20260906-e2e-stage3-comp-certainty-bigskey-offline-run.json` — Big Sky offline Stage 3b snapshot: 100→73→6 picks, confidence 0.6332, `status: pilot_review`, `subdivision_match_pct=0.0`, `photo_coverage_pct=0.0`.

### Disk inventory re-verified 2026-09-06 (scope session)
Workfile root: `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address`
- **17 spark holders** (all must appear in gate JSON):
  `11452_snyder_dr_frisco_tx_75035`, `1302_rivercrest_blvd_allen_tx_75002`, `1325_heidi_dr_plano_tx_75025`, `1433_thistlewood_ln_grapevine_tx_76051`, `15060_cactus_blossom_blvd_fort_worth_tx_76052`, `1804_caladium_dr_corinth_tx_76210`, `1818_lake_tawakoni_dr_allen_tx_75002`, `2000_brazos_ct_westlake_tx_76262`, `2010_glenhaven_street_arlington_tx_76010`, `2208_arbor_creek_dr_carrollton_tx_75010`, `308_big_sky_circle_northlake_tx_76226`, `3841_parkmont_dr_plano_tx_75023`, `5205_brookside_dr_argyle_tx_76226`, `6037_sundown_dr_watauga_tx_76148`, `6413_crator_dr_mckinney_tx_75070`, `6505_victoria_ave_north_richland_hills_tx_76180`, `801_lark_dr_aubrey_tx_76227`
- **Caladium** `1804_caladium_dr_corinth_tx_76210`: `comps\spark_export.csv` OK (352,257 B, 101 lines = header+100 rows, mtime 15:01:11). **MISS** `selected_comps.json`, `selected_spark_export.csv`, `truetracts_mls_import_status.json`. Subject file ready: `tools\_tmp_subject_caladium.json`.
- **Big Sky** `308_big_sky_circle_northlake_tx_76226`: spark CSV OK (411,523 B, 101 lines); `selected_comps.json` OK (50,600 B, 14:56:27); `selected_spark_export.csv` OK (7 lines); geocode cache OK; `subject\truetracts_mls_import_status.json` exists with:
  ```json
  "handoff": {"ready": true, "csv_path": "workfiles\\by_address\\308_big_sky_circle_northlake_tx_76226\\comps\\spark_export.csv", "selected_comp_ids": [], "selected_comp_count": 0, "selected_comp_source": ""}
  ```
  Stage-4 flags `opened:false` / `file_attached:false` are Stage-4-owned, not Stage-3 defects. CERTIFY path may refresh `handoff.selected_comp_ids` from `selected_comps.json` MLS#s when empty.
- **Brazos** `2000_brazos_ct_westlake_tx_76262`: spark CSV present (26 lines, older 2026-08-26, Houston-polluted per Stage-4 notes); has `truetracts_mls_import_status.json` — evaluate for gate; do not invent live Matrix re-export unless required for min CERTIFIED set (it is not required).
- Gate rule: missing or header-only CSV → `BLOCKED` with `block_reason`. Usable CSV alone is not CERTIFIED without discovery handoff JSON.

### Code entry points (pipeline repo)
- Pool export: `agent\stages\stage3_matrix_spark.py` via `tools\run_stage3_single_case.py` (Doppler `auth-userpass/prd`; NTREIS state `C:\Users\lkmot\.motto-appraisal-pipeline\browser-state\ntreis_matrix.json`).
- Pick / offline Stage 3b: `agent\stages\stage3b_comp_selection.py` → `agent.comp_selection.run_comp_only_cli(workfile_dir, subject=None)` → writes `comps\selected_comps.json` + `comps\selected_spark_export.csv`. `pilot_review` is SUCCESS for Stage 3b (operator review next by design).
- CSV discovery consumer: `agent\truetracts_context.py` — `_mls_csv_path`, `_extract_selected_comp_ids` (~L193, ~L304). Prefer reusing this shape for discovery-only status JSON writes.
- Canonical discovery JSON shape (match Big Sky): top-level `handoff{ready, csv_path, selected_comp_ids, selected_comp_count, selected_comp_source}` + optional `status{...}` (Stage 4 owns attach fields). **Never** set `file_attached:true` or open TrueTracts in this tangent.
- Calibration tool (recommend-only): `tools\calibrate_comp_weights.py`.

### Sibling consumer
- `tangents\20260906-e2e-stage4-truetracts-repair.md` is **running**, CSV-gated on Caladium. It must consume `stage4-gate.json` from this tangent. Contaminated Stage-4 evidence orders (list only, never delete): 771 Monticello, 4424 Santa Fe, 3808 Denham, 6804 Richfield, 308 Big Sky.
- Stage-4 preflight already recorded Caladium CSV GREEN (100 local rows, zip 76210) and missing picks → expects full-CSV attach fallback; this tangent's Caladium certification (Stage 3b + discovery handoff) improves that path but must not claim Stage-4 attach success.

### Operator intent
- Pin `3e537a32`: certainty through logic in a defined submarket; recycler-first before deepening investment. No-spend fence unchanged. Addendum 2026-09-06 15:05: handoff artifact emission + stage-4 gate list mandatory.

## Approach sketch
1. **Launch gate**: confirm ≥1 real tool turn; append `run_started` to `tangents\20260906-e2e-stage3-comp-certainty.md`. Zero-turn/permission gate → Outcome `failed (environmental: yes)` and stop.
2. **Verify research trio + pb-0076** against live code/disk; amend only broken citations with dated `amended_at` / `## Verify/Amend` stanza (fix the `bigsky` vs `bigskey` filename cite); never rewrite narratives from scratch.
3. **Inventory scan** (read-only) over real address dirs under `workfiles\by_address\*` (exclude `live_*`, `artifacts`, `memory`, `pipeline-logs`) → draft CERTIFIED vs BLOCKED rows for all 17 spark holders + non-holders needed for Brazos/Caladium/Big Sky explicit rows.
4. **Certify Caladium (priority)**: CSV already healthy; run **offline** Stage 3b only:
   - from pipeline repo: `python -c "from agent.comp_selection import run_comp_only_cli; ..."` or invoke `agent.stages.stage3b_comp_selection.run` with the Caladium workfile path;
   - require `comps\selected_comps.json` (+ prize CSV if produced);
   - write discovery-only `subject\truetracts_mls_import_status.json` with `handoff.ready=true`, `handoff.csv_path` pointing at the order-local spark CSV (absolute or repo-relative path that resolves), `selected_comp_ids` from picks when available;
   - **Never** claim `file_attached:true` or open TrueTracts / Stage 4 runners.
5. **Confirm/refresh Big Sky** (second local-geo CERTIFIED preferred): if picks exist and `handoff.selected_comp_ids` empty, refresh IDs from `selected_comps.json`; keep `handoff.ready=true`; mark CERTIFIED. Do not run Stage 4; do not delete contaminated Stage-4 evidence history on this order.
6. **BLOCKED list**: every scanned order without usable CSV (missing or header-only) → BLOCKED + `block_reason` (explicit Stage 4 must-not-run signal). Orders with CSV but without handoff remain non-CERTIFIED until handoff written (either CERTIFY via discovery write when in min set, or BLOCKED/`handoff_ready=false` with reason for non-min cohort — document rule in gate JSON `schema_notes`).
7. **Write** `coo\outcomes\20260906-e2e-stage3-comp-certainty-stage4-gate.json` (+ optional short `.md` summary table).
8. **Live Matrix only if** a required CERTIFIED target lacks CSV: one Doppler-wrapped `run_stage3_single_case.py` attempt. If `all_download_strategies_failed` → PARTIAL + point at closed `20260905-spark-csv-export` (no export redesign). Caladium already has CSV → live Matrix not required for success path.
9. **Outcome + governance write-backs** on the tangent file and `agent-governance.jsonl`. Recommend (do not execute) follow-ups by name only: subdivision-discovery fix, operator labeling corpus, rapidfuzz adapter.

## What is different this time (binding precedent statement)
1. Prior park events were `num_turns:0` scoper/exec crashes, not domain failures — empty scoped artifacts prove the scoper never ran domain work.
2. Analysis trio + pb-0076 + Big Sky offline run already exist; executor verifies/amends rather than re-deriving.
3. Operator addendum 2026-09-06 15:05 is binding: handoff emission + stage-4 gate list (4/5 Stage-4 orders lacked usable `spark_export.csv`).
4. Upstream blockers `ntreis-fm23` and `spark-csv` closed today; Caladium CSV is live on disk, making certification mechanically possible for the first time.
5. Sibling Stage 4 is mid-flight and already CSV-gated on Caladium; this contract's primary deliverable is the gate artifact + Caladium discovery handoff that Stage 4 can consume without Stage 3 inventing attach success.

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
run_started: 2026-09-06T15:35:40-05:00
