#!/usr/bin/env bash
# gen-board.sh -- regenerate status.html (linked board) + per-tangent live view pages.
# Safe to run any time; used manually now and by Task Scheduler wiring later.
set -u
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT" || exit 1
LOG="coo/coo-loop.log"
LIVE="coo/live"
SESSIONS_DIR="/c/Users/lkmot/.factory/sessions/-C-Users-lkmot-factory-context-code-fleet-triage"
mkdir -p "$LIVE"

esc() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

CSS='body{font-family:consolas;background:#111;color:#ddd;padding:16px}table{border-collapse:collapse}td,th{border:1px solid #444;padding:4px 10px}a{color:#6cf}.done{color:#6f6}.running{color:#ff6}.scoping,.assess,.validating{color:#6cf}.parked,.rescope{color:#f66}pre{font-size:11px;white-space:pre-wrap}h4{margin:14px 0 4px}'

# ---- per-tangent view pages ---------------------------------
for tf in tangents/2026*.md; do
  [ -f "$tf" ] || continue
  id=$(basename "$tf" .md)
  s=$(grep -m1 '^status:' "$tf" | cut -d' ' -f2 | tr -d '\r')
  prio=$(grep -m1 '^priority:' "$tf" | cut -d' ' -f2 | tr -d '\r')
  budg=$(grep -m1 '^budget_cycles:' "$tf" | cut -d' ' -f2 | tr -d '\r')
  sid=$(grep -m1 '^executor_session:' "$tf" | cut -d' ' -f2 | tr -d '\r')
  [ -n "$sid" ] && sid="yes (${sid})" || sid="none yet"
  newest_log=$(ls -t "$LIVE/$id".*.live.log 2>/dev/null | head -1)
  logtail=""
  if [ -n "$newest_log" ]; then
    logtail="<h4>live log tail ($newest_log)</h4><pre>$(tail -40 "$newest_log" | esc)</pre><p><a href=\"file:///C:/Users/lkmot/factory-context/code/fleet-triage/$newest_log\">open raw log</a></p>"
  else
    logtail="<h4>live log</h4><p>none for this tangent yet (COO_LIVE instances write these)</p>"
  fi
  {
    echo "<html><head><meta http-equiv='refresh' content='5'><title>$id</title><style>$CSS</style></head><body>"
    echo "<p><a href='status.html'>&larr; board</a></p>"
    echo "<h2>$id</h2><table><tr><th>status</th><th>priority</th><th>budget_cycles</th><th>executor session</th></tr>"
    echo "<tr><td class='$s'>$s</td><td>${prio:-?}</td><td>${budg:-?}</td><td>$sid</td></tr></table>"
    echo "<h4>tangent file (contract + outcomes + verdicts, updates as stages complete)</h4><pre>$(esc < "$tf")</pre>"
    echo "$logtail"
    echo "<p><a href=\"file:///C:/Users/lkmot/.factory/sessions/-C-Users-lkmot-factory-context-code-fleet-triage\">session transcripts folder (newest jsonl = live session)</a></p>"
    echo "</body></html>"
  } > "$LIVE/$id.view.html"
done

# ---- linked board --------------------------------------------
{
  echo "<html><head><meta http-equiv='refresh' content='10'><title>COO Board</title><style>$CSS</style></head><body>"
  echo "<h3>COO Pipeline Board &mdash; $(date -Iseconds)</h3><p>click a tangent for its live view</p>"
  echo "<table><tr><th>tangent</th><th>status</th></tr>"
  for tf in tangents/2026*.md; do
    [ -f "$tf" ] || continue
    n=$(basename "$tf" .md); s=$(grep -m1 '^status:' "$tf" | cut -d' ' -f2 | tr -d '\r')
    echo "<tr><td><a href='$n.view.html'>$n</a></td><td class='$s'>$s</td></tr>"
  done
  echo "</table><h4>recent loop events</h4><pre>$(tail -20 "$LOG" 2>/dev/null | esc)</pre>"
  echo "<p><a href='metrics-view.html'>stage metrics</a></p></body></html>"
} > "$LIVE/status.html"

# ---- metrics view --------------------------------------------
{
  echo "<html><head><meta http-equiv='refresh' content='10'><title>COO Metrics</title><style>$CSS</style></head><body>"
  echo "<p><a href='status.html'>&larr; board</a></p><h3>stage metrics (seconds)</h3><pre>"
  if [ -f coo/metrics.jsonl ]; then tail -60 coo/metrics.jsonl | esc; else echo "no metrics yet (v4 instances emit these)"; fi
  echo "</pre></body></html>"
} > "$LIVE/metrics-view.html"

echo "board + $(ls "$LIVE" | grep -c '\.view\.html') view pages regenerated"
