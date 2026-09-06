=== PROBE ===
# Probe: 20260905-gmail-intake-repair
revalidate_after: 2026-09-08 (after 2+ autonudge cycles at 09:00Z/12:00Z on 09-06)
checks:
  - check: outcome artifact JSON-valid, ok, metadata-only (privacy fence)
    command: python -c "import json;d=json.load(open(r'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260905-gmail-intake-repair-scan.json',encoding='utf-8'));print(d['ok'],d['path'],d['result_count'],all(set(m)<= {'id','threadId'} for m in d['messages']))"
    expect: "True composio-rest 201 True (ok, composio path, nonzero count, ids/threads only)"
  - check: smithery-toolbox re-enabled in mcp.json, no BOM
    command: python -c "raw=open(r'C:\Users\lkmot\.factory\mcp.json','rb').read();import json;d=json.loads(raw.decode('utf-8'));print(raw[:1]==b'{', d['mcpServers']['smithery-toolbox'].get('disabled'))"
    expect: "True False (no BOM, disabled is false)"
  - check: scan script still send-free (no modify/mark/label endpoints)
    command: python -c "s=open(r'C:\Users\lkmot\.factory\automations\autonudge-loop\gmail_intake_scan.py',encoding='utf-8').read();print(any(t in s for t in ('/send','/modify','/trash','removeLabelIds','/labels')))"
    expect: "False (no send/mark endpoints present)"
  - check: HEARTBEAT fallback block still wired
    command: Select-String -Path "C:\Users\lkmot\.factory\automations\autonudge-loop\HEARTBEAT.md" -Pattern "gmail_intake_scan.py" | Measure-Object | Select-Object -ExpandProperty Count
    expect: ">= 1 (fallback command referenced in heartbeat)"
  - check: post-repair autonudge cycles no longer report blind intake
    command: Get-ChildItem "C:\Users\lkmot\.factory\automations\autonudge-loop\reports" -Filter "2026090[6-9]*-summary.md" | Sort-Object Name | Select-Object -Last 3 | ForEach-Object { Select-String -Path $_.FullName -Pattern "Gmail scan|UNAVAILABLE" | Select-Object -First 2 }
    expect: no "UNAVAILABLE this session" on the Gmail scan line in reports dated 2026-09-06 onward (MCP tool loaded or fallback used)
  - check: live re-scan still succeeds (optional, network, metadata only)
    command: doppler run -p auth-api -c prd -- python C:\Users\lkmot\.factory\automations\autonudge-loop\gmail_intake_scan.py --out "$env:TEMP\probe-gmail-scan.json"
    expect: "SCAN_OK ... EXIT=0; output JSON contains only id/threadId message keys"
verdict_on_last_run: PASS 2026-09-06 (validator independently re-executed scan: SCAN_OK resultSizeEstimate=201 listed=5, exit 0; 16/16 static checks passed; probe at coo/probes/20260905-gmail-intake-repair.probe.md)
=== END PROBE ===
