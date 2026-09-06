=== PROBE ===
# Probe: 20260906-e2e-stage3-comp-certainty
revalidate_after: 2026-09-13
checks:
  - check: Stage-4 gate JSON intact with 7 CERTIFIED / 10 BLOCKED across 17 cohort rows
    command: py -3 -c "import json;g=json.load(open(r'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-stage4-gate.json'));print(g['certified_count'],g['blocked_count'],len(g['orders']))"
    expect: prints exactly `7 10 17`
  - check: Minimum CERTIFIED set (Caladium + Big Sky) still CERTIFIED
    command: py -3 -c "import json;g=json.load(open(r'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-stage4-gate.json'));print([r['gate'] for r in g['orders'] if r['slug'] in ('1804_caladium_dr_corinth_tx_76210','308_big_sky_circle_northlake_tx_76226')])"
    expect: prints `['CERTIFIED', 'CERTIFIED']`
  - check: Caladium discovery handoff still ready with 6 picked comps
    command: py -3 -c "import json;s=json.load(open(r'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\1804_caladium_dr_corinth_tx_76210\subject\truetracts_mls_import_status.json'));print(s['handoff']['ready'],s['handoff']['selected_comp_count'])"
    expect: prints `True 6`
  - check: Big Sky discovery handoff still ready with 6 picked comps
    command: py -3 -c "import json;s=json.load(open(r'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\308_big_sky_circle_northlake_tx_76226\subject\truetracts_mls_import_status.json'));print(s['handoff']['ready'],s['handoff']['selected_comp_count'])"
    expect: prints `True 6`
  - check: Caladium spark CSV still has data rows (header + >=1 row)
    command: py -3 -c "print(sum(1 for _ in open(r'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\1804_caladium_dr_corinth_tx_76210\comps\spark_export.csv')) - 1)"
    expect: prints a number >= 100
  - check: Stage-4 attach fence still held (no Stage-3 attach claims on Caladium)
    command: py -3 -c "import json;s=json.load(open(r'C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\1804_caladium_dr_corinth_tx_76210\subject\truetracts_mls_import_status.json'));st=s.get('status',{});print(st.get('file_attached'),st.get('submitted'))"
    expect: prints `False False`
  - check: Gap-analysis Verify/Amend stanza still present
    command: Select-String -Path 'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-gap-analysis.md' -SimpleMatch '## Verify/Amend' -Quiet
    expect: prints `True`
  - check: Recommendation memo still scores the $200/mo MLS API as explicit bottom row
    command: Select-String -Path 'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-recommendation.md' -SimpleMatch 'Explicit bottom row' -Quiet
    expect: prints `True`
  - check: Recycler top verdict still REUSE
    command: Select-String -Path 'C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage3-comp-certainty-recycler.md' -SimpleMatch 'VERDICT: REUSE' -Quiet
    expect: prints `True`
  - check: Parts-bin pb-0076 entry still dated 2026-09-06
    command: py -3 -c "import json;pb=json.load(open(r'C:\Users\lkmot\.factory\knowledge\parts-bin.json'));e=[x for x in pb if x['id']=='pb-0076'][0];print(e['date'][:10])"
    expect: prints `2026-09-06`
  - check: Full re-validation (all 60 machine checks)
    command: py -3 "C:\Users\lkmot\factory-context\code\fleet-triage\coo\tmp\validate-20260906-e2e-stage3-comp-certainty.py"
    expect: exit code 0 and final line `ALL CHECKS GREEN`
verdict_on_last_run: PASS 2026-09-06 (validator machine-check 60/60 green; script at coo\tmp\validate-20260906-e2e-stage3-comp-certainty.py)
