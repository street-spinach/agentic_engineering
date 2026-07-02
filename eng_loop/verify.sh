#!/usr/bin/env bash
# verify.sh — the machine-checkable gate for an agentic coding loop.
#
# Contract (this is the entire API):
#   exit 0  -> everything green AND the overall task is complete  -> loop stops
#   exit 1  -> not done; stdout explains the one most useful thing to fix next
#
# Design rules baked in:
#   * cheapest checks first, fail fast — one clear failure per run
#   * non-interactive: CI=1, no watch modes, timeouts on anything that can hang
#   * stdout becomes the next iteration's prompt context: short, legible, log tails only
#   * "healthy" (tests pass) is NOT "done" (plan complete) — both are checked

set -uo pipefail
export CI=1 FORCE_COLOR=0
LOG_DIR=".agent/logs"
mkdir -p "$LOG_DIR"

# --- 0. Gate integrity: the agent must not edit its own exam -----------------
if git rev-parse -q --verify HEAD >/dev/null 2>&1 \
   && ! git diff --quiet HEAD -- "$0"; then
  echo "FAIL: $0 differs from HEAD — the gate itself was modified. Revert it."
  exit 1
fi

run() {  # run <name> <cmd...> : log everything, surface only the tail on failure
  local name="$1"; shift
  local log="$LOG_DIR/$name.log"
  echo "=== $name ==="
  if "$@" >"$log" 2>&1; then
    echo "PASS: $name"
  else
    echo "FAIL: $name (exit $?)"
    echo "--- tail of $log ---"
    tail -n 40 "$log"
    exit 1
  fi
}

# --- 1. Static checks: seconds to run, catch the dumb stuff ------------------
run format    npx prettier --check .          # py: ruff format --check .
run lint      npx eslint . --max-warnings 0   # py: ruff check .
run typecheck npx tsc --noEmit                # py: mypy .   rust: cargo check

# --- 2. Tests: the real signal ------------------------------------------------
run unit-tests timeout 600 npx vitest run     # py: pytest -q   go: go test ./...

# --- 3. Build: it must actually assemble --------------------------------------
run build     npm run --silent build          # rust: cargo build --release

# --- 4. Optional deeper gates (enable once they exist) -------------------------
# run integration timeout 900  npm run test:integration
# run e2e         timeout 1200 npx playwright test

# --- 5. Completion: healthy is not the same as done ---------------------------
echo "=== completion ==="
if ! open_issues=$(gh issue list --label agent-ready --state open \
                     --json number --jq 'length' 2>"$LOG_DIR/gh.log"); then
  echo "NOT DONE: cannot query GitHub issues (gh failed) — never a silent pass."
  tail -n 5 "$LOG_DIR/gh.log"
  exit 1
fi
if [ "$open_issues" -gt 0 ]; then
  echo "NOT DONE: $open_issues open agent-ready issue(s) remain:"
  gh issue list --label agent-ready --state open --limit 10
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "NOT DONE: working tree has uncommitted changes:"
  git status --short | head -n 20
  exit 1
fi

echo "ALL GREEN: checks pass, plan complete, tree clean."
exit 0