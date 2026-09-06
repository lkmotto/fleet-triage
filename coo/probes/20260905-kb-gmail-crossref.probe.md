=== PROBE ===
# Probe: 20260905-kb-gmail-crossref
revalidate_after: 2026-09-12 (weekly heartbeat probe cycle)
checks:
  - check: credential lookup for gmail resolves to Composio custody (the fixed blind spot)
    command: python C:\Users\lkmot\.factory\scripts\kb-query.py credential "gmail"
    expect: one row starting 'Composio API (OAuth custody: Gmail x2' with auth-api / prd / COMPOSIO_API_KEY (empty output = regression)
  - check: gmail capability still routes read/search to Composio (not Resend)
    command: python C:\Users\lkmot\.factory\scripts\kb-query.py capability "gmail"
    expect: row 'Gmail read/search (BOTH inboxes)' -> 'Composio proxy via smithery composio connection: tools.execute.proxy'
  - check: fence - resend credential row unchanged
    command: python C:\Users\lkmot\.factory\scripts\kb-query.py credential "resend"
    expect: exactly one row 'Resend API' / auth-api / prd / RESEND_API_KEY
  - check: fence - email capability still shows Resend send path
    command: python C:\Users\lkmot\.factory\scripts\kb-query.py capability "email"
    expect: 'Send email' row -> 'Resend REST API (RESEND_API_KEY, Doppler auth-api/prd)'
  - check: proof artifact still on disk and non-empty
    command: Get-Item 'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260905-kb-gmail-crossref-proof.md' | Select-Object Name,Length
    expect: file exists, Length > 0
  - check: deep re-diff vs pre-fix backup still shows exactly one label-only credential change
    command: python C:\Users\lkmot\factory-context\code\fleet-triage\coo\tmp\validate-20260905-kb-gmail-crossref-dbdiff.py
    expect: one REMOVED/ADDED pair ('Composio API (OAuth custody)' -> '...Gmail x2...'), changed row count: 2 (= one renamed row), kb_capabilities / kb_services / kb_deprecations / kb_error_patterns all 'identical'
verdict_on_last_run: PASS 2026-09-06 (validator independently re-executed all four live queries and the backup-vs-live diff: exactly one label-only kb_credentials change, all guidance tables identical)
=== END PROBE ===
