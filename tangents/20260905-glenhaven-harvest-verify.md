---
id: 20260905-glenhaven-harvest-verify
status: running
priority: medium
budget_cycles: 2
escalate_if: 1 failed cycle
origin: autonudge-carried-item (20260905T090000Z report)
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# Verify Glenhaven export gaps (garage $/space + boundary)

## Why
Stage 4 succeeded on the 09-05 retry (tangent 20260905T091000Z-...-sfrep-retry = SUCCESS) and order 2010 Glenhaven St, Arlington, TX 76010 is otherwise sfrep-complete, but the 09-05 09:00Z cycle flagged "garage $/space not present on export page" and "boundary reading incomplete — minor, verify manually." An appraiser delivering this workfile needs an artifact-backed READY/NOT READY call before use. This is a delivery-readiness gate on a revenue workfile, not a code task.

## Done when
- [ ] Report exists at `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\2010_glenhaven_street_arlington_tx_76010\metadata\glenhaven_export_gap_verification.md`
- [ ] Report includes explicit verdicts: garage $/space **PASS/FAIL**, boundary reading **PASS/FAIL**, core export package **PASS/FAIL**, overall **READY / NOT READY** for appraiser use
- [ ] Report cites the early-vs-final inconsistency (`subject\truetracts_workflow_status.json` stale gated-page flags vs final `truetracts_export_harvest.json`) with file paths
- [ ] Report states whether a follow-on harvest-bug tangent is warranted (**yes/no** + one-line reason)
- [ ] No Stage-4 / SFREP / TrueTracts browser or COM session was opened for this work

## Out of scope
- Re-running any SFREP COM or TrueTracts Stage-4 workflow (hard fence)
- Editing `truetracts_template_harvest.py` or stage4 harvest wiring — recommend-only if a real gap remains
- Fixing `workflow_status.json` lag or the TDCX subject-block extractor (`tdcx_subject_block_absent`)
- Any other order's workfiles
- Delivery, bid submit, mass email, DNS/network changes, data deletion, production deploy (all hard fences)

## Context (verified during scoping)
- **Machine:** Legion (hostname confirmed).
- **Stub Desktop path is wrong/empty.** Real workfile root: `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\2010_glenhaven_street_arlington_tx_76010\` (44 files inventoried).
- **Tangents** (`~\.factory\knowledge\tangents.json`): 09-05 sfrep-retry SUCCESS (Report.tdcx + workfiles.zip + harvest/verification JSONs); 09-03 sfrep FAILED `create_session_modal_timeout` (different problem, already resolved by retry). **No prior harvest-verify tangent** — different this time: static artifact verification only, no live session.
- **Flag source:** `~\.factory\automations\autonudge-loop\reports\20260905T090000Z-summary.md` (outcome section lists both flags verbatim).
- **Key inconsistency verified on disk:** `subject\truetracts_workflow_status.json` still holds early gated-page harvest state (`template_harvest.ok: false`, `text_chars: 229`, garage/boundary flags, empty boundary streets, SS gate notice), while final `subject\truetracts_export_harvest.json` shows `garage_rate: "$6,000"`, `boundary.ok: true` (W=E Mitchell St, N=E Abram St, E=Swatson Rd, S=E Park Row Dr), `flags: []`. `truetracts_comment_templates.md` carries the garage $6,000 language and the four-street boundary line; `truetracts_boundary_map_{0,1,2}.jpg` + crops exist; `truetracts_boundary_recovery.json` shows `gate_cleared: true` with both downloads. Matches the design note in `tools\_exploration\truetracts_findings.md`: gated harvest degrades by design; workflow rerun overwrites harvest artifacts (workflow_status can lag).
- **Known residual:** `subject\truetracts_export_verification.json` has `checked: false`, flag `tdcx_subject_block_absent`, `foreign_hits: {}` — non-fatal by design; note it, do not repair it here.
- **Decision precedent:** `decisions.jsonl` 2026-09-01 wired template harvest into every Stage 4 run, non-fatal, missing figures become verify markers. Project ledger has no Glenhaven entry.
- Parked draft spec from a failed scoper session exists at `~\.factory\specs\2026-09-05-contract-verify-glenhaven-export-gaps-garage-space-boundary.md`; this contract supersedes it.

## Approach sketch
1. Use the **pipeline** workfile root only (never Desktop Motto-Workfiles).
2. Diff early vs final: `subject\truetracts_workflow_status.json` → `Export.export.template_harvest` (early flags) against `truetracts_export_harvest.json`, `truetracts_comment_templates.md`, and boundary map JPGs (final state).
3. Garage check (offline): confirm final JSON `garage_rate` and template text for `$6,000` / garage-space adjustment language; treat the early workflow_status flag as stale if finals are populated.
4. Boundary check (offline): confirm `boundary.ok`, four edge streets non-empty, map/crop files exist, templates' boundary section has no `[verify on map]` markers. Spot-check map JPG labels only if needed (local/Qwen); no live TrueTracts session.
5. Package integrity: confirm `Report.tdcx` (~13.6 MB) + `workfiles.zip` (~8.0 MB) exist and non-trivial; optionally list zip members; record the TDCX subject-block absence as known residual only.
6. Write the single markdown report at the Done-when path with PASS/FAIL verdicts, READY/NOT READY, the early-vs-final citation, and the harvest-bug-tangent yes/no.
7. If and only if the **final** harvest still lacks garage/boundary on re-read, recommend a separate harvest-logic tangent; do not fix code here.


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
run_started: 2026-09-05T19:24:51-05:00
