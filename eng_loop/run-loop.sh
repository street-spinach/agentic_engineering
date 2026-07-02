#!/usr/bin/env bash
# run-loop.sh — the harness. Owns scheduling, budgets, and the billing route.
# It verifies nothing and implements nothing: it branches on exit codes.
set -uo pipefail

MAX_ITERS="${MAX_ITERS:-25}"      # hard budget: total agent invocations
STALL_LIMIT="${STALL_LIMIT:-3}"   # consecutive iterations with no new commit
RATE_SLEEP="${RATE_SLEEP:-1800}"  # seconds to wait on a rate/usage limit

# --- Preflight 1: refuse to run on API billing -------------------------------
# If any of these is set, `claude -p` routes to per-token billing (or a
# gateway). This loop must only run on subscription auth. Confirm once
# interactively with /status that the route is your Pro/Max login.
for v in ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL \
         CLAUDE_CODE_USE_BEDROCK CLAUDE_CODE_USE_VERTEX; do
  if [ -n "${!v:-}" ]; then
    echo "ABORT: $v is set — this would route to per-token API billing."
    echo "Unset it and use subscription login (verify with /status)."
    exit 2
  fi
done

# --- Preflight 2: required tools ---------------------------------------------
for c in claude gh git; do
  command -v "$c" >/dev/null || { echo "ABORT: '$c' not found."; exit 2; }
done
[ -f PROMPT.md ] && [ -x ./verify.sh ] || {
  echo "ABORT: PROMPT.md or executable verify.sh missing."; exit 2; }

# NB: headless runs need non-interactive permissions — pre-approve the tools
# the loop uses in .claude/settings.json, and run in a sandboxed checkout.

iter=0 stall=0
while :; do
  if ./verify.sh; then
    echo "DONE after $iter iteration(s)."; exit 0
  fi
  if [ "$iter" -ge "$MAX_ITERS" ]; then
    echo "ABORT: budget exhausted (MAX_ITERS=$MAX_ITERS) without completion."
    exit 1
  fi

  head_before=$(git rev-parse HEAD 2>/dev/null || echo none)
  out=$(claude -p "$(cat PROMPT.md)" 2>&1) || true
  printf '%s\n' "$out" | tail -n 20

  # Rate limit: wait and retry — costs time, not budget, and not a failure.
  if printf '%s' "$out" | grep -qiE 'rate.?limit|usage limit|limit (reached|hit)'; then
    echo "Rate-limited — sleeping $((RATE_SLEEP / 60)) min, then resuming."
    sleep "$RATE_SLEEP"
    continue
  fi

  iter=$((iter + 1))

  # Stall detection: no new commit means no verifiable progress.
  if [ "$(git rev-parse HEAD 2>/dev/null || echo none)" = "$head_before" ]; then
    stall=$((stall + 1))
    if [ "$stall" -ge "$STALL_LIMIT" ]; then
      echo "ABORT: stalled — $STALL_LIMIT iteration(s) with no commits. Human review needed."
      exit 1
    fi
  else
    stall=0
  fi
done
