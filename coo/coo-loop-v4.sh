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
mkdir -p coo/tmp "$LIVE_DIR"

log() { echo "[$(date -Iseconds)] $*" >> "$LOG"; }
# git operations serialized across parallel instances (index.lock contention killed an executor).
# Portable lock: Git Bash on Windows has no flock(1) — mkdir is our atomic primitive.
GITLOCK="$REPO_ROOT/coo/.git.lock.d"
acquire_lock() { # $1 = max wait seconds
  local n=0
  while ! mkdir "$GITLOCK" 2>/dev/null; do
    n=$((n + 1)); [ "$n" -ge "$1" ] && return 1
    # steal a stale lock older than 120s (crashed holder)
    local age=$(( $(date +%s) - $(stat -c %Y "$GITLOCK" 2>/dev/null || echo 0) ))
    [ "$age" -gt 120 ] && rmdir "$GITLOCK" 2>/dev/null
    sleep 1
  done
  return 0
}
release_lock() { rmdir "$GITLOCK" 2>/dev/null; }
commit_f() {
  acquire_lock 60 || log "WARN gitlock timeout in commit"
  git add "$f" >/dev/null 2>&1
  git add coo/probes coo/live coo/metrics.jsonl >/dev/null 2>&1
  git commit -m "coo: $(basename "$f" .md) $1" >> "$LOG" 2>&1 || true
  release_lock
}
push() {
  if [ "$COO_PUSH" = "1" ]; then
    acquire_lock 120 || log "WARN gitlock timeout in push"
    git push >> "$LOG" 2>&1 || log "WARN push failed"
    release_lock
  fi
}

# observability: linked board + per-tangent view pages (gen-board.sh is the single writer)
write_status() {
  bash "$REPO_ROOT/coo/gen-board.sh" >> "$LOG" 2>&1 || log "WARN board gen failed"
}

status_of() { grep -m1 '^status:' "$f" | cut -d' ' -f2 | tr -d '\r'; }

# run_droid <live-suffix> <droid args...>  -- tees output when COO_LIVE=1; hard stage timeout
run_droid() {
  local suffix="$1"; shift
  local id; id=$(basename "$f" .md)
  local to="${COO_STAGE_TIMEOUT:-1200}"
  # Native Factory UI surfacing: every pipeline session gets tags + a log
  # group, so the app's session list groups them (search tag "coo" or
  # tangent:<id> — the "folder in Factory UI", no custom UI required).
  # IMPORTANT: --tag/--log-group-id are `droid exec` subcommand flags, NOT
  # global droid flags — global placement silently drops into the interactive
  # TUI (2026-09-06: scoper spun 20 min in a TUI, watchdog killed it).
  local sub="$1"; shift
  local TAGS=(--tag coo --tag "tangent:$id" --tag "stage:$suffix" --log-group-id "coo/$id")
  if [ "$COO_LIVE" = "1" ]; then
    # -k 30: SIGTERM alone does not reap droid TUI processes — they ignore it
    # and the pipeline hangs forever (2026-09-06: executor wedged past watchdog)
    timeout -k 30 "$to" droid "$sub" "${TAGS[@]}" "$@" 2>&1 | tee "$LIVE_DIR/$id.$suffix.live.log"
  else
    timeout -k 30 "$to" droid "$sub" "${TAGS[@]}" "$@"
  fi
}

# extract result text + session id from a -o json stage log
extract_stage() { # $1=tangent-id $2=stage-basename (scoped|verdict|validation)
  python - "$1" "$2" <<'PYEOF'
import json, sys
base = f"coo/tmp/{sys.argv[1]}.{sys.argv[2]}"
try:
    d = json.load(open(base + ".json", encoding="utf-8", errors="replace"))
    open(base + ".txt", "w", encoding="utf-8").write(str(d.get("result", "") or ""))
    sid = str(d.get("session_id") or d.get("sessionId") or "")
    open(base + ".sid", "w").write(sid)
except Exception:
    pass
PYEOF
}

# record a stage session id in the tangent front-matter (session lineage)
record_sid() { # $1=front-matter-key $2=stage-basename
  local sid; sid=$(tr -d ' \r\n' < "coo/tmp/$(basename "$f" .md).$2.sid" 2>/dev/null)
  [ -z "$sid" ] && return 0
  sed -i "/^$1:/d" "$f"
  # & = the matched status line; broken s//<new>/ syntax silently broke
  # session persistence from day one (2026-09-06)
  sed -i "0,/^status:/s//&\n$1: $sid/" "$f"
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
    run_droid scope exec -o json --use-spec --auto high -m "$COO_FAST_MODEL" "$PROMPT" > coo/tmp/"$id".scoped.json 2>> "$LOG"
  else
    run_droid scope exec -o json --use-spec --auto high "$PROMPT" > coo/tmp/"$id".scoped.json 2>> "$LOG"
  fi
  extract_stage "$id" scoped
  record_sid scoper_session scoped
  local scope_rc=0
  # sanitize: strip ANSI/TUI escape sequences; a TUI leak means the run went
  # interactive by mistake — its output is spinner junk, never a contract
  if [ -s "coo/tmp/$id.scoped.txt" ]; then
    sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g; s/\x1b\][^\x07]*\x07//g' "coo/tmp/$id.scoped.txt" > "coo/tmp/$id.scoped.clean"
    mv "coo/tmp/$id.scoped.clean" "coo/tmp/$id.scoped.txt"
    if grep -qE 'Press ESC to stop|Ctrl\+Enter to queue' "coo/tmp/$id.scoped.txt"; then
      : > "coo/tmp/$id.scoped.txt"; scope_rc=1
      log "TUI LEAK $id - scoper ran interactive; check run_droid flag order"
    fi
  fi
  [ ! -s "coo/tmp/$id.scoped.txt" ] && scope_rc=1
  if [ "$scope_rc" -ne 0 ]; then
    # requeue-once: most scoper failures are environmental (watchdog, TUI leak,
    # daemon death) — parking on first failure starves the pipeline. Park only
    # after a second consecutive failure of the same kind.
    if [ ! -f "coo/tmp/$id.scopeRetry" ]; then
      touch "coo/tmp/$id.scopeRetry"
      sed -i 's/^status:.*/status: queued/' "$f"
      log "SCOPER FAILED $id - requeued for one retry"
      commit_f "scope-retry"
    else
      rm -f "coo/tmp/$id.scopeRetry"
      sed -i 's/^status:.*/status: parked/' "$f"
      echo "- scoper session failed twice, parked for operator review" >> "$f"
      log "SCOPER FAILED x2 $id"; commit_f "parked-scoperfail"
    fi
  elif [ -n "$(grep '=== UNSCOPABLE:' coo/tmp/"$id".scoped.txt 2>/dev/null | grep -v '<one-line reason>' | head -1)" ]; then
      sed -i 's/^status:.*/status: parked/' "$f"
      echo "- parked by scoper: $(grep '=== UNSCOPABLE:' coo/tmp/"$id".scoped.txt | grep -v '<one-line reason>' | head -1)" >> "$f"
      log "UNSCOPABLE $id"; commit_f "parked-unscopable"
    elif grep -q '=== CONTRACT ===' coo/tmp/"$id".scoped.txt; then
      awk '/=== CONTRACT ===/{flag=1;next}/=== END CONTRACT ===/{flag=0}flag' \
        coo/tmp/"$id".scoped.txt > coo/tmp/"$id".body.md
      # hard gate: contract front-matter must carry THIS tangent's id (rejects
      # prompt echoes / template examples masquerading as contracts)
      if grep -qE "^id:[[:space:]]*$id([[:space:]]|$)" coo/tmp/"$id".body.md && grep -q '^---' coo/tmp/"$id".body.md; then
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
  # executor needs explicit --auto or it exits num_turns:0 at the permission gate
  # (2026-09-06: two FM23 verify cycles died on "insufficient permission")
  local EXEC_AUTO="${COO_EXECUTE_AUTO:-medium}"
  if [ -n "$sid" ] && [ "${relooped:-0}" -gt 0 ]; then
    # RELOOP: resume the SAME executor session with assessor feedback
    { echo "RELOOP continuation for this tangent. Assessor said RELOOP; address the feedback, stay inside the contract, then append an updated Outcome block."; echo ""; echo "=== ASSESSOR FEEDBACK ==="; grep -A2 '## Assessor verdict' "$f"; } > coo/tmp/"$id".cont.md
    run_droid execute exec -o json --auto "$EXEC_AUTO" -s "$sid" -f coo/tmp/"$id".cont.md >> coo/tmp/"$id".exec.log 2>&1 || rc=$?
  else
    run_droid execute exec -o json --auto "$EXEC_AUTO" -f "$f" >> coo/tmp/"$id".exec.log 2>&1 || rc=$?
  fi
  # persist session id for future continuity
  local newsid; newsid=$(grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' coo/tmp/"$id".exec.log 2>/dev/null | head -1 | sed 's/.*:\s*"//;s/"$//')
  [ -z "$newsid" ] && newsid=$(grep -o '"sessionId"[[:space:]]*:[[:space:]]*"[^"]*"' coo/tmp/"$id".exec.log 2>/dev/null | head -1 | sed 's/.*:\s*"//;s/"$//')
  if [ -n "$newsid" ]; then
    sed -i '/^executor_session:/d' "$f"
    sed -i "0,/^status:/s//&\nexecutor_session: $newsid/" "$f"
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
    run_droid assess exec -o json --auto medium -m "$COO_FAST_MODEL" "$PROMPT" > coo/tmp/"$id".verdict.json 2>> "$LOG" || scope_rc2=$?
  else
    run_droid assess exec -o json --auto medium "$PROMPT" > coo/tmp/"$id".verdict.json 2>> "$LOG" || scope_rc2=$?
  fi
  extract_stage "$id" verdict
  record_sid assessor_session verdict
  if [ "$scope_rc2" -eq 0 ]; then
    local V; V=$(grep '=== VERDICT:' coo/tmp/"$id".verdict.txt 2>/dev/null | grep -v '<one-line reason>' | head -1 || true)
    [ -z "$V" ] && V="=== VERDICT: RESCOPE === no verdict line"
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
    run_droid validate exec -o json --auto medium -m "$COO_FAST_MODEL" "$PROMPT" > coo/tmp/"$id".validation.json 2>> "$LOG" || scope_rc3=$?
  else
    run_droid validate exec -o json --auto medium "$PROMPT" > coo/tmp/"$id".validation.json 2>> "$LOG" || scope_rc3=$?
  fi
  extract_stage "$id" validation
  record_sid validator_session validation
  if [ "$scope_rc3" -eq 0 ]; then
    local VL; VL=$(grep '=== VALIDATION:' coo/tmp/"$id".validation.txt 2>/dev/null | head -1 || true)
    [ -z "$VL" ] && VL="=== VALIDATION: FAIL === no validation line"
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
# COO_INCLUDE = space-separated tangent FILENAMES (quoted whole at launch).
# No brace globs: bash does not re-expand braces from parameter results, so
# "20260905-{a,b}.md" silently matched nothing (2026-09-06 sweep skipped 4 tangents).
if [ -n "${COO_INCLUDE:-}" ]; then TFS="$COO_INCLUDE"; else TFS="tangents/2026*.md"; fi
for tf in $TFS; do
  case "$(basename "$tf")" in TEMPLATE.md|EXAMPLE-*) continue;; esac
  f="tangents/$(basename "$tf")"
  st=$(status_of)
  case "$st" in
    queued|scoped|approved|assess|validating|rescope) log "SWEEP item=$tf status=$st action=advance"; advance "$f" ;;
    *) log "SWEEP item=$tf status=$st action=skip"; : ;;
  esac
done
log "SWEEP MANIFEST: processed items above; TFS had $(echo $TFS | wc -w) words"

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
