# 20260905-gmail-intake-repair — proof of restoration

Executed 2026-09-05 (local) / 2026-09-06T01:47Z (UTC) on Legion per the approved contract.
Executor: Droid main session (contract scoped by coo-scoper).

## Root cause (verified)

`C:\Users\lkmot\.factory\mcp.json` had the Smithery gateway explicitly disabled:

```json
"smithery-toolbox": { "url": "https://mcp.smithery.run/ljm32901", ..., "disabled": true }
```

With the server disabled, Factory never registered `smithery-toolbox___*` in the session
deferred-tools list, so `ToolSearch select:smithery-toolbox___execute` failed and autonudge
Step 0/0.3 (Gmail order + prospect-reply scans) reported UNAVAILABLE for 4+ consecutive
cycles (20260903T170000Z onward, `~/.factory/automations/autonudge-loop/reports/`).
No OAuth or Doppler problem existed: the Composio grant for `ca_UTAkgVEEqtiV` (lkmotto
Gmail) is ACTIVE and answered a live call during this repair (below). No record was found
explaining who set `disabled: true`.

## Changes made

1. `~/.factory/mcp.json` — `mcpServers.smithery-toolbox.disabled` set `true` → `false`.
   Nothing else touched (URL, Bearer header, all other servers unchanged).
   Byte-copy backup: `~/.factory/mcp.json.bak-20260905-intake-repair`
   (8423 bytes, sha256 `A042000FCF7BFE71C8DB2E2B7ACA810D0DAEBA0A0675C5BFDEB7A2E0FB1AB5DE`,
   verified identical to pre-edit file).
2. `~/.factory/automations/autonudge-loop/gmail_intake_scan.py` — NEW. Metadata-only
   Gmail intake scan via Composio REST proxy (`POST
   https://backend.composio.dev/api/v3/tools/execute/proxy`), pattern adapted from
   `motto-appraisal-pipeline/agent/gmail_api.py` + `tools/_scan_starred_threads.py`
   (stdlib urllib, no new deps). Exit 0 = OK, 2 = auth/config (stop, do not blind-retry),
   1 = transient.
3. `~/.factory/automations/autonudge-loop/HEARTBEAT.md` — under Prerequisites, added the
   "Gmail intake fallback (no MCP needed)" block: when `smithery-toolbox___execute`
   cannot be loaded, run `doppler run -p auth-api -c prd -- python
   ...\gmail_intake_scan.py` and use `result_count` from
   `memory\gmail-scan-latest.json` as the Smart Gate count. Message IDs only — no body
   fetches, no marks, no sends (privacy + safety fences preserved).

## Proof commands and results

1. Post-edit mcp.json integrity:

```
first3: 123,10,32        ← "{\n " — no UTF-8 BOM (AGENTS.md byte-safety rule held)
json_ok disabled=False url=https://mcp.smithery.run/ljm32901
```

2. REST intake scan (metadata only):

```
doppler run -p auth-api -c prd -- python C:\Users\lkmot\.factory\automations\autonudge-loop\gmail_intake_scan.py
SCAN_OK: resultSizeEstimate=201 listed=5 -> ...\memory\gmail-scan-latest.json
EXIT=0
```

HTTP 200 through the Composio proxy with query
`is:unread newer_than:7d (appraisal OR inspection OR valuation OR order)` — proves
(a) `COMPOSIO_API_KEY` valid, (b) Gmail OAuth grant live, (c) intake scan path works.
Artifact: `.../memory/gmail-scan-latest.json` (IDs + threadIds only).
Contract copy: `coo/outcomes/20260905-gmail-intake-repair-scan.json`.

3. MCP tool re-registration: ToolSearch in the repair session still returns
   "Not found: smithery-toolbox___execute" — expected, because the deferred-tools list is
   fixed at session start (before the re-enable). The re-enable takes effect in fresh
   sessions; the next autonudge cycle (2026-09-06T09:00Z) either loads the tool or uses
   the HEARTBEAT fallback. Order intake does not depend on that outcome: the REST path is
   MCP-independent and proven above.

## KB / capability drift note

- `kb-query.py capability "gmail"` still routes Gmail read/search via "smithery composio
  connection"; the Composio REST proxy path is proven here to work with no Smithery MCP
  involvement (same-day precedent: parts-bin pb-0070, 2026-09-04).
- `kb-query.py credential "gmail"` is empty; the operative key is
  `kb-query.py credential "composio"` → Doppler `auth-api/prd` `COMPOSIO_API_KEY`.
- IMAP revival was explicitly rejected: HEARTBEAT deprecates `gmail_order_check.py`
  (app password expired); Composio is the OAuth custodian per decisions.jsonl 2026-08-05.

## Scope fences respected

Metadata only (no bodies/snippets persisted), no messages marked read, no pipeline stage
triggers for live orders, no Doppler secret changes, no outbound email. Composio OAuth
needed no reauth (200 response), so no operator Allow click was required.
