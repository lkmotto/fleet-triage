# 20260905-kb-gmail-crossref — proof of KB cross-reference fix

Executed 2026-09-06T02:52Z–02:56Z (UTC; local 2026-09-05 21:52 CDT) on Legion per the
approved contract (scoped by coo-scoper, operator-approved spec 2026-09-06).
Executor: Droid main session.

## Root cause (verified)

The operative Gmail credential reference lives in `memory.db` table `kb_credentials`
under `key_name = 'COMPOSIO_API_KEY'` (Doppler `auth-api/prd`), but its `what` label was
`Composio API (OAuth custody)` — it contained no `gmail` token, and `kb-query.py`
searches case-insensitive substrings over row text. So `kb-query.py credential "gmail"`
returned nothing while `credential "composio"` hit. The capability side was NOT stale:
`capability "gmail"` already returned `Gmail read/search (BOTH inboxes) -> Composio
proxy ...` at baseline (transcript below), so only the credential row needed the
cross-reference token.

## Changes made

1. `C:\Users\lkmot\.factory\memory.db` — single-row label rename in `kb_credentials`
   (no new rows, no Doppler coords or secret values touched):

   ```sql
   -- pre-check asserted exactly 1 matching row, then:
   UPDATE kb_credentials
      SET what = 'Composio API (OAuth custody: Gmail x2, Sheets, Docs, LinkedIn)'
    WHERE what = 'Composio API (OAuth custody)';
   -- changes() == 1 asserted in code before commit
   ```

   `doppler_project` / `doppler_config` / `key_name` unchanged (`auth-api` / `prd` /
   `COMPOSIO_API_KEY`). No `kb_capabilities` edit was needed — verified already correct.

2. Pre-write safety:
   - Byte-copy backup `C:\Users\lkmot\.factory\memory.db.bak-20260906T025300Z`,
     sha256 `993E64C3793DE6486D97344D5A56F0881AFB852D794CE6A2407644E7A0572EAF`,
     hash-verified identical to the pre-edit DB. No `-wal`/`-shm` sidecar files existed.
   - Exact-string consumer scan: `rg -F "Composio API (OAuth custody)"` across
     `~/.factory/{knowledge,scripts,skills}` and the fleet-triage repo → zero hits,
     so renaming the label could not break any parser.

## Proof commands and results

### Baseline (2026-09-06T02:52:03Z, before the write)

```
### kb-query.py capability "gmail"
ACTION                              PRIMARY PATH
Send email                          Resend REST API (RESEND_API_KEY, Doppler auth-api/prd)
Gmail read/search (BOTH inboxes)    Composio proxy via smithery composio connection: tools.execute.proxy

### kb-query.py credential "gmail"
No credentials matching 'gmail'

### kb-query.py credential "composio"
Composio API (OAuth custody)   auth-api   prd   COMPOSIO_API_KEY
```

Full transcript: `coo/tmp/20260905-kb-gmail-crossref.baseline.txt`

### Post-change (2026-09-06T02:54:20Z, after the write)

```
### kb-query.py credential "gmail"
WHAT                           DOPPLER PROJECT      CONFIG     KEY NAME
Composio API (OAuth custody: Gmail x2, Sheets, Docs, LinkedIn) auth-api prd COMPOSIO_API_KEY

### kb-query.py credential "composio"
Composio API (OAuth custody: Gmail x2, Sheets, Docs, LinkedIn) auth-api prd COMPOSIO_API_KEY

### kb-query.py capability "gmail"   (unchanged, still correct)
Send email                          Resend REST API (RESEND_API_KEY, Doppler auth-api/prd)
Gmail read/search (BOTH inboxes)    Composio proxy via smithery composio connection: tools.execute.proxy

### kb-query.py all "gmail"
Capabilities: the two rows above; Credentials: the Composio row above (was: none)
```

Full transcript: `coo/tmp/20260905-kb-gmail-crossref.post.txt`

### Fence checks (behavior that must NOT change — verified unchanged)

```
### kb-query.py capability "email"     → Send email (Resend) + Tomba rows, unchanged
### kb-query.py credential "resend"    → Resend API / auth-api / prd / RESEND_API_KEY
```

Send-vs-read split preserved: Resend = transactional send, Composio = Gmail OAuth
read/search. Nothing in the rename suggests Gmail credentials are Resend's.

## Scope fences respected

- No credential values, Doppler keys, or mailbox/OAuth tokens touched (label text only).
- `kb-query.py` untouched (read-only tool; the fix was data, not code).
- Only `kb_credentials` row updated; `kb_capabilities`, `kb_services`, deprecations,
  error patterns untouched.
- No Gmail intake/MCP repair work performed (owned by tangent
  `20260905-gmail-intake-repair`).
- No email sent or read; no other KB reorganization.

## Observations (non-blocking, out of scope by contract)

- `kb_services` has no gmail/SMTP row at all; a future hygiene tangent could decide
  whether mail transport belongs there. Not done here — fenced.
- The stub's premise ("capability KB pointed to gmail ... nowhere useful") was only
  half-true at execution time; the credential blind spot was the live defect. Baseline
  transcripts above are the evidence either way.
