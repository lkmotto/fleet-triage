#!/usr/bin/env bash
cd /c/Users/lkmot/factory-context/code/fleet-triage || exit 1
export COO_INCLUDE="20260905-scout-consumer-wiring.md 20260905-strategic-outcomes-verify.md 20260905-spark-csv-export.md 20260905-ms01-scripts-inventory.md"
if [ -n "${COO_INCLUDE:-}" ]; then TFS="$COO_INCLUDE"; else TFS="tangents/2026*.md"; fi
echo "TFS=[$TFS]"
for tf in $TFS; do
  case "$(basename "$tf")" in TEMPLATE.md|EXAMPLE-*) continue;; esac
  f="tangents/$(basename "$tf")"
  st=$(grep -m1 '^status:' "$f" | cut -d' ' -f2 | tr -d '\r')
  echo "ITER tf=[$tf] f=[$f] st=[$st] match=$([ "$st" != "" ] && echo yes || echo no)"
done
echo "---breaker/fails---"
ls -la coo/.breaker coo/.consec_fails 2>/dev/null; cat coo/.consec_fails 2>/dev/null
