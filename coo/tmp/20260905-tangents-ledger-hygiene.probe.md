=== PROBE ===
# Probe: 20260905-tangents-ledger-hygiene
revalidate_after: 2026-10-06
checks:
  - check: timestamped backup exists beside live tangents.json
    command: Get-ChildItem "C:\Users\lkmot\.factory\knowledge\tangents.json*.bak" | Select-Object -ExpandProperty Name
    expect: at least one tangents.json.<UTC>.bak, specifically tangents.json.20260906T020828Z.bak
  - check: live ledger clean, coherent, id-complete vs newest backup
    command: python -c "import json,glob,os;K=r'C:\Users\lkmot\.factory\knowledge';d=json.load(open(os.path.join(K,'tangents.json'),encoding='utf-8'));b=json.load(open(sorted(glob.glob(os.path.join(K,'tangents.json*.bak')))[-1],encoding='utf-8'));pid=lambda a:[e.get('id') for e in a];print('pending',len(d['pending']),'cip',sum(1 for e in d['pending'] if e.get('status')=='completed'),'completed',len(d['completed']),'total',len(pid(d['pending'])+pid(d['completed'])),'idmatch',set(pid(d['pending'])+pid(d['completed']))==set(pid(b['pending'])+pid(b['completed'])))"
    expect: "pending 0 cip 0 completed >= 74 total == completed (no rows lost) idmatch True (vs newest backup)"
  - check: reconciliation note and last_updated present
    command: python -c "import json;d=json.load(open(r'C:\Users\lkmot\.factory\knowledge\tangents.json',encoding='utf-8'));print(d['last_updated']);print(d['_note'][:160])"
    expect: ISO last_updated (>= 2026-09-06) and _note text describing the move of status=completed rows out of pending
  - check: decision trail still records the reconciliation
    command: Select-String -Path "C:\Users\lkmot\.factory\knowledge\decisions.jsonl" -Pattern "Reconciled tangents.json" | Select-Object -First 1
    expect: one matching line timestamped 2026-09-06T02:10:04Z describing 47 rows moved and ids preserved
  - check: stub outcome block still filled
    command: Select-String -Path "C:\Users\lkmot\factory-context\code\fleet-triage\tangents\20260905-tangents-ledger-hygiene.md" -Pattern "status: success" | Select-Object -First 1
    expect: "status: success" under the Outcome section
verdict_on_last_run: PASS 2026-09-06 (full independent re-execution of all done-when items passed; script at coo/tmp/20260905-tangents-ledger-hygiene.validate.py)
=== END PROBE ===
