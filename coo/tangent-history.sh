#!/usr/bin/env bash
# tangent-history.sh <tangent-id>
# Assembles everything known about one tangent's life:
#   - status + front-matter session ids (scoper/executor/assessor/validator)
#   - progression timeline from the pipeline event log
#   - every session id captured in stage logs, mapped to its transcript on disk
#   - verdicts + validation scores
#   - legacy: full-text search over ALL prior droid sessions (pre-pipeline work)
# Used by the Scoper (precedent check) and by humans reviewing a tangent.
cd "$(dirname "$0")/.." || exit 1
id="$1"; [ -z "$id" ] && { echo "usage: tangent-history.sh <tangent-id>"; exit 1; }
T="tangents/$id.md"; [ -f "$T" ] || { echo "no such tangent: $id"; exit 1; }

echo "# Lineage: $id"
echo ""
echo "## Status"
grep -E '^(status|priority|budget_cycles|escalate_if):' "$T" | sed 's/\r$//'
echo ""
echo "## Progression (pipeline events)"
grep -- "$id" coo/coo-loop.log | tail -40 | sed 's/\r$//' || echo "(no events)"
echo ""
echo "## Stage sessions"
grep -E '^(executor|scoper|assessor|validator)_session:' "$T" | sed 's/^/- front-matter: /;s/\r$//'
for f in coo/tmp/$id.scoped.json coo/tmp/$id.exec.log coo/tmp/$id.verdict.json coo/tmp/$id.validation.json; do
  [ -f "$f" ] || continue
  stage=$(basename "$f" | sed "s/^$id\.//;s/\.json$//;s/\.log$//")
  grep -oE '"session_?[iI]d"[[:space:]]*:[[:space:]]*"[^"]*"' "$f" 2>/dev/null \
    | sed 's/.*: *"//;s/"$//' | sort -u | while read -r s; do
        [ -n "$s" ] && echo "- $stage: $s"
      done
done
echo ""
echo "## Session transcripts on disk"
sids=$(grep -ohE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' \
        "$T" coo/tmp/$id.* 2>/dev/null | sort -u | head -12)
for s in $sids; do
  hit=$(find "$HOME/.factory/sessions" -iname "*$s*" -print 2>/dev/null | head -1)
  if [ -n "$hit" ]; then echo "- $s -> $hit"; else echo "- $s -> (no local transcript)"; fi
done
[ -z "$sids" ] && echo "(no session ids recorded yet)"
echo ""
echo "## Verdicts"
grep -E '=== (VERDICT|VALIDATION):' "$T" | sed 's/\r$//' || echo "(none yet)"
echo ""
echo "## Legacy (pre-pipeline sessions on this domain)"
# The raw tangent ID never appears in legacy sessions (they predate the
# pipeline), and searching it makes the search tool return its default page
# (uniform 0.150 noise — 2026-09-06 probe). Search DOMAIN KEYWORDS instead:
# distinctive tokens from slug + title, score-floored, keyword-verified.
slug=$(echo "$id" | sed 's/^[0-9]\{8\}-//')
# Keywords from the SLUG ONLY. Curated at filing time, no prose noise. LLM
# titles pulled in generic words ("download", "blocker") that wrecked precision
# (2026-09-06 probe, 3 iterations).
kw=$(echo "$slug" | tr ' -_' '\n\n\n' | tr -d '"'"'"'.,:()' | tr 'A-Z' 'a-z' \
  | grep -Ev '^(|verify|verification|check|report|review|hygiene|tangent|update|test|fix)$' \
  | awk '!seen[$0]++' | head -3)
: > "coo/tmp/$id.legacy.seen"
emit_hits() { # $1=query  $2=label
  python "$HOME/.factory/scripts/full-session-search.py" search "$1" 2>/dev/null \
    | grep -E '^\[0\.[3-9]' \
    | while read -r line; do
        low=$(echo "$line" | tr 'A-Z' 'a-z')
        case "$low" in
          *"$2"*)
            sid=$(echo "$line" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}' | head -1)
            grep -q "^$sid$" "coo/tmp/$id.legacy.seen" 2>/dev/null && continue
            echo "$sid" >> "coo/tmp/$id.legacy.seen"
            echo "[match: $2] $(echo "$line" | cut -c1-200)"
            ;;
        esac
      done | head -4
}
if [ -n "$kw" ]; then
  # phrase query first (higher precision), then single tokens (recall)
  bigram=$(echo "$kw" | head -2 | tr '\n' ' ' | sed 's/ $//;s/ / /')
  [ "$(echo "$kw" | wc -w)" -ge 2 ] && emit_hits "$bigram" "$bigram"
  for k in $kw; do emit_hits "$k" "$k"; done
else
  echo "(no distinctive keywords extracted)"
fi
rm -f "coo/tmp/$id.legacy.seen"
exit 0
