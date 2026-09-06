---
id: 20260905-kb-gmail-crossref
status: approved
priority: low
budget_cycles: 2
escalate_if: live gmail credential query still empty after one verified repair cycle, or any need to touch secret values / non-kb_credentials tables
origin: COO v1 audit (scoper gap report: capability KB pointed to gmail, records under composio)
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# Fix / verify KB gmail ↔ Composio cross-reference

## Why
`kb-query.py credential "gmail"` previously returned nothing while the operative Gmail OAuth path lived under Composio (`COMPOSIO_API_KEY`, Doppler `auth-api/prd`). That blind spot burned a scoping session during intake diagnosis — the exact failure mode the capability/credential KB exists to prevent. Revenue-adjacent: Gmail read/search is the order-intake path; lookup must resolve on first query.

## Done when
- [ ] `python C:\Users\lkmot\.factory\scripts\kb-query.py credential "gmail"` prints a row whose label/path points at Composio custody (`COMPOSIO_API_KEY`, Doppler `auth-api` / `prd`) — paste transcript into proof
- [ ] `python C:\Users\lkmot\.factory\scripts\kb-query.py capability "gmail"` still shows Gmail read/search → Composio proxy path (not rewritten to Resend)
- [ ] Fence checks unchanged vs baseline intent: `capability "email"` keeps Resend send path; `credential "resend"` still returns `RESEND_API_KEY` only
- [ ] Proof artifact present and current: `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260905-kb-gmail-crossref-proof.md` (before/after or verify-live transcripts + exact SQL if a write was needed + backup path if a write was needed)
- [ ] If a DB write was required: byte-copy backup under `C:\Users\lkmot\.factory\memory.db.bak-*` exists and only one intentional `kb_credentials` row change was made (`changes()==1`); no secret values altered

## Out of scope
- Any other KB reorganization (`kb_services` mail-transport row, deprecations, error patterns, broad alias system)
- Credential **value** changes, Doppler secret rotation, mailbox/OAuth token work
- Edits to `kb-query.py` code (data fix only; tool is substring search over row text)
- Gmail intake / MCP / HEARTBEAT repair (owned by `20260905-gmail-intake-repair`)
- Mass email send, production deploy, DNS/network, data deletion, or any safety-rule approval action
- Re-running a no-op label rename if live queries already pass (verify-and-close only)

## Context (verified during scoping)
Machine/host path: repo `C:\Users\lkmot\factory-context\code\fleet-triage` on branch `feature/coo-loop`.

**Live KB queries (scoper, read-only, this session):**
- `kb-query.py capability "gmail"` → includes `Gmail read/search (BOTH inboxes)` → `Composio proxy via smithery composio connection: tools.execute.proxy` (also lists Resend under broad match)
- `kb-query.py credential "gmail"` → **HIT**: `Composio API (OAuth custody: Gmail x2, Sheets, Docs, LinkedIn)` / `auth-api` / `prd` / `COMPOSIO_API_KEY`
- `kb-query.py credential "composio"` → same Composio row
- `kb-query.py capability "email"` → Send email via Resend (unchanged fence)
- `kb-query.py credential "resend"` → `Resend API` / `RESEND_API_KEY` (unchanged fence)

**Root-cause model (from proof + decisions; executor must re-verify):**
- `kb-query.py` matches case-insensitive substrings over row text.
- Defect was **credential-side label only**: old `what = 'Composio API (OAuth custody)'` had no `gmail` token → `credential "gmail"` empty.
- Capability side was already correct at baseline; no `kb_capabilities` edit required if still true.

**Prior execution evidence already on disk (do not treat as authority without re-query):**
- Tangent stub: `tangents/20260905-kb-gmail-crossref.md` (still `status: scoping` in frontmatter, but embeds a success outcome block)
- Proof: `coo/outcomes/20260905-kb-gmail-crossref-proof.md`
- Transcripts: `coo/tmp/20260905-kb-gmail-crossref.baseline.txt`, `coo/tmp/20260905-kb-gmail-crossref.post.txt`
- Backup cited: `C:\Users\lkmot\.factory\memory.db.bak-20260906T025300Z` (exists)
- Decision log (`C:\Users\lkmot\.factory\knowledge\decisions.jsonl`, 2026-09-06T02:57:30Z): single-row rename to include `Gmail x2...` in the Composio credential label; alternatives rejected (alias row, capability edit, kb-query code change)
- Related prior decisions: 2026-08-05 Composio replaces IMAP for Gmail API; 2026-09-06 Gmail intake repair (separate tangent)
- `C:\Users\lkmot\.factory\knowledge\tangents.json` parse returned 0 items in this environment (do not rely on it as SoT for this id; use `tangents/20260905-kb-gmail-crossref.md` + proof)
- `project-ledger.json` has no dedicated entry for this hygiene item (infra/docs, not a core project next_step)

**Precedent / what is different if anything still fails:**
- First full attempt claims success via label rename only. Live scoper queries currently pass.
- Difference if repair needed again: only if label drifted or DB restored from pre-fix backup — re-apply the **same** minimal `kb_credentials.what` rename, not a new design. No difference in approach if the failure mode is still "substring miss on credential label".

## Approach sketch
1. Re-run the four queries (`capability/credential "gmail"`, fence `capability "email"`, `credential "resend"`) and capture transcripts under `coo/tmp/`.
2. If all done-when queries already pass and proof is accurate: refresh/confirm `coo/outcomes/20260905-kb-gmail-crossref-proof.md` with verify-live timestamp, fill outcome as success/no-op write, stop. Do not mutate `memory.db`.
3. If `credential "gmail"` is empty again: read-only inspect `kb_credentials` for the Composio row; byte-copy backup `memory.db`; single UPDATE renaming `what` to include an explicit `Gmail` token (same target string as proof unless a clearer minimal token is required); assert `changes()==1`; re-query; do not touch secret columns.
4. Do not edit `kb_capabilities` unless live `capability "gmail"` no longer routes to Composio (unexpected; escalate rather than invent structure).
5. Leave `kb_services` mail-transport gap as a separate future hygiene tangent recommendation only.


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
