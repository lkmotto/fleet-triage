---
id: 20260905-ms01-scripts-inventory
status: running
priority: low
budget_cycles: 2
escalate_if: 1 failed cycle OR any non-inventory mutation of code/ ms01-* files OR execute stage hits wall timeout with zero inventory rows written
origin: project-ledger proposed step (infrastructure:ms01-scripts-inventory); RESCOPE after cycle2 1200s timeout (b1966b9→49f16fc)
scoped_by: coo-scoper
scoped_at: 2026-09-05
---
# Inventory ms01-* scripts; map to workflows or mark archive-candidate

## Why
Infrastructure tier noise reduction. Flat `C:\Users\lkmot\factory-context\code\` holds **65** `ms01-*.{ps1,sh}` scripts (plus 7 screenshot PNGs) from the July 2026 Docker-Desktop→WSL docker-ce recovery and Hyper-V/ISO experiments. ms01 is now native Proxmox (decision 2026-08-09); live ops knowledge lives in workflows/postmortems. This inventory is the reversible classification feed for a later operator-approved cull (Minimalist Operations). No revenue path is unblocked by the inventory itself; it reduces infra cognitive load and de-risks accidental reuse of dead Hyper-V paths.

## Done when
- [ ] File exists: `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\ms01-scripts-inventory.md` containing:
  - Inventory date + source path (`C:\Users\lkmot\factory-context\code\`)
  - One row/section per **script** matching `ms01*.ps1` or `ms01*.sh` (65 expected at scope-time; recount on execute)
  - Per script: `path`, `mtime`, `size_bytes`, one-line `purpose` (from header/comments or first meaningful commands), `mapped_workflow` (workflow id or `none`), `era` (docker-wsl-recovery | hyperv-iso | proxmox-adjacent | unknown), `verdict` ∈ {`keep`, `archive-candidate`, `unknown`}
  - Explicit non-script note for the 7 `ms01-*.png` (evidence artifacts, not scripts; "ignore-as-script", no keep/archive verdict required)
  - Summary counts: total scripts, keep, archive-candidate, unknown, and counts by era
  - "Recommended follow-on tangents" section listing cull packages (names only; no deletion)
  - **Completeness check** block proving coverage, e.g. output of
    `(Get-ChildItem 'C:\Users\lkmot\factory-context\code' -File | ? Name -match '^ms01.*\.(ps1|sh)$').Count`
    equals inventory row count (or documents intentional exclusions with reason)
- [ ] Append to `tangents/20260905-ms01-scripts-inventory.md` an Outcome block (status: success/partial/failed, artifacts list, 2-4 line summary) whose summary counts match the inventory md: `keep=N archive-candidate=N unknown=N total=<recount>`
- [ ] Mutation guard proven: git status/diff shows **no** moves/renames/deletes/edits of any `ms01-*` file under `code\` (inventory-only). Acceptable writes: the new outcomes markdown + tangent Outcome block (+ COO live/tmp logs)

## Out of scope
- Deleting, moving, renaming, chmodding, or archiving any script (cull = separate operator-approved tangent)
- Any SSH/login or change on ms01 (192.168.1.120): no service restarts, package installs, Proxmox API calls, Docker commands, scheduled-task edits
- Rewriting scripts to match Proxmox; "keep" means "still potentially referenced / document-worthy," not "run it"
- Editing `workflows.json` (may **recommend** workflow ids only)
- Editing `coo-loop-v3.sh` / `coo-loop-v4.sh` or other harness files to change timeouts (document required env only; operator/loop sets `COO_STAGE_TIMEOUT`)
- Classifying non-flat-dir trees as primary inventory set (`code\ms01-ider\` tools are context for mapping only; optional appendix at most)
- PNG/binary cleanup
- Resolving the open infra blocker `offhost-backup`; may flag `ms01-backup.sh` keep/unknown but must not implement storage changes
- Hard fences: production deploys, DNS/network changes, data deletion, mass email, and any action requiring explicit operator approval under safety rules

## Context (verified during scoping)
**Machine:** Legion local paths only.

**Failure history (must not repeat without new angle)**
- Cycle 1: launch without `--auto` → fixed (`EXEC_AUTO` default medium in coo-loop v3/v4).
- Cycle 2: hard stage timeout 1200s; `coo/live/20260905-ms01-scripts-inventory.execute.live.log` 0 bytes; `coo/tmp/...exec.log` still only cycle-1 permission JSON; no inventory rows. Reloop already used → this RESCOPE.
- **Different this time:** (1) `--auto medium` present; (2) contract requires execute-stage budget `COO_STAGE_TIMEOUT>=2400` (prefer 3600) before bulk work; (3) approach is batch-first (one listing cmd + one bulk header extract + one write) to minimize turns so work completes inside one execute stage.

**Ledger**
- `~\.factory\knowledge\project-ledger.json` project `infrastructure` (tier infra, active)
- Step `infrastructure:ms01-scripts-inventory`: status `proposed`, autonomy `queue`, reversible true
- Blockers: `ms01-scripts-sprawl` (since 2026-07-30), `offhost-backup` (OOS)

**Filesystem (recount 2026-09-05 rescope)**
- 65 scripts: 46 `.ps1` (mtime cluster 2026-07-30), 19 `.sh` (2026-07-15); 7 `ms01-*.png`
- Outcome path missing; pattern confirmed by existing `coo/outcomes/20260905-*-*.md`
- Sample keep-likely: `ms01-backup.sh`, `ms01-container-guard.sh`, `ms01-install-ops.sh`, `ms01-validate-ops.sh`
- Sample archive-likely: Hyper-V/ISO/WinPE/`*-v2/-v3` family (`ms01-rebuild*.ps1`, `ms01-start.ps1`, `ms01-schedule-setup.ps1`, bootwim/iso builders, etc.)

**Workflows / decisions (map targets)**
- Prefer exact ids from `~\.factory\knowledge\workflows.json` when purpose overlaps; else `mapped_workflow: none`
- Decisions: 2026-07-15 docker-ce WSL recovery + backup/guard; 2026-08-09 Proxmox VE 9 supersedes Hyper-V/ISO chain; Tailscale removed 2026-08
- Postmortems (notes only, not workflow ids): `~\.factory\knowledge\postmortems\ms01-proxmox-install-20260809.json`, `ms01-guest-platform-20260809.json`, `ms01-linux-browser-runner-20260809.json`
- Related dir (optional appendix only): `code\ms01-ider\`

**Never execute any ms01-* script.** Read only. Redact tokens from purpose lines (e.g. Telegram env refs).

## Approach sketch
1. **Preflight budget:** Confirm execute stage can run ≥2400s (`$env:COO_STAGE_TIMEOUT` or parent). If still effectively 1200 and cannot be raised from this session, write partial Outcome noting harness budget blocker and stop (do not half-classify 65 files across doomed stage). Prefer operator/loop export `COO_STAGE_TIMEOUT=3600` before claim.
2. **One freeze list:** single PowerShell inventory of Name, FullName, Length, LastWriteTime, Extension for `^ms01.*\.(ps1|sh)$`; record count as completeness baseline. Separately list 7 PNGs for the non-script note.
3. **Bulk purpose extract (not 65 tool turns):** one command that dumps first ~30 lines (or SYNOPSIS/header comments) of every script into a single temp text under `coo/tmp/` (allowed write), then classify offline from that blob. Never run the scripts.
4. **Classify fast:**
   - `era`: docker-wsl-recovery | hyperv-iso | proxmox-adjacent | unknown
   - `mapped_workflow`: workflows.json id or `none`
   - `verdict`: conservative — `keep` if cited by decisions/postmortems or uniquely documents live-adjacent ops (backup/guard/install/validate); `archive-candidate` for superseded Hyper-V/ISO one-offs and `*-v2/-v3` duplicates (expected majority); `unknown` if static read is insufficient (prefer unknown over false keep)
5. **Write once:** `coo/outcomes/ms01-scripts-inventory.md` with summary counts first, full per-script table/sections, PNG note, recommended follow-on cull tangent titles only, Completeness check block.
6. **Prove guards:** completeness count matches rows; `git status` shows no `ms01-*` mutations under `code\` (outside inventory md / tangent Outcome).
7. **Append Outcome block** to this tangent file with matching keep/archive-candidate/unknown/total counts; stop.

## Risk / notes for executor
- Low risk if inventory-only. Highest residual risk is stage timeout — batch I/O and single-file write.
- If recount ≠ 65, inventory the actual set and state the drift; do not fail solely on scope-time number.
- Do not spend turns "improving" scripts or opening ms01 SSH.
- Acceptable artifacts only: `coo/outcomes/ms01-scripts-inventory.md`, tangent Outcome block, optional `coo/tmp/*` scratch for bulk headers.


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
run_started: 2026-09-05T22:59:43-05:00
