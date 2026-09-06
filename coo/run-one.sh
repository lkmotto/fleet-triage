#!/usr/bin/env bash
# Launch one pinned pipeline instance.
# Usage: run-one.sh "tangent-file.md tangent2.md ..."   (space-separated, quoted whole)
#        run-one.sh ""                                   (full sweep, all tangents)
cd "$(dirname "$0")/.." || exit 1
export COO_APPROVAL="${COO_APPROVAL:-blanket}"
export COO_PUSH="${COO_PUSH:-1}"
export COO_LIVE="${COO_LIVE:-1}"
export COO_MODE=once
export COO_FAST_MODEL="${COO_FAST_MODEL:-glm-5.3-flash}"
export COO_INCLUDE="$1"
exec ./coo/coo-loop-v4.sh >> coo/coo-loop.log 2>&1
