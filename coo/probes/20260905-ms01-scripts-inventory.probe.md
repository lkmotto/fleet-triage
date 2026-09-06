=== PROBE ===
# Probe: 20260905-ms01-scripts-inventory
revalidate_after: 2026-09-13 (or immediately before any operator-approved cull tangent runs; after a cull, checks 2/3/4 must be re-baselined against post-cull counts)
checks:
  - check: outcomes md exists and summary counts still state the validated totals
    command: Select-String -Path 'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\ms01-scripts-inventory.md' -Pattern 'Total scripts \| \*\*65\*\*|keep \| \*\*4\*\*|archive-candidate \| \*\*61\*\*|unknown \| \*\*0\*\*'
    expect: 4 matching lines (total=65, keep=4, archive-candidate=61, unknown=0)
  - check: live directory still matches inventory (65 scripts + 7 PNGs, pre-cull)
    command: $f = Get-ChildItem 'C:\Users\lkmot\factory-context\code' -File | Where-Object { $_.Name -match '^ms01' }; "TOTAL=$($f.Count) SCRIPTS=$(($f | Where-Object { $_.Extension -in '.ps1','.sh' }).Count) PNG=$(($f | Where-Object { $_.Extension -eq '.png' }).Count)"
    expect: "TOTAL=72 SCRIPTS=65 PNG=7 (other numbers mean the folder changed after validation; if an operator-approved cull ran, re-baseline instead of failing)"
  - check: per-row verdict counts still equal the summary
    command: $c = Get-Content 'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\ms01-scripts-inventory.md'; "KEEP=$(@($c | Where-Object { $_ -match '\| keep \|$' }).Count) ARCHIVE=$(@($c | Where-Object { $_ -match '\| archive-candidate \|$' }).Count) UNKNOWN=$(@($c | Where-Object { $_ -match '\| unknown \|$' }).Count)"
    expect: "KEEP=4 ARCHIVE=61 UNKNOWN=0"
  - check: no ms01* file in code\ touched after validation (2026-09-06T17:45:00-05:00) unless a cull ran
    command: Get-ChildItem 'C:\Users\lkmot\factory-context\code' -File | Where-Object { $_.Name -match '^ms01' -and $_.LastWriteTime -gt [datetime]'2026-09-06T17:45:00' } | Measure-Object | Select-Object -ExpandProperty Count
    expect: 0 (nonzero = post-validation mutation of fenced files; investigate before trusting the inventory)
  - check: outcomes md carries no unredacted secret material
    command: @(Select-String -Path 'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\ms01-scripts-inventory.md' -Pattern 'ghp_[A-Za-z0-9]|bot[0-9]{6,}|xox[bp]-|AKIA[0-9A-Z]{16}').Count
    expect: 0
  - check: outcome block counts in the tangent match the outcomes md
    command: Select-String -Path 'C:\Users\lkmot\factory-context\code\fleet-triage\tangents\20260905-ms01-scripts-inventory.md' -Pattern 'keep=4 archive-candidate=61 unknown=0 total=65'
    expect: at least 1 match
verdict_on_last_run: PASS 2026-09-06 (all 6 checks re-executed by Validator session; recount 72/65/7, freeze diff 0, verdict cells 4/61/0, secret scan 0, fenced files untouched)
