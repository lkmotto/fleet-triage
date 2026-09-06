#!/usr/bin/env bash
# Launch one pinned pipeline instance: run-one.sh <tangent-filename-glob>
cd "$(dirname "$0")/.." || exit 1
export COO_APPROVAL="${COO_APPROVAL:-blanket}"
export COO_PUSH="${COO_PUSH:-1}"
export COO_LIVE="${COO_LIVE:-1}"
export COO_MODE=once
export COO_FAST_MODEL="${COO_FAST_MODEL:-glm-5.3-flash}"
export COO_INCLUDE="$1"
exec ./coo/coo-loop-v4.sh >> coo/coo-loop.log 2>&1
