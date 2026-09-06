#!/usr/bin/env bash
# ============================================================
# coo-loop-v4.sh -- per-tangent chained pipeline
#   v4 = v3 + git serialization (flock) + metrics.jsonl + status.html board
# Run via run-one.sh <tangent-glob>; cron/Task Scheduler sweeps the inbox only.
# ============================================================
set -u -o pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
COO_APPROVAL="${COO_APPROVAL:-merge}"
COO_PUSH="${COO_PUSH:-0}"
COO_LIVE="${COO_LIVE:-0}"
COO_MAX_CONSEC_FAILS="${COO_MAX_CONSEC_FAILS:-3}"
COO_MODE="${COO_MODE:-once}"
BREAKER="$REPO_ROOT/coo/.breaker"
LOG="$REPO_ROOT/coo/coo-loop.log"
FAILS_FILE="$REPO_ROOT/coo/.consec_fails"
LIVE_DIR="$REPO_ROOT/coo/live"
GITLOCK="$REPO_ROOT/coo/.git.lock"
mkdir -p coo/tmp "$LIVE_DIR"

log() { echo "[$(date -Iseconds)] $*" >> "$LOG"; }
# git operations serialized across parallel instances (index.lock contention killed an executor)
commit_f() {
  (
    flock -w 60 9 || log "WARN gitlock timeout in commit"
    git add "$f" >/dev/null 2>&1
    git add coo/probes coo/live coo/metrics.jsonl >/dev/null 2>&1
    git commit -m "coo: $(basename "$f" .md) $1" >> "$LOG" 2>&1 || true
  ) 9>> "$GITLOCK"
}
push() {
  if [ "$COO_PUSH" = "1" ]; then
    (
      flock -w 120 9 || log "WARN gitlock timeout in push"
      git push >> "$LOG" 2>&1 || log "WARN push failed"
    ) 9>> "$GITLOCK"
  fi
}

# observability: self-contained HTML board, refresh every 15s
write_status() {
  {
    echo "<html><head><meta http-equiv='refresh' content='15'><title>COO Board</title><style>body{font-family:consolas;background:#111;color:#ddd;padding:16px}table{border-collapse:collapse}td,th{border:1px solid #444;padding:4px 10px}.done{color:#6f6}.running{color:#ff6}.scoping,.assess,.validating{color:#6cf}.parked,.rescope{color:#f66}</style></head><body>"
    echo "<h3>COO Pipeline Board &mdash; $(date -Iseconds)</h3><table><tr><th>tangent</th><th>status</th></tr>"
    for tf in tangents/2026*.md; do [ -f "$tf" ] || continue
      n=$(basename "$tf" .md); s=$(grep -m1 '^status:' "$tf" | cut -d' ' -f2 | tr -d '\r')
      echo "<tr><td>$n</td><td class='$s'>$s</td></tr>"
    done
    echo "</table><h4>recent loop events</h4><pre style='font-size:11px'>"
    tail -20 "$LOG" 2>/dev/null | sed "s/</\&lt;/g"
    echo "</pre></body></html>"
  } > "$LIVE_DIR/status.html" 2>/dev/null
}

status_of() { grep -m1 '^status:' "$f" | cut -d' ' -f2 | tr -d '\r'; }

# run_droid <live-suffix> <droid args...>  -- tees output when COO_LIVE=1; hard stage timeout
run_droid() {
  local suffix="$1"; shift
  local id; id=$(basename "$f" .md)
  local to="${COO_STAGE_TIMEOUT:-1200}"
  if [ "$COO_LIVE" = "1" ]; then
    timeout "$to" droid "$@" 2>&1 | tee "$LIVE_DIR/$id.$suffix.live.log"
  else
    timeout "$to" droid "$@"
  fi
}

# ---- stage: SCOPE -------------------------------------------
do_scope() {
  local id; id=$(basename "$f" .md)
  log "SCOPE claim $id"
  sed -i 's/^status:.*/status: scoping/' "$f"; commit_f "claim-scope"
  local PROMPT="$(cat coo/mandates/scoper.md)

=== STUB ===
$(cat "$f")"
  if [ -f "coo/tmp/$id.scopeRetry" ]; then
    PROMPT="$PROMPT

STRICT RE-REQUEST: Your previous attempt performed WORK instead of returning a contract. You are the SCOPER. Return ONLY the === CONTRACT === block per the format above. Do not perform any work, write any files, or run any state-changing commands. Put everything you learned in the contract's Context section — the Executor will re-verify it."
  fi
  if [ -n "${COO_FAST_MODEL:-}" ]; then
    run_droid scope exec --use-spec -o text --auto high -m "$COO_FAST_MODEL" "$PROMPT" > coo/tmp/"$id".scoped.txt 2>> "$LOG"
  else
    run_droid scope exec --use-spec -o text --auto high "$PROMPT" > coo/tmp/"$id".scoped.txt 2>> "$LOG"
  fi
  local scope_rc=0
  [ ! -s "coo/tmp/$id.scoped.txt" ] && scope_rc=1
  if [ "$scope_rc" -ne 0 ]; then
    sed -i 's/^status:.*/status: parked/' "$f"
    echo "- scoper session failed, parked" >> "$f"
    log "SCOPER FAILED $id"; commit_f "parked-scoperfail"
  elif grep -q '=== UNSCOPABLE:' coo/tmp/"$id".scoped.txt 2>/dev/null; then
      sed -i 's/^status:.*/status: parked/' "$f"
      echo "- parked by scoper: $(grep -m1 '=== UNSCOPABLE:' coo/tmp/"$id".scoped.txt)" >> "$f"
      log "UNSCOPABLE $id"; commit_f "parked-unscopable"
    elif grep -q '=== CONTRACT ===' coo/tmp/"$id".scoped.txt; then
      awk '/=== CONTRACT ===/{flag=1;next}/=== END CONTRACT ===/{flag=0}flag' \
        coo/tmp/"$id".scoped.txt > coo/tmp/"$id".body.md
      if grep -q '^---' coo/tmp/"$id".body.md; then
        cat coo/tmp/"$id".body.md > "$f"
        echo "" >> "$f"; cat coo/mandates/executor-addendum.md >> "$f"
        if [ "$COO_APPROVAL" = "blanket" ]; then
          sed -i 's/^status:.*/status: approved/' "$f"; log "CONTRACT $id scoped+approved"
        else
          sed -i 's/^status:.*/status: scoped/' "$f"; log "CONTRACT $id scoped - awaiting merge"
        fi
        commit_f "scoped"
      else
        sed -i 's/^status:.*/status: parked/' "$f"
        echo "- scoper produced malformed contract, parked" >> "$f"
        log "MALFORMED contract $id"; commit_f "parked-malformed"
      fi
    else
      if [ ! -f "coo/tmp/$id.scopeRetry" ]; then
        touch "coo/tmp/$id.scopeRetry"
        log "NO CONTRACT $id - strict scoper reloop (1 of 1)"
        sed -i 's/^status:.*/status: queued/' "$f"; commit_f "scope-reloop"
      else
        rm -f "coo/tmp/$id.scopeRetry"
        sed -i 's/^status:.*/status: parked/' "$f"
        echo "- scoper returned no contract twice, parked for operator review" >> "$f"
        log "NO CONTRACT x2 $id"; commit_f "parked-nocontract"
      fi
    fi
}

# ---- stage: EXECUTE (with session continuity on RELOOP) ------
do_execute() {
  local id; id=$(basename "$f" .md)
  local sid; sid=$(grep -m1 '^executor_session:' "$f" | cut -d' ' -f2 | tr -d '\r')
  local relooped; relooped=$(grep -c 'RELOOP' "$f" 2>/dev/null || true)
  log "EXECUTE claim $id (continuity_sid=${sid:-none} reloop=$relooped)"
  sed -i 's/^status:.*/status: running/' "$f"
  echo "run_started: $(date -Iseconds)" >> "$f"; commit_f "claim-execute"
  local rc=0
  if [ -n "$sid" ] && [ "${relooped:-0}" -gt 0 ]; then
    # RELOOP: resume the SAME executor session with assessor feedback
    { echo "RELOOP continuation for this tangent. Assessor said RELOOP; address the feedback, stay inside the contract, then append an updated Outcome block."; echo ""; echo "=== ASSESSOR FEEDBACK ==="; grep -A2 '## Assessor verdict' "$f"; } > coo/tmp/"$id".cont.md
    run_droid execute exec -o json -s "$sid" -f coo/tmp/"$id".cont.md >> coo/tmp/"$id".exec.log 2>&1 || rc=$?
  else
    run_droid execute exec -o json -f "$f" >> coo/tmp/"$id".exec.log 2>&1 || rc=$?
  fi
  # persist session id for future continuity
  local newsid; newsid=$(grep -o '"sessionId"[[:space:]]*:[[:space:]]*"[^"]*"' coo/tmp/"$id".exec.log 2>/dev/null | head -1 | sed 's/.*:\s*"//;s/"$//')
  if [ -n "$newsid" ]; then
    sed -i '/^executor_session:/d' "$f"
    sed -i "0,/^status:/s//status:/\nexecutor_session: $newsid/" "$f"
    log "SESSION $id -> $newsid"
  fi
  [ "$rc" -eq 0 ] && log "EXECUTOR exited 0 $id" || log "EXECUTOR exited nonzero $id"
  sed -i 's/^status:.*/status: assess/' "$f"; commit_f "executed"
}

# ---- stage: ASSESS ------------------------------------------
do_assess() {
  local id; id=$(basename "$f" .md)
  log "ASSESS $id"
  local PROMPT="$(cat coo/mandates/assessor.md)

=== CONTRACT WITH OUTCOME ===
$(cat "$f")"
  local scope_rc2=0
  if [ -n "${COO_FAST_MODEL:-}" ]; then
    run_droid assess exec -o text --auto medium -m "$COO_FAST_MODEL" "$PROMPT" > coo/tmp/"$id".verdict.txt 2>> "$LOG" || scope_rc2=$?
  else
    run_droid assess exec -o text --auto medium "$PROMPT" > coo/tmp/"$id".verdict.txt 2>> "$LOG" || scope_rc2=$?
  fi
  if [ "$scope_rc2" -eq 0 ]; then
    local V; V=$(grep -m1 '=== VERDICT:' coo/tmp/"$id".verdict.txt || echo "=== VERDICT: RESCOPE === no verdict line")
    echo "" >> "$f"; echo "## Assessor verdict" >> "$f"; echo "$V" >> "$f"
    case "$V" in
      *DONE*)   sed -i 's/^status:.*/status: validating/' "$f"; log "VERDICT $id DONE -> validating" ;;
      *RELOOP*) sed -i 's/^status:.*/status: approved/' "$f"; log "VERDICT $id RELOOP" ;;
      *)        sed -i 's/^status:.*/status: rescope/' "$f"; log "VERDICT $id RESCOPE" ;;
    esac
    commit_f "assessed"
  else
    log "ASSESSOR FAILED $id (retry next sweep)"; commit_f "assessfail"
  fi
}

# ---- stage: VALIDATE ----------------------------------------
do_validate() {
  local id; id=$(basename "$f" .md)
  log "VALIDATE $id"
  local PROMPT="$(cat coo/mandates/validator.md)

=== COMPLETED TANGENT WITH OUTCOME AND VERDICT ===
$(cat "$f")"
  local scope_rc3=0
  if [ -n "${COO_FAST_MODEL:-}" ]; then
    run_droid validate exec -o text --auto medium -m "$COO_FAST_MODEL" "$PROMPT" > coo/tmp/"$id".validation.txt 2>> "$LOG" || scope_rc3=$?
  else
    run_droid validate exec -o text --auto medium "$PROMPT" > coo/tmp/"$id".validation.txt 2>> "$LOG" || scope_rc3=$?
  fi
  if [ "$scope_rc3" -eq 0 ]; then
    local VL; VL=$(grep -m1 '=== VALIDATION:' coo/tmp/"$id".validation.txt || echo "=== VALIDATION: FAIL === no validation line")
    awk '/=== PROBE ===/{flag=1}/=== END PROBE ===/{flag=0}flag' \
      coo/tmp/"$id".validation.txt > "coo/probes/$id.probe.md"
    echo "" >> "$f"; echo "## Validator" >> "$f"; echo "$VL" >> "$f"
    case "$VL" in
      *PASS*) sed -i 's/^status:.*/status: done/' "$f"; log "VALIDATION $id PASS -> done" ;;
      *)      sed -i 's/^status:.*/status: assess/' "$f"; log "VALIDATION $id FAIL -> assess" ;;
    esac
    commit_f "validated"
  else
    log "VALIDATOR FAILED $id (retry next sweep)"; commit_f "validatefail"
  fi
}

# ---- advance one tangent through as many stages as possible --
metric() { echo "{\"id\":\"$(basename "$f" .md)\",\"stage\":\"$1\",\"secs\":$2,\"ts\":\"$(date -Iseconds)\"}" >> coo/metrics.jsonl; }
advance() {
  f="$1"
  local guard=0
  while [ "$guard" -lt 12 ]; do
    guard=$((guard+1))
    local st; st=$(status_of)
    case "$st" in
      queued)     local T0=$SECONDS; do_scope;     metric scope "$((SECONDS-T0))" ;;
      scoped)     [ "$COO_APPROVAL" = "blanket" ] && { sed -i 's/^status:.*/status: approved/' "$f"; commit_f "blanket-approved"; } || { write_status; return 0; } ;;
      approved)   local T1=$SECONDS; do_execute;   metric execute "$((SECONDS-T1))" ;;
      assess)     local T2=$SECONDS; do_assess;    metric assess "$((SECONDS-T2))" ;;
      validating) local T3=$SECONDS; do_validate;  metric validate "$((SECONDS-T3))" ;;
      rescope)    sed -i 's/^status:.*/status: queued/' "$f"; commit_f "returned-to-scoping" ;;
      done|parked|running|scoping) write_status; return 0 ;;
      *)          write_status; return 0 ;;
    esac
    write_status
  done
}

# ================= INBOX SWEEP ================================
if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  git pull --ff-only >> "$LOG" 2>&1 || { log "pull failed, skipping sweep"; exit 1; }
fi
[ -f "$BREAKER" ] && { log "BREAKER TRIPPED - paused (delete coo/.breaker)"; exit 0; }

CYCLE_FAILURES=0
INCLUDE="${COO_INCLUDE:-*.md}"
for tf in tangents/$INCLUDE; do
  case "$(basename "$tf")" in TEMPLATE.md|EXAMPLE-*) continue;; esac
  f="$tf"
  st=$(status_of)
  case "$st" in
    queued|scoped|approved|assess|validating|rescope) advance "$f" ;;
    *) : ;;
  esac
done

if [ "$CYCLE_FAILURES" -gt 0 ]; then
  PREV=$(cat "$FAILS_FILE" 2>/dev/null || echo 0)
  TOTAL=$((PREV + CYCLE_FAILURES)); echo "$TOTAL" > "$FAILS_FILE"
  if [ "$TOTAL" -ge "$COO_MAX_CONSEC_FAILS" ]; then
    touch "$BREAKER"; log "CIRCUIT BREAKER TRIPPED ($TOTAL)"
  fi
else
  echo 0 > "$FAILS_FILE"
fi

write_status
push
log "===== sweep end ====="
[ "$COO_MODE" = "loop" ] && sleep "${COO_CYCLE_SECONDS:-900}" && exec "$0"
