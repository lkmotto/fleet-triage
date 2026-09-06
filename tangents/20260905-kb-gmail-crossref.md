---
id: 20260905-kb-gmail-crossref
status: queued
priority: low
budget_cycles: 1
escalate_if: immediate
origin: COO v1 audit (scoper gap report: capability KB pointed to gmail, records under composio)
---

# Fix capability KB gmail/composio cross-reference

## Why
`kb-query.py capability/credential "gmail"` pointed nowhere useful during the intake
diagnosis; the operative records lived under "composio". A scoping session lost time
to a stale KB entry — exactly what the KB exists to prevent.

## Done when
- [ ] memory.db kb_capabilities/kb_credentials updated or cross-referenced so a
      "gmail" query returns the composio records (verified by running the query)
- [ ] Change documented in the outcome block

## Out of scope
- Any other KB reorganization; any credential value changes

## Contract (scoped and operator-approved 2026-09-06; executed same session by the scoper under operator dispatch approval)
- [x] `kb-query.py credential "gmail"` returns a row pointing at Composio custody
      (`COMPOSIO_API_KEY` / Doppler `auth-api/prd`) — verified by running the query
- [x] `kb-query.py capability "gmail"` still returns the Gmail read/search → Composio
      path; fence checks (`capability "email"`, `credential "resend"`) unchanged
- [x] Proof artifact: `coo/outcomes/20260905-kb-gmail-crossref-proof.md`
      (before/after transcripts + exact SQL + backup/consumer-scan evidence)

## Outcome (filled by executor)
- status: success
- artifacts: `coo/outcomes/20260905-kb-gmail-crossref-proof.md`;
  `coo/tmp/20260905-kb-gmail-crossref.baseline.txt`;
  `coo/tmp/20260905-kb-gmail-crossref.post.txt`;
  `C:\Users\lkmot\.factory\memory.db.bak-20260906T025300Z` (pre-write backup)
- what was done: Single-row `kb_credentials` label rename in memory.db
  (`Composio API (OAuth custody)` → `Composio API (OAuth custody: Gmail x2, Sheets, Docs,
  LinkedIn)`) with `changes()==1` assertion and hash-verified byte-copy backup. No
  capability edit needed — `capability "gmail"` already routed to Composio at baseline;
  the stale claim was the credential side only. No other KB tables touched.
- what remains: nothing — done-when fully met. Non-blocking observation recorded in the
  proof: `kb_services` has no mail-transport row (future hygiene tangent, fenced here).
- rescope note: N/A — no bail.

run_started: 2026-09-06T02:52:03Z
run_finished: 2026-09-06T02:56:40Z
