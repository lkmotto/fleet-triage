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
title=$(grep -m1 '^# ' "$T" | sed 's/^# //;s/\r$//')
python "$HOME/.factory/scripts/full-session-search.py" search "$id" 2>/dev/null | head -8
if [ -n "$title" ] && [ "$title" != "$id" ]; then
  echo "--- (by title: $title) ---"
  python "$HOME/.factory/scripts/full-session-search.py" search "$title" 2>/dev/null | head -8
fi
exit 0
