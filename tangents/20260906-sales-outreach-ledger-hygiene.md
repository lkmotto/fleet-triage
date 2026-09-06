---
id: 20260906-sales-outreach-ledger-hygiene
status: approved
priority: medium
budget_cycles: 2
escalate_if: 2 failed cycles OR JSON parse failure after edit OR diff shows unintended keys/projects/workstreams changed
origin: coo-scoper replacement stub (spawned when 20260905-sdr-9800-recovery closed UNSCOPABLE)
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# Close stale sales-outreach sdr-9800 blocker as retired (K1)

## Why
Core project `sales-outreach` still shows blocker `sdr-9800` ("needs Docker deploy") and `workstream-registry.json` `sales_emails` is still `partially_broken` on the same framing. Live evidence (kill-list K1, GH archive, workspace archive, unscopable recovery verdict) proves the stack is retired, not broken. Stale recover wording poisons COO dispatch on a core-tier project. This tangent corrects the record only.

## Done when
- [x] `project-ledger.json`: step `sales-outreach:sdr-9800` flipped to `done` with confirm-and-close wording; `outcome` cites kill-list K1 (`motto-sales-engine/docs/kill-list.md`), GH repo archived (2026-08-19), workspace archive 2026-09-01, UNSCOPABLE verdict, engine supersession; blocker `sdr-9800` removed from `blockers` array; `completed_at` and top-level `updated` set to edit time.
- [x] `workstream-registry.json`: `sales_emails` no longer claims ":9800 dead (needs Docker deploy)"; blockers record retirement per K1 + cold-email send lock (2a) + K12 deferral to `ms01-reverification`; `notes` added; `last_checked` 2026-09-06; status uses existing vocab (`partial`).
- [x] `decisions.jsonl`: one appended single-line JSON entry recording the applied retirement with artifact paths (line 57, 2026-09-06T20:17:10Z); no historical lines rewritten.
- [x] All three files parse; recursive diff vs `.bak` (`20260906T201233Z`) shows changes only in the named entries; line-ending deltas exact (ledger −2 CRLF, registry +1 LF); no BOM.

## Out of scope
- Any email send (cold/mass) — safety 2a.
- Docker start/rebuild/deploy of :9800 or `ghcr.io/lkmotto/motto-sdr-agent` — production-deploy fence; contradicts K1.
- ms01 repair/SSH/n8n workflow deactivate-export (K12) — owned by `ms01-reverification`.
- GH archive/unarchive Tier-B actions; motto-sales-engine code changes; credential/prospect data changes.
- Clearing the stale `manyreach-auth` ledger blocker (separate hygiene).
- Editing `infrastructure_health` image HOLD line.
- Rewriting the full `sales_emails` component map (follow-up only).

## Context (verified during scoping)
- Ledger/registry live state matched the stub exactly on 2026-09-06 (blocker since 2026-07-15; step `proposed`; sibling steps `manyreach-auth`/`manyreach-refresh-cadence` done).
- `decisions.jsonl` line ~51 recorded scoping intent only — files were unedited before this contract ran.
- Precedent: `20260905-sdr-9800-recovery` closed UNSCOPABLE (hygiene ≠ recover); `20260905-tangents-ledger-hygiene` sets the backup-first/narrow-rewrite pattern (DONE/PASS).
- Evidence paths verified: kill-list K1 + execution record, reconciliation 2026-09-01 (163 entries, zero orphans), unscopable spec, engine context pack, archive tree `factory-context/archive/sales-stack-2026-09-01/motto-sdr-agent`, old `C:\Users\lkmot\motto-sdr-agent` absent.
- Ledger step vocabulary: `done` | `proposed` | `resolved-pending-verify`; blockers have no closed flag — removal over schema invention. WSL unavailable, so `tangent-history.sh` lineage was reconstructed from stubs/decisions.

## Approach sketch
1. Timestamped raw-byte `.bak` copies beside both JSON files.
2. Surgical raw-text segment replacements (unique-match asserted before write; CRLF/LF preserved).
3. Append one decisions.jsonl line (UTF-8 no BOM).
4. Built-in parse + narrow-diff verification vs `.bak`; fix-forward on any caught defect; restore from `.bak` on unresolvable failure.
5. Executor Outcome section on the tangent stub; proof JSON in `coo/tmp/`.

## Outcome (filled by executor)
- status: success
- artifacts: both `.20260906T201233Z.bak` backups; edited `project-ledger.json` / `workstream-registry.json` / `decisions.jsonl`; `coo/tmp/20260906-sales-outreach-ledger-hygiene.proof.json` (34/34 PASS); `coo/tmp/...apply.py` + `.fixverify.py`; governance record in `agent-governance.jsonl`
- what was done: step closed as retired (K1), blocker removed, registry rewritten to retirement framing, decisions line appended, all verified by deep diff + parse + newline accounting
- what remains: nothing — done-when fully met; adjacent items (manyreach-auth blocker, image HOLD line, K12) fenced to their own tangents
- rescope note: n/a — one in-flight trailing-comma defect caught by built-in parse check and fixed before verification completed


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
