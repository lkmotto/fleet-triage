=== PROBE ===
# Probe: 20260905-glenhaven-harvest-verify
revalidate_after: 2026-10-05
checks:
  - check: Verification report still exists with READY and three PASS verdicts
    command: Select-String -Path 'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\2010_glenhaven_street_arlington_tx_76010\metadata\glenhaven_export_gap_verification.md' -Pattern '\*\*PASS\*\*','READY' | Measure-Object | Select-Object -ExpandProperty Count
    expect: Count >= 4 (garage/boundary/package PASS rows + overall READY)
  - check: Final harvest still shows populated garage rate, complete boundary, zero flags
    command: $h = Get-Content 'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\2010_glenhaven_street_arlington_tx_76010\subject\truetracts_export_harvest.json' -Raw | ConvertFrom-Json; "$($h.parsed.garage_rate)|$($h.boundary.ok)|$($h.boundary.west)/$($h.boundary.north)/$($h.boundary.east)/$($h.boundary.south)|$(@($h.flags).Count)"
    expect: "$6,000|True|E Mitchell St/E Abram St/Swatson Rd/E Park Row Dr|0"
  - check: Core export package files still non-trivial
    command: Get-Item 'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\2010_glenhaven_street_arlington_tx_76010\subject\Report.tdcx','C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\2010_glenhaven_street_arlington_tx_76010\subject\workfiles.zip' | ForEach-Object { "{0}:{1}" -f $_.Name,$_.Length }
    expect: Report.tdcx:13653547 and workfiles.zip:8020796 (>=13 MB and >=8 MB respectively)
  - check: Templates still carry zero verify-markers and the garage rate
    command: $t = Get-Content 'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\2010_glenhaven_street_arlington_tx_76010\subject\truetracts_comment_templates.md' -Raw; "verify:$(([regex]::Matches($t,'verify')).Count) garage6000:$($t -match '6,000 per space')"
    expect: verify:0 garage6000:True
  - check: Early-vs-final inconsistency citation remains accurate (stale snapshot unchanged)
    command: $s = (Get-Content 'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\2010_glenhaven_street_arlington_tx_76010\subject\truetracts_workflow_status.json' -Raw | ConvertFrom-Json).Export.export.template_harvest; "$($s.ok)|$($s.text_chars)|$(@($s.flags).Count)"
    expect: False|229|3 (proves the cited stale state is still the stale state)
verdict_on_last_run: PASS 2026-09-05
