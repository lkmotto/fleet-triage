#!/usr/bin/env bash
# ============================================================
# coo-loop.sh v2 -- git-dictated tangent pipeline (free trigger)
# ============================================================
# Phases per cycle:
#   1. SCOPE    status:queued   -> droid exec --use-spec (Scoper) -> contract
#   2. EXECUTE  status:approved -> droid exec --auto medium (Executor)
#   3. ASSESS   status:assess   -> droid exec (Assessor) -> DONE|RELOOP|RESCOPE
# Empty cycle cost: one git rev-parse + a grep. No LLM session.
#
# Env:
#   COO_APPROVAL=merge|blanket   blanket: scoped -> approved automatically
#                                (validation mode; merge = PR gate in steady state)
#   COO_PUSH=0|1                 push commits to origin after each state change
#   COO_MAX_CONSEC_FAILS=3       circuit breaker
#   COO_CYCLE once|loop          once = single cycle (Task Scheduler calls per trigger)
# ============================================================
set -u
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
COO_APPROVAL="${COO_APPROVAL:-merge}"
COO_PUSH="${COO_PUSH:-0}"
COO_MAX_CONSEC_FAILS="${COO_MAX_CONSEC_FAILS:-3}"
COO_MODE="${COO_MODE:-once}"
BREAKER="$REPO_ROOT/coo/.breaker"
LOG="$REPO_ROOT/coo/coo-loop.log"
FAILS_FILE="$REPO_ROOT/coo/.consec_fails"
mkdir -p coo/tmp

log() { echo "[$(date -Iseconds)] $*" >> "$LOG"; }
push() { if [ "$COO_PUSH" = "1" ]; then git push >> "$LOG" 2>&1 || log "WARN push failed"; fi; }

# ---- upstream sync (skip if branch has none) -----------------
if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  git pull --ff-only >> "$LOG" 2>&1 || { log "pull failed, skipping cycle"; exit 1; }
fi

[ -f "$BREAKER" ] && { log "BREAKER TRIPPED - paused (delete coo/.breaker to resume)"; exit 0; }

CYCLE_FAILURES=0

# ================= PHASE 1: SCOPE ============================
for f in $(grep -l '^status: *queued$' tangents/*.md 2>/dev/null || true); do
  id=$(basename "$f" .md)
  log "SCOPE claim $id"
  sed -i 's/^status:.*/status: scoping/' "$f"
  git add "$f" >/dev/null; git commit -m "coo: claim $id for scoping" >> "$LOG" 2>&1 || true

  PROMPT="$(cat coo/mandates/scoper.md)

=== STUB ===
$(cat "$f")"

  if droid exec --use-spec -o text --auto high "$PROMPT" > coo/tmp/"$id".scoped.txt 2>> "$LOG"; then
    if grep -q '=== UNSCOPABLE:' coo/tmp/"$id".scoped.txt; then
      REASON=$(grep -m1 '=== UNSCOPABLE:' coo/tmp/"$id".scoped.txt)
      sed -i 's/^status:.*/status: parked/' "$f"
      echo "- parked by scoper: $REASON" >> "$f"
      log "UNSCOPABLE $id: $REASON"
    elif grep -q '=== CONTRACT ===' coo/tmp/"$id".scoped.txt; then
      # contract body = scoper output between markers; front-matter merged by script
      awk '/=== CONTRACT ===/{flag=1;next}/=== END CONTRACT ===/{flag=0}flag' \
        coo/tmp/"$id".scoped.txt > coo/tmp/"$id".body.md
      # merge: take scoper front-matter + body as the new file
      if grep -q '^---' coo/tmp/"$id".body.md; then
        cat coo/tmp/"$id".body.md > "$f"
        echo "" >> "$f"; cat coo/mandates/executor-addendum.md >> "$f"
        sed -i 's/^status:.*/status: scoped/' "$f"
        if [ "$COO_APPROVAL" = "blanket" ]; then
          sed -i 's/^status:.*/status: approved/' "$f"
          log "CONTRACT $id scoped + blanket-approved"
        else
          log "CONTRACT $id scoped - awaiting approval (merge to approve)"
        fi
      else
        sed -i 's/^status:.*/status: parked/' "$f"
        echo "- scoper produced malformed contract, parked for operator review" >> "$f"
        log "MALFORMED contract $id"
      fi
    else
      sed -i 's/^status:.*/status: parked/' "$f"
      echo "- scoper returned no contract, parked for operator review" >> "$f"
      log "NO CONTRACT $id"; CYCLE_FAILURES=$((CYCLE_FAILURES+1))
    fi
  else
    sed -i 's/^status:.*/status: parked/' "$f"
    echo "- scoper session failed, parked" >> "$f"
    log "SCOPER FAILED $id"; CYCLE_FAILURES=$((CYCLE_FAILURES+1))
  fi
  git add tangents/ coo/ >/dev/null; git commit -m "coo: $id scoped" >> "$LOG" 2>&1 || true
done

# ================= PHASE 2: EXECUTE ==========================
for f in $(grep -l '^status: *approved$' tangents/*.md 2>/dev/null || true); do
  id=$(basename "$f" .md)
  log "EXECUTE claim $id"
  sed -i 's/^status:.*/status: running/' "$f"
  echo "run_started: $(date -Iseconds)" >> "$f"
  git add "$f" >/dev/null; git commit -m "coo: claim $id for execution" >> "$LOG" 2>&1 || true

  if droid exec -o text --auto medium -f "$f" >> coo/tmp/"$id".exec.log 2>&1; then
    log "EXECUTOR exited 0 $id"
  else
    log "EXECUTOR exited nonzero $id (assessor will judge)"
  fi
  sed -i 's/^status:.*/status: assess/' "$f"
  git add tangents/ coo/ >/dev/null; git commit -m "coo: $id executed, awaiting assessment" >> "$LOG" 2>&1 || true
done

# ================= PHASE 3: ASSESS ===========================
for f in $(grep -l '^status: *assess$' tangents/*.md 2>/dev/null || true); do
  id=$(basename "$f" .md)
  log "ASSESS $id"
  PROMPT="$(cat coo/mandates/assessor.md)

=== CONTRACT WITH OUTCOME ===
$(cat "$f")"

  if droid exec -o text --auto medium "$PROMPT" > coo/tmp/"$id".verdict.txt 2>> "$LOG"; then
    V=$(grep -m1 '=== VERDICT:' coo/tmp/"$id".verdict.txt || echo "=== VERDICT: RESCOPE === assessor returned no verdict line")
    case "$V" in
      *DONE*)    NEW=done ;;
      *RELOOP*)  NEW=approved ;;   # same contract, one retry (assessor allows)
      *)         NEW=rescope; CYCLE_FAILURES=$((CYCLE_FAILURES+1)) ;;
    esac
    echo "" >> "$f"; echo "## Assessor verdict" >> "$f"; echo "$V" >> "$f"
    sed -i "s/^status:.*/status: $NEW/" "$f"
    log "VERDICT $id -> $NEW"
  else
    log "ASSESSOR FAILED $id (leave in assess for retry)"; CYCLE_FAILURES=$((CYCLE_FAILURES+1))
  fi
  git add tangents/ coo/ >/dev/null; git commit -m "coo: $id -> $NEW" >> "$LOG" 2>&1 || true
done

# ---- RESCOPE phase: rescope items go back to the scoper next cycle -----------
for f in $(grep -l '^status: *rescope$' tangents/*.md 2>/dev/null || true); do
  sed -i 's/^status:.*/status: queued/' "$f"   # scoper sees outcome block + verdict
  git add "$f" >/dev/null; git commit -m "coo: $id returned to scoping" >> "$LOG" 2>&1 || true
done

# ---- circuit breaker ---------------------------------------------------------
if [ "$CYCLE_FAILURES" -gt 0 ]; then
  PREV=$(cat "$FAILS_FILE" 2>/dev/null || echo 0)
  TOTAL=$((PREV + CYCLE_FAILURES)); echo "$TOTAL" > "$FAILS_FILE"
  if [ "$TOTAL" -ge "$COO_MAX_CONSEC_FAILS" ]; then
    touch "$BREAKER"; log "CIRCUIT BREAKER TRIPPED ($TOTAL consecutive failures)"
  fi
else
  echo 0 > "$FAILS_FILE"
fi

push
log "===== cycle end ====="
[ "$COO_MODE" = "loop" ] && sleep "${COO_CYCLE_SECONDS:-900}" && exec "$0"
