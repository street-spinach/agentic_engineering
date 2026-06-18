#!/usr/bin/env bash
#
# test-runner.sh — deterministic unit-test execution hook for Claude Code.
#
# This is the EXECUTION half of the unit-testing flow. Judgment (what to test,
# how thoroughly) lives in the unit-test-generator subagent + the unit-testing
# skills. This script only RUNS tests and reports their result deterministically.
# It NEVER calls a model and NEVER decides what to test.
#
# Twin of lint-dispatch.sh. ONE script handles BOTH events (branching on
# hook_event_name), so it never adds a second hook racing on the same event:
#
#   PreToolUse   (Bash)        -> commit gate (HARD block on test failure)
#   SubagentStop               -> validate the generator's output immediately
#                                 (NON-blocking; surfaced via additionalContext)
#
# It does NOT run on PostToolUse (Edit|Write) — that lane is the lint hook's, and
# running tests on every edit would be slow and would race the linter. Tests run
# only at the slice/commit boundary and right after the generator finishes.
#
# DESIGN INVARIANTS
#   * Scope to the CHANGED package(s) only — never the whole repo.
#   * Fail OPEN when no test framework is configured (notice, exit 0), and SAY SO.
#   * Commit gate is the ONLY hard block (exit 2), and ONLY on real test failures.
#   * Setup/environment failures (tag C) are reported, NEVER hard-blocked.
#
# FAILURE-TYPE TAGS (the routing contract — see CLAUDE.md):
#   A = production code wrong (a test caught a real bug)   -> coder fixes code
#   B = generated test wrong / brittle                     -> generator fixes test
#   C = environment / setup failure (couldn't run cleanly) -> report, don't block
#   A vs B is a JUDGMENT call arbitrated against SPEC.md (test contradicts spec =
#   B; code contradicts spec = A) — this script cannot make it. It tags C
#   deterministically and emits raw expected-vs-actual for the orchestrator to
#   split A from B. C and "no framework" never hard-block.
#
# DURABLE ENFORCEMENT NOTE: like the lint gate, this commit gate is a convenience.
# Real enforcement belongs in a git pre-commit hook and/or CI.

set -u

INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0   # no jq => cannot parse => fail open

EVENT="$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty')"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# --------------------------------------------------------------------------- #
# Manifest detection. Walk up from a changed file to the nearest project
# manifest and echo "<type>\t<package_dir>". Resolves per-package in a monorepo.
#   pubspec.yaml -> flutter-dart | package.json -> nodejs
#   pyproject.toml/setup.py -> python | go.mod -> go
# --------------------------------------------------------------------------- #
detect_pkg() {
  local dir; dir="$(cd "$(dirname "$1")" 2>/dev/null && pwd)" || return 1
  while [ -n "$dir" ] && [ "$dir" != "/" ]; do
    if   [ -f "$dir/pubspec.yaml" ];                              then printf 'flutter-dart\t%s\n' "$dir"; return 0
    elif [ -f "$dir/package.json" ];                             then printf 'nodejs\t%s\n'       "$dir"; return 0
    elif [ -f "$dir/pyproject.toml" ] || [ -f "$dir/setup.py" ]; then printf 'python\t%s\n'       "$dir"; return 0
    elif [ -f "$dir/go.mod" ];                                   then printf 'go\t%s\n'           "$dir"; return 0
    fi
    [ "$dir" = "$REPO_ROOT" ] && break
    dir="$(dirname "$dir")"
  done
  return 1
}

# Is this a source/test file worth triggering a run for? (skip docs/config/data.)
is_testable_file() {
  case "$1" in
    *.dart|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.py|*.go) return 0 ;;
    *) return 1 ;;
  esac
}

# --------------------------------------------------------------------------- #
# Per-stack scoped test command. Echoes combined output; returns the runner's
# exit code. Scopes to the changed package; never the whole repo.
# --------------------------------------------------------------------------- #
run_tests() {
  local type="$1" pkg="$2"
  case "$type" in
    flutter-dart)
      if grep -q '^\s*flutter:' "$pkg/pubspec.yaml" 2>/dev/null && command -v flutter >/dev/null 2>&1; then
        ( cd "$pkg" && flutter test 2>&1 ); return $?
      elif command -v dart >/dev/null 2>&1; then
        ( cd "$pkg" && dart test 2>&1 ); return $?
      fi
      echo "__NOFRAMEWORK__"; return 127 ;;
    nodejs)
      local runner; runner="$(node_runner "$pkg")"
      case "$runner" in
        jest)   ( cd "$pkg" && npx --no-install jest 2>&1 ); return $? ;;
        vitest) ( cd "$pkg" && npx --no-install vitest run 2>&1 ); return $? ;;
        mocha)  ( cd "$pkg" && npx --no-install mocha 2>&1 ); return $? ;;
        *)      echo "__NOFRAMEWORK__"; return 127 ;;
      esac ;;
    python)
      if command -v pytest >/dev/null 2>&1; then ( cd "$pkg" && pytest 2>&1 ); return $?
      elif python -m pytest --version >/dev/null 2>&1; then ( cd "$pkg" && python -m pytest 2>&1 ); return $?
      fi
      echo "__NOFRAMEWORK__"; return 127 ;;
    go)
      if command -v go >/dev/null 2>&1; then ( cd "$pkg" && go test ./... 2>&1 ); return $?
      fi
      echo "__NOFRAMEWORK__"; return 127 ;;
    *) echo "__NOFRAMEWORK__"; return 127 ;;
  esac
}

# Detect the node runner from package.json (deps + test script). No model.
node_runner() {
  local pj="$1/package.json"
  [ -f "$pj" ] || { echo ""; return; }
  local hit
  hit="$(jq -r '
    ((.dependencies // {}) + (.devDependencies // {})) as $d
    | (.scripts.test // "") as $s
    | if   ($d.jest   // ($s|test("jest")))   then "jest"
      elif ($d.vitest // ($s|test("vitest"))) then "vitest"
      elif ($d.mocha  // ($s|test("mocha")))  then "mocha"
      else "" end' "$pj" 2>/dev/null)"
  echo "$hit"
}

# --------------------------------------------------------------------------- #
# Classify a run's output into one of: pass | fail (A/B) | setup (C) | none.
# Deterministic heuristics only — A vs B is left to the orchestrator + SPEC.md.
# --------------------------------------------------------------------------- #
classify_run() {
  local code="$1" out="$2"
  printf '%s' "$out" | grep -q '__NOFRAMEWORK__' && { echo "none"; return; }
  [ "$code" -eq 0 ] && { echo "pass"; return; }
  # Setup / environment markers (couldn't run cleanly) => tag C, never block.
  if printf '%s' "$out" | grep -qiE 'build failed|cannot find module|no tests? (ran|found|to run)|import(error| failed)|collection error|syntaxerror|compilation (error|failed)|command not found|no such file'; then
    echo "setup"; return
  fi
  # Test-failure markers => tag A/B, block at the gate.
  if printf '%s' "$out" | grep -qiE 'fail|failed|✗|expected|assertion|panic:'; then
    echo "fail"; return
  fi
  # Non-zero with no clear marker: treat as setup (report, don't hard-block).
  echo "setup"
}

# Pull the most useful failing lines (expected-vs-actual + file:line) from output.
extract_failures() {
  printf '%s' "$1" \
    | grep -iE 'fail|expected|actual|assert|✗|panic:|[A-Za-z0-9_./-]+:[0-9]+' \
    | grep -vE '^\s*(PASS|ok|✓)' \
    | head -n 20
}

# --------------------------------------------------------------------------- #
# Collect the changed files for this event, then run each changed package once.
#   PreToolUse (commit gate) -> staged files
#   SubagentStop             -> working-tree + untracked files
# Echoes a report block on stdout and sets RESULT to: pass|fail|setup|none.
# --------------------------------------------------------------------------- #
RESULT="none"
REPORT=""
run_changed_packages() {
  local files="$1" seen="" line type pkg out code status
  # Build the set of distinct (type, pkg) pairs from the changed files.
  local pkgs=""
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    is_testable_file "$f" || continue
    local abs="$REPO_ROOT/$f"; [ -f "$abs" ] || continue
    line="$(detect_pkg "$abs")" || continue
    case "|$pkgs|" in *"|$line|"*) ;; *) pkgs="${pkgs:+$pkgs
}$line" ;; esac
  done <<EOF
$files
EOF

  [ -n "$pkgs" ] || { RESULT="none"; return; }

  while IFS=$'\t' read -r type pkg; do
    [ -n "$type" ] || continue
    out="$(run_tests "$type" "$pkg")"; code=$?
    status="$(classify_run "$code" "$out")"
    local rel="${pkg#"$REPO_ROOT"/}"; [ "$rel" = "$pkg" ] && rel="."
    case "$status" in
      pass)
        REPORT="${REPORT}[$rel] ($type) PASS — tests green."$'\n' ;;
      fail)
        REPORT="${REPORT}[$rel] ($type) FAIL — tag A/B (arbitrate vs SPEC.md):"$'\n'"$(extract_failures "$out")"$'\n'
        RESULT="fail" ;;
      setup)
        REPORT="${REPORT}[$rel] ($type) tag C — could not run cleanly (setup/env), not blocking:"$'\n'"$(extract_failures "$out" | head -n 8)"$'\n'
        [ "$RESULT" = "fail" ] || RESULT="setup" ;;
      none)
        REPORT="${REPORT}[$rel] ($type) no test framework configured — failing open."$'\n'
        [ "$RESULT" = "fail" ] || [ "$RESULT" = "setup" ] || RESULT="none" ;;
    esac
  done <<EOF
$pkgs
EOF
}

# =========================================================================== #
# COMMIT GATE (PreToolUse: Bash) — hard block ONLY on real test failures.
# =========================================================================== #
command_has_git_commit() {
  local cmd="$1" seg
  while IFS= read -r seg; do
    local found_git=0 skip_next=0 tok
    for tok in $seg; do
      if [ "$skip_next" = "1" ]; then skip_next=0; continue; fi
      if [ "$found_git" = "0" ]; then [ "$tok" = "git" ] && found_git=1; continue; fi
      case "$tok" in
        -C|-c|--git-dir|--work-tree|--namespace|--exec-path) skip_next=1 ;;
        --*=*|-p|--paginate|--no-pager|--bare|--no-replace-objects|--literal-pathspecs) : ;;
        -*) : ;;
        commit) return 0 ;;
        *) found_git=0 ;;
      esac
    done
  done <<EOF
$(printf '%s' "$cmd" | sed -E 's/(\|\||&&|;|\||&)/\n/g')
EOF
  return 1
}

handle_pre_tool_use() {
  local command
  command="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"
  command_has_git_commit "$command" || exit 0

  local staged
  staged="$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null)"
  run_changed_packages "$staged"

  case "$RESULT" in
    fail)
      echo "Commit blocked — unit tests failing on changed package(s):" >&2
      printf '%s' "$REPORT" >&2
      echo "Route: tag A -> coder fixes code; tag B -> unit-test-generator fixes the test (arbitrate vs SPEC.md)." >&2
      exit 2 ;;
    setup)
      # Tag C: report, but do not hard-block (fail open).
      echo "Note — tests could not run cleanly (tag C); not blocking the commit:" >&2
      printf '%s' "$REPORT" >&2
      exit 0 ;;
    none)
      # No framework / no testable change: fail open silently-ish.
      [ -n "$REPORT" ] && { echo "Note — no tests run (no framework / no testable change); failing open." >&2; }
      exit 0 ;;
    *) exit 0 ;;
  esac
}

# =========================================================================== #
# SUBAGENTSTOP — validate the generator's output immediately (non-blocking).
# =========================================================================== #
handle_subagent_stop() {
  # Working-tree + untracked changes (the test files just written).
  local changed
  changed="$( { git -C "$REPO_ROOT" diff --name-only 2>/dev/null
                git -C "$REPO_ROOT" ls-files --others --exclude-standard 2>/dev/null; } )"
  run_changed_packages "$changed"

  [ -n "$REPORT" ] || exit 0
  local header
  case "$RESULT" in
    fail)  header="Test run after generation — FAILURES (arbitrate A/B vs SPEC.md before commit):" ;;
    setup) header="Test run after generation — could not run cleanly (tag C); not blocking:" ;;
    *)     header="Test run after generation:" ;;
  esac
  jq -n --arg ctx "$header"$'\n'"$REPORT" \
    '{hookSpecificOutput: {hookEventName: "SubagentStop", additionalContext: $ctx}}'
  exit 0
}

case "$EVENT" in
  PreToolUse)   handle_pre_tool_use ;;
  SubagentStop) handle_subagent_stop ;;
  *)            exit 0 ;;
esac
