#!/usr/bin/env bash
# queue-runner.sh [max_concurrent] [poll_secs] [min_free_ram_kb]
# Keeps up to N single-tangent pipeline instances fed, highest priority first.
# Removes the serial-sweep bottleneck: each queued/assess/validating tangent
# gets its own run-one.sh instance; done/parked/running/scoping are skipped.
# Memory budget: ~600MB private per droid session — cap accordingly (Legion ~30).
# Environmental gate: launches are HELD while free RAM < min_free_ram_kb
# (default ~6GB) — red environments skip dispatch instead of consuming cycles.
cd "$(dirname "$0")/.." || exit 1
MAX="${1:-3}"
POLL="${2:-60}"
RAM_MIN_KB="${3:-6000000}"

free_ram_kb() { powershell -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory" 2>/dev/null | tr -d ' \r\n'; }

prio_of() { grep -m1 '^priority:' "$1" 2>/dev/null | cut -d' ' -f2 | tr -d '\r'; }
rank_of() { case "$1" in high) echo 0;; medium) echo 1;; low) echo 2;; *) echo 3;; esac; }

declare -A JOBS   # tangent-file -> pid
declare -A STARTED

log() { echo "[$(date -Iseconds)] $*" >> coo/coo-loop.log; }

while true; do
  # reap finished jobs
  for t in "${!JOBS[@]}"; do
    pid="${JOBS[$t]}"
    if ! kill -0 "$pid" 2>/dev/null; then
      log "RUNNER reap $t (pid $pid)"
      unset "JOBS[$t]"
    fi
  done

  # candidate list: actionable tangents, priority-ranked
  mapfile -t candidates < <(
    for f in tangents/2026*.md; do
      [ -f "$f" ] || continue
      case "$(basename "$f")" in TEMPLATE.md|EXAMPLE-*) continue;; esac
      s=$(grep -m1 '^status:' "$f" | cut -d' ' -f2 | tr -d '\r')
      case "$s" in
        queued|scoped|approved|assess|validating|rescope)
          echo "$(rank_of "$(prio_of "$f")") $(basename "$f")" ;;
      esac
    done | sort -n | awk '{print $2}'
  )

  slots=$((MAX - ${#JOBS[@]}))
  ram=$(free_ram_kb)
  if [ -n "$ram" ] && [ "$ram" -lt "$RAM_MIN_KB" ]; then
    log "RUNNER hold: free RAM ${ram}kB < ${RAM_MIN_KB}kB — no launches this cycle (environmental gate)"
    sleep "$POLL"
    continue
  fi
  for t in "${candidates[@]}"; do
    [ "$slots" -le 0 ] && break
    [ -n "${JOBS[$t]:-}" ] && continue
    log "RUNNER launch $t (slot ${#JOBS[@]}+1/$MAX)"
    bash coo/run-one.sh "$t" >> coo/runner-instances.log 2>&1 &
    JOBS[$t]=$!
    STARTED[$t]=$(date -Iseconds)
    slots=$((slots - 1))
  done

  sleep "$POLL"
done
