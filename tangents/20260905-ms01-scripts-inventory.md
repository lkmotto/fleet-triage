---
id: 20260905-ms01-scripts-inventory
status: done
validator_session: 2ad9e8d7-f60c-4444-bb46-06945bc4cd67 validating
assessor_session: cb4479f0-c0ed-416e-a214-e53a4a35ed18 assess
executor_session: 561dd6d8-ecb2-495a-badd-5b5880047452 running
priority: low
budget_cycles: 2
escalate_if: another zero-row/zero-turn execute cycle OR any non-inventory mutation of `code\ms01-*` files OR executor attempts harness (`coo-loop-v3.sh`/`v4.sh`) edits or ms01 SSH
origin: project-ledger infrastructure:ms01-scripts-inventory; RESCOPE cycle 4 after assess-3 ESCALATE (3× zero-work: cycle1 no --auto, cycle2 1200s timeout, cycle3 permission gate at 0 turns; sessions 561dd6d8, b1526404)
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# Inventory ms01-* scripts; map to workflows or mark archive-candidate (seed-frozen rescope)

## Why
Ledger blocker `ms01-scripts-sprawl` (since 2026-07-30): 65 `ms01*.{ps1,sh}` scripts (plus 7 PNGs) sit in flat `C:\Users\lkmot\factory-context\code\` from the 2026-07-15 Docker-Desktop→WSL docker-ce recovery and the 2026-07-30 Hyper-V/ISO experiments. ms01 has been native Proxmox since 2026-08-09 (decisions.jsonl). This inventory is the reversible classification feed for a later operator-approved cull (Minimalist Operations). No revenue path is unblocked by the inventory itself; it de-risks accidental reuse of dead Hyper-V paths and reduces infra cognitive load.

## Done when
- [ ] `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\ms01-scripts-inventory.md` exists containing: inventory date + source path; one row per script with `path`, `mtime`, `size_bytes`, redacted `purpose`, `mapped_workflow` (exact workflows.json id or `none`), `era` ∈ {docker-wsl-recovery, hyperv-iso, proxmox-adjacent, unknown}, `verdict` ∈ {keep, archive-candidate, unknown}; explicit non-script note for the 7 `ms01-*.png` ("ignore-as-script"); summary counts (total/keep/archive-candidate/unknown + by era); "Recommended follow-on tangents" (names only, no deletion); Completeness block (live recount equals row count, or documents permission-block and proves basename equality against the seed freeze of 65)
- [ ] Outcome block appended to `tangents/20260905-ms01-scripts-inventory.md` with counts matching the outcomes md exactly (`keep=N archive-candidate=N unknown=N total=65`)
- [ ] Mutation guard proven: zero changes to any `code\ms01-*` file. `code\` is NOT a git repo — proof is mtime evidence (post-run spot-check: no `ms01*` mtime after inventory start) plus executor turn/IO accounting, not `git status` on `code\`. Only acceptable writes: the outcomes md, the tangent Outcome block, optional `coo/tmp/*` scratch, COO live/tmp logs.

## Out of scope
- Deleting, moving, renaming, chmodding, or archiving any script or PNG (cull = separate operator-approved tangent)
- Any SSH/login or change on ms01 (192.168.1.120); never execute any `ms01-*` script
- Editing `workflows.json`, postmortems, or `project-ledger.json` (recommend only)
- Editing `coo-loop-v3.sh`/`coo-loop-v4.sh`, `COO_STAGE_TIMEOUT`, or `COO_EXECUTE_AUTO` (document env needs only; the fix is a separate operator/harness tangent)
- Inventorying `code\ms01-ider\` as the primary set (one-line appendix pointer at most)
- PNG/binary cleanup; implementing `offhost-backup` (open ledger blocker; flag `ms01-backup.sh` disposition only)
- Hard fences: production deploys, DNS/network changes, data deletion, mass email, anything requiring explicit operator approval

## Context (verified during scoping)
**Machine:** Legion, local paths only. **Scoper session could read `C:\Users\lkmot\factory-context\code\` under spec/auto-high — the executor historically could not.**

**Failure history (binding)**
- Cycle 1: executor launched without `--auto` → 0 turns (RELOOP).
- Cycle 2: 1200s stage timeout, 0-byte live log, no inventory rows (RESCOPE).
- Cycle 3 (rescope): both executor sessions (`561dd6d8`, `b1526404`) died `num_turns:0`, "insufficient permission to proceed. Re-run with --auto medium or --auto high" (`coo/tmp/20260905-ms01-scripts-inventory.exec.log`); outcome file ENOENT; no Outcome block. Assessor verdict 2026-09-06: ESCALATE/parked; grounds were the fenced harness fix.
- **Verified this session:** `coo-loop-v4.sh` do_execute runs `droid exec -o json --auto "$EXEC_AUTO"` with `EXEC_AUTO=${COO_EXECUTE_AUTO:-medium}` (line ~202). The bypass flag IS present; it does not unlock parent-directory reads for the executor. A fourth attempt that still requires parent-`code\` reads will fail identically.
- **What is different this time:** the contract embeds a scoper-verified freeze list (all 65 names + mtimes + sizes, headers read and token-redacted this session). The executor's happy path performs ZERO parent-`code\` reads: it materializes the inventory from the seed, runs at most one best-effort recount, and writes only inside `fleet-triage`. Budget capped at 2; escalation on repeat zero-work is expected, not a loop defect.

**Ledger** (`~\.factory\knowledge\project-ledger.json`): project `infrastructure` active; step `infrastructure:ms01-scripts-inventory` status proposed, autonomy queue, reversible true; blockers `ms01-scripts-sprawl` (this tangent) and `offhost-backup` (OOS).

**Workflows** (`~\.factory\knowledge\workflows.json`, exact ids): `workflow-uspto-mcp-capability-audit`, `workflow-headless-proxmox-rescue-bootstrap`, `workflow-proxmox-linux-first-guest-platform`, `workflow-linux-browser-runner-canary`, `workflow-sfrep-session-hygiene-and-delivery`, `workflow-ntreis-stage3-spark-export`. None of the 65 flat-dir scripts map cleanly to a workflow id: all predate Proxmox. Expect `mapped_workflow: none` for every row; do not force-map.

**Decisions/postmortems (era evidence, notes only):** 2026-07-15 docker-ce WSL recovery + backup/guard + Mission Control decisions; 2026-08-09 Proxmox VE 9 install + linux-first two-guest architecture + snapshot backups (supersedes the entire Hyper-V/ISO chain); Tailscale removed 2026-08; postmortems `ms01-proxmox-install-20260809.json`, `ms01-guest-platform-20260809.json`, `ms01-linux-browser-runner-20260809.json` (they document IDER/KVM work, not these scripts).

**Filesystem freeze (scoper recount 2026-09-06 = 65 scripts, 7 PNGs):**
- 19 `.sh` (2026-07-15 docker-wsl-recovery cluster): `ms01_bringup.sh`, `ms01_bringup2.sh`, `ms01_buildall.sh`, `ms01_check_pgdata.sh`, `ms01_container_defs.sh`, `ms01_explore.sh`, `ms01_explore2.sh`, `ms01_extract_pipeline.sh`, `ms01_mc_run.sh`, `ms01_migrate_vols.sh`, `ms01_read_srcs.sh`, `ms01_recon_pipeline.sh`, `ms01_sales_run.sh`, `ms01_sdrpull.sh`, `ms01_vols.sh`, `ms01-backup.sh`, `ms01-container-guard.sh`, `ms01-install-ops.sh`, `ms01-validate-ops.sh`
- 46 `.ps1` (2026-07-30 hyperv-iso cluster): `ms01-autounattend.ps1`, `ms01-bootwim.ps1`, `ms01-bootwim-v2.ps1`, `ms01-bridge-iso.ps1`, `ms01-build-iso.ps1`, `ms01-check.ps1`, `ms01-cleanup.ps1`, `ms01-clone-test.ps1`, `ms01-csharp-iso.ps1`, `ms01-detailed.ps1`, `ms01-final-rebuild.ps1`, `ms01-fix-boot.ps1`, `ms01-fix-iso.ps1`, `ms01-fix-template.ps1`, `ms01-inspect.ps1`, `ms01-iso-v3.ps1`, `ms01-iso9660.ps1`, `ms01-kb-list.ps1`, `ms01-kb-v2.ps1`, `ms01-mount-check.ps1`, `ms01-mount-fix.ps1`, `ms01-parallel.ps1`, `ms01-progress.ps1`, `ms01-quick.ps1`, `ms01-ready.ps1`, `ms01-rebuild.ps1`, `ms01-rebuild-v3.ps1`, `ms01-reset-password.ps1`, `ms01-schedule-setup.ps1`, `ms01-seal-clone.ps1`, `ms01-start.ps1`, `ms01-start-vm.ps1`, `ms01-status.ps1`, `ms01-stop-check.ps1`, `ms01-task-status.ps1`, `ms01-template.ps1`, `ms01-test-novhdx.ps1`, `ms01-test-original.ps1`, `ms01-test-rebuilt.ps1`, `ms01-validate-ops.ps1` is NOT present (only the 46 listed; see freeze below), `ms01-verify.ps1`, `ms01-verify-iso.ps1`, `ms01-vhdx-unattend.ps1`, `ms01-vms.ps1`, `ms01-vm-status.ps1`, `ms01-winpeshl.ps1`, `ms01-wmi-keyboard.ps1` — full 65-row machine freeze (name|mtime|size) captured in scoper transcript and in `coo/tmp/20260905-ms01-scripts-inventory.body.md` precedent; executor regenerates any missing cell from the recount or marks `unknown`.
- 7 PNGs (2026-08-08, AMT/KVM + IDER evidence, ignore-as-script): `ms01-debian-ider.png`, `ms01-hardware-kvm-awake.png`, `ms01-hardware-kvm-wide.png`, `ms01-hardware-kvm.png`, `ms01-kvm-after-cad.png`, `ms01-kvm-reboot.png`, `ms01-meshcommander.png`

**Era/verdict seed (apply as defaults; conservative deviations allowed with one-line justification per row):**
- era: 2026-07-15 `.sh` family → `docker-wsl-recovery`; 2026-07-30 `.ps1` Hyper-V/ISO/VHDX/WinPE/daemon-base family → `hyperv-iso`; nothing → `proxmox-adjacent`; unclassifiable → `unknown`.
- verdict keep (document-worthy, still-referenced ops patterns): `ms01-backup.sh` (nightly docker backup; generic DEST_ROOT), `ms01-container-guard.sh` (Telegram container-count guard), `ms01-install-ops.sh` (installer for the two above + systemd units), `ms01-validate-ops.sh` (guard self-test). Everything else → `archive-candidate` (use `unknown` only if a header is unreadable/uninformative after best effort).
- **Expected summary: total=65, keep=4, archive-candidate=61, unknown=0; era: docker-wsl-recovery=19, hyperv-iso=46, proxmox-adjacent=0.**
- Purpose lines: one line each from header comments or first meaningful commands. REDACT any token/secret references (e.g. `ms01-container-guard.sh` TELEGRAM_BOT_TOKEN → `[REDACTED]`).
- Sample purposes already verified: backup = "nightly docker volume+pg_dump backup, repointable DEST_ROOT"; guard = "Telegram alert when container count < EXPECTED"; `ms01_explore.sh` = "read-only block-device probe + mount of old docker disk"; rebuild family = "wipe/reinit daemon-base.vhdx from WS2025-eval.iso".

## Approach sketch
1. **Batch-first recount (single command, best-effort):** one `Get-ChildItem 'C:\Users\lkmot\factory-context\code' -File | ? Name -match '^ms01.*\.(ps1|sh)$' | Select Name,Length,LastWriteTime` producing a single listing. If permission-gated, note it and proceed with the frozen list — do not die here.
2. **Bulk purpose extract (single command):** loop that dumps the first ~30 lines of every script into ONE scratch file under `coo/tmp/` (allowed write), then classify offline from that blob. If blocked, reuse the seed purposes above. Never execute scripts; never open 65 individual tool turns.
3. **Write once:** `coo/outcomes/ms01-scripts-inventory.md` — summary counts first, per-script table (path, mtime, size_bytes, purpose, mapped_workflow=none unless a clear string match, era, verdict), PNG non-script note, "Recommended follow-on tangents" (e.g. `20260906-ms01-hyperv-iso-cull`, `20260906-ms01-docker-wsl-one-shot-cull`, each explicitly operator-approved deletion), Completeness check block.
4. **Prove the guards:** row count equals recount (or freeze count with documented permission-block); spot-check 5 random `code\ms01-*` mtimes unchanged; then append the Outcome block to this tangent with matching counts. Stop.


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
run_started: 2026-09-06T17:28:39-05:00

## Outcome (filled by executor)
- status: success
- artifacts: `coo/outcomes/ms01-scripts-inventory.md` (full 65-row inventory + PNG note + completeness block); scratch: `coo/tmp/20260905-ms01-scripts-inventory.freeze.txt`, `coo/tmp/20260905-ms01-scripts-inventory.headers.txt`
- what was done: Live recount succeeded this cycle (no permission gate): 72 `ms01*` files = 65 scripts (19 `.sh` + 46 `.ps1`) + 7 PNGs, exactly matching the seed freeze. Bulk header extract of all 65 into one scratch blob; classified offline per seed rules. Wrote the outcomes md in one shot: keep=4 archive-candidate=61 unknown=0 total=65; era docker-wsl-recovery=19 hyperv-iso=46 proxmox-adjacent=0; mapped_workflow=none for all rows (no match against any of the 6 workflows.json ids); 7 PNGs noted ignore-as-script; 3 follow-on cull tangents recommended (names only).
- what remains: nothing — done-when fully met. Mutation guard proven: post-run re-listing at 2026-09-06T17:36:34-05:00 shows all 72 files identical name|mtime|size to the pre-run freeze (Compare-Object empty; 5-file spot-check mtimes all 2026-07-15/07-30/08-08, none after inventory start 17:28:39). Executor wrote only the outcomes md, the scratch files, and this Outcome block. Counts in this block match the outcomes md exactly: keep=4 archive-candidate=61 unknown=0 total=65.
- rescope note: none

## Assessor verdict
=== VERDICT: DONE === All 3 done-when items independently verified: 65-row inventory matches live recount (72 files, newest mtime 2026-08-08), counts keep=4/archive=61/total=65 consistent across outcome artifacts, mutation guard proven by fresh mtime spot-check.

## Validator
=== VALIDATION: PASS === value:hygiene_only; score:3; all 3 done-when items independently re-proven (65/65 rows counted, keep=4/archive=61/unknown=0 in both artifacts, 72-file freeze diff=0, newest mtime 2026-08-08 predates run, zero fenced mutations); hygiene_only work that consumed 4 cycles due to 3 prior zero-work failures.
