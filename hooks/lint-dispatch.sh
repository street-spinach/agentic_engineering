#!/usr/bin/env bash
#
# lint-dispatch.sh — deterministic auto-linting hook for Claude Code.
#
# This is the CODE-LEVEL, MECHANICAL complement to the Goldfish spec gate.
# It NEVER calls a model and NEVER judges intent. It only runs formatters /
# linters and reports their output deterministically.
#
# ONE script handles BOTH events (branching on hook_event_name), so there is
# never a second hook racing on the same event:
#
#   PostToolUse  (Edit|Write|MultiEdit) -> per-edit feedback loop (NON-blocking)
#   PreToolUse   (Bash)                 -> commit gate           (HARD block)
#
# Wiring lives in .claude/settings.json (project-level, shared via git).
#
# DESIGN INVARIANTS
#   * Lint only the changed/staged file(s). Never the whole repo on an edit.
#   * Fail open: missing linter/formatter/config => one short notice, exit 0.
#   * Idempotent; only side effect is formatting the edited file in place.
#   * Per-edit tier is ALWAYS exit 0 (never block) to avoid edit->fail->edit loops.
#   * Commit gate is the ONLY hard block (exit 2).
#
# STALE-old_string EDGE CASE (chosen mitigation):
#   Auto-formatting can rewrite a file after Claude's edit, which would make a
#   subsequent Edit's `old_string` stale. We DO format in place (per spec), and
#   whenever formatting actually changed the file we emit a `systemMessage`
#   telling Claude the file was reformatted so it RE-READS before editing again.
#
# DURABLE ENFORCEMENT NOTE:
#   The commit gate here is a convenience only. `git commit` can be aliased,
#   chained with &&, or invoked as `git -C <path> commit`; we parse robustly but
#   cannot resolve shell aliases. Real, durable enforcement belongs in a genuine
#   git pre-commit hook and/or CI. This gate just catches the common cases early.

set -u

# --------------------------------------------------------------------------- #
# Read the event once. All inputs come from stdin as JSON, parsed with jq.
# --------------------------------------------------------------------------- #
INPUT="$(cat)"

if ! command -v jq >/dev/null 2>&1; then
  # No jq => we cannot parse input. Fail open, never block.
  exit 0
fi

EVENT="$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty')"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# --------------------------------------------------------------------------- #
# DISPATCH TABLE — trivially extensible. Add a row + the matching format_*/lint_*
# helper to support a new language. Keys are language ids.
#
#   ext_to_lang  : file extension  -> language id
#   format_<lang>: in-place formatter for one file (formatters are pure rewrites)
#   lint_<lang>  : linter for one file, emitting `path:line:col: message` lines
# --------------------------------------------------------------------------- #
ext_to_lang() {
  case "$1" in
    js|jsx|ts|tsx|mjs|cjs) echo "js"     ;;
    py)                    echo "python" ;;
    go)                    echo "go"     ;;
    rs)                    echo "rust"   ;;
    *)                     echo ""       ;;  # not a language we lint
  esac
}

# --------------------------------------------------------------------------- #
# Path filtering: decide whether a file is one we should lint at all.
# Skips docs/config/data, lockfiles, generated/vendored trees, and this repo's
# own non-code dirs (.claude/, skills/, agents/) so we never fire on SPEC.md,
# skill .md, settings.json, etc.
# --------------------------------------------------------------------------- #
is_lintable_path() {
  local path="$1"
  [ -n "$path" ] || return 1
  [ -f "$path" ] || return 1

  # Normalize to a repo-relative path for directory checks.
  local rel="${path#"$REPO_ROOT"/}"

  # Excluded directories (repo-own non-code + generated/vendored).
  case "/$rel" in
    */.claude/*|*/skills/*|*/agents/*) return 1 ;;
    */node_modules/*|*/vendor/*|*/dist/*|*/build/*|*/target/*|*/.git/*) return 1 ;;
    */__pycache__/*|*/.venv/*|*/venv/*) return 1 ;;
  esac
  case "$rel" in
    .claude/*|skills/*|agents/*) return 1 ;;
  esac

  local base="${path##*/}"

  # Lockfiles and obviously generated artifacts.
  case "$base" in
    package-lock.json|yarn.lock|pnpm-lock.yaml|Cargo.lock|poetry.lock|go.sum|Gemfile.lock|composer.lock) return 1 ;;
    *.min.js|*.min.css|*.generated.*|*_pb2.py|*.pb.go) return 1 ;;
  esac

  # Extension must map to a language we lint. (.md/.json/.yaml/.yml/.txt etc.
  # have no mapping and are skipped here.)
  local ext="${base##*.}"
  [ "$ext" != "$base" ] || return 1   # no extension at all
  [ -n "$(ext_to_lang "$ext")" ] || return 1
  return 0
}

# --------------------------------------------------------------------------- #
# Tool resolution. Returns the runnable command on stdout, or non-zero if the
# tool is unavailable (caller then fails open with a notice).
# --------------------------------------------------------------------------- #
resolve_bin() {
  local bin="$1"
  if command -v "$bin" >/dev/null 2>&1; then
    printf '%s' "$bin"
    return 0
  fi
  return 1
}

# --------------------------------------------------------------------------- #
# Formatters — rewrite one file in place. Each echoes "changed" on stdout if it
# modified the file, "missing" if the tool is absent, "" otherwise.
# --------------------------------------------------------------------------- #
format_file() {
  local lang="$1" f="$2" before after bin
  before="$(shasum "$f" 2>/dev/null | awk '{print $1}')"
  case "$lang" in
    js)
      if bin="$(resolve_bin prettier)"; then
        $bin --write "$f" >/dev/null 2>&1
      elif command -v npx >/dev/null 2>&1 && npx --no-install prettier --version >/dev/null 2>&1; then
        npx --no-install prettier --write "$f" >/dev/null 2>&1
      else
        echo "missing"; return 0
      fi
      ;;
    python)
      if bin="$(resolve_bin black)"; then $bin -q "$f" >/dev/null 2>&1; else echo "missing"; return 0; fi
      ;;
    go)
      if bin="$(resolve_bin gofmt)"; then $bin -w "$f" >/dev/null 2>&1; else echo "missing"; return 0; fi
      ;;
    rust)
      if bin="$(resolve_bin rustfmt)"; then $bin "$f" >/dev/null 2>&1; else echo "missing"; return 0; fi
      ;;
    *) return 0 ;;
  esac
  after="$(shasum "$f" 2>/dev/null | awk '{print $1}')"
  [ "$before" != "$after" ] && echo "changed"
  return 0
}

# --------------------------------------------------------------------------- #
# Linters — run on ONE file. Emit raw `path:line:col: message` lines on stdout.
# Echo the sentinel "__MISSING__" if the linter is unavailable (fail open).
# --------------------------------------------------------------------------- #
lint_file() {
  local lang="$1" f="$2" bin
  case "$lang" in
    python)
      if bin="$(resolve_bin ruff)"; then
        $bin check --quiet --output-format=concise "$f" 2>/dev/null
      else echo "__MISSING__"; fi
      ;;
    js)
      if bin="$(resolve_bin eslint)"; then
        $bin -f unix "$f" 2>/dev/null
      elif command -v npx >/dev/null 2>&1 && npx --no-install eslint --version >/dev/null 2>&1; then
        npx --no-install eslint -f unix "$f" 2>/dev/null
      else echo "__MISSING__"; fi
      ;;
    go)
      if bin="$(resolve_bin golangci-lint)"; then
        $bin run "$f" 2>/dev/null
      else echo "__MISSING__"; fi
      ;;
    rust)
      # clippy operates per-crate, not per-file; only run if a Cargo manifest is
      # reachable. Best-effort, short message format.
      if command -v cargo >/dev/null 2>&1 && cargo clippy --version >/dev/null 2>&1; then
        ( cd "$(dirname "$f")" && cargo clippy --message-format=short 2>&1 )
      else echo "__MISSING__"; fi
      ;;
    *) : ;;
  esac
}

# Normalize raw linter output into the concise report rows the model reads:
#   /path/foo.py:42:5: F841 'x' assigned but never used  ->  "  L42  F841 'x' ..."
normalize_lint() {
  grep -E ':[0-9]+:[0-9]+:' \
    | sed -E 's#^.*:([0-9]+):[0-9]+:[[:space:]]*#  L\1  #' \
    | head -n 25
}

# Fast, warn-only secret/dangerous-call grep (NO heavy SAST). Emits rows or "".
scan_danger() {
  local f="$1"
  grep -nE \
    -e '(eval|exec)[[:space:]]*\(' \
    -e '(AKIA[0-9A-Z]{16})' \
    -e '(secret|password|passwd|api[_-]?key|token)[[:space:]]*[:=][[:space:]]*['\''"][^'\''"]{6,}' \
    "$f" 2>/dev/null \
    | sed -E 's#^([0-9]+):[[:space:]]*#  L\1  #' \
    | head -n 10
}

# --------------------------------------------------------------------------- #
# Emit the PostToolUse JSON result. Both fields optional; prints nothing if both
# are empty (the "clean / skipped" path).
# --------------------------------------------------------------------------- #
emit_post() {
  local sys_msg="$1" ctx="$2"
  [ -z "$sys_msg" ] && [ -z "$ctx" ] && return 0
  jq -n --arg msg "$sys_msg" --arg ctx "$ctx" '
    ( (if $msg != "" then {systemMessage: $msg} else {} end)
      + (if $ctx != "" then {hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}} else {} end) )'
}

# =========================================================================== #
# PER-EDIT TIER  (PostToolUse: Edit|Write|MultiEdit) — non-blocking, exit 0.
# =========================================================================== #
handle_post_tool_use() {
  local file_path
  file_path="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"

  # Not a source file we lint -> exit 0 immediately and silently.
  is_lintable_path "$file_path" || exit 0

  local ext="${file_path##*.}"
  local lang; lang="$(ext_to_lang "$ext")"

  local sys_msg="" ctx=""

  # --- format (in place) ---------------------------------------------------- #
  local fmt; fmt="$(format_file "$lang" "$file_path")"
  if [ "$fmt" = "changed" ]; then
    # Tell Claude to re-read: the file on disk no longer matches its last edit.
    sys_msg="Auto-formatted ${file_path##*/}; re-read the file before editing it again (old_string may be stale)."
  elif [ "$fmt" = "missing" ]; then
    sys_msg="Note: no formatter for $lang found; skipped formatting (fail-open)."
  fi

  # --- lint ----------------------------------------------------------------- #
  local raw; raw="$(lint_file "$lang" "$file_path")"
  if printf '%s' "$raw" | grep -q '__MISSING__'; then
    # Fail open: one short notice, never block.
    local note="Note: $lang linter not installed; skipped linting (fail-open)."
    sys_msg="${sys_msg:+$sys_msg }$note"
  else
    local report; report="$(printf '%s' "$raw" | normalize_lint)"
    if [ -n "$report" ]; then
      ctx="Lint failed: $file_path"$'\n'"$report"$'\n'"Fix and re-save."
    fi
  fi

  # --- warn-only danger scan (secrets / eval / exec) ------------------------ #
  local danger; danger="$(scan_danger "$file_path")"
  if [ -n "$danger" ]; then
    local warn="Warning — possible secret / dangerous call in $file_path:"$'\n'"$danger"
    ctx="${ctx:+$ctx$'\n'}$warn"
  fi

  emit_post "$sys_msg" "$ctx"
  exit 0
}

# =========================================================================== #
# COMMIT GATE  (PreToolUse: Bash) — the ONLY hard block (exit 2).
# =========================================================================== #

# Robustly decide whether a Bash command runs `git commit`. Handles && / || / ;
# / | chains and global options (git -C <path> commit, git --no-pager commit).
# Shell aliases cannot be resolved here — see DURABLE ENFORCEMENT NOTE above.
command_has_git_commit() {
  local cmd="$1" seg
  # Break the command into segments on shell separators.
  while IFS= read -r seg; do
    local found_git=0 skip_next=0 tok
    for tok in $seg; do
      if [ "$skip_next" = "1" ]; then skip_next=0; continue; fi
      if [ "$found_git" = "0" ]; then
        [ "$tok" = "git" ] && found_git=1
        continue
      fi
      case "$tok" in
        -C|-c|--git-dir|--work-tree|--namespace|--exec-path)
          skip_next=1 ;;                       # this global option takes a value
        --*=*|-p|--paginate|--no-pager|--bare|--no-replace-objects|--literal-pathspecs)
          : ;;                                  # value-less global option, skip
        -*)
          : ;;                                  # other flag, skip
        commit)
          return 0 ;;                           # git ... commit  -> match
        *)
          found_git=0 ;;                         # some other subcommand, reset
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

  # Only the `git commit` case is gated. Everything else: allow, do nothing.
  command_has_git_commit "$command" || exit 0

  # Lint the staged source files only.
  local staged
  staged="$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null)"

  local error_files="" error_count=0
  local rel abs lang raw report
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    abs="$REPO_ROOT/$rel"
    is_lintable_path "$abs" || continue
    lang="$(ext_to_lang "${abs##*.}")"
    raw="$(lint_file "$lang" "$abs")"
    # Missing linter => fail open (do not count as error, do not block).
    printf '%s' "$raw" | grep -q '__MISSING__' && continue
    report="$(printf '%s' "$raw" | normalize_lint)"
    if [ -n "$report" ]; then
      error_count=$((error_count + 1))
      error_files="${error_files:+$error_files, }$rel"
    fi
  done <<EOF
$staged
EOF

  if [ "$error_count" -gt 0 ]; then
    echo "Commit blocked — $error_count lint error(s) in $error_files. Fix, then commit." >&2
    exit 2
  fi
  exit 0
}

# =========================================================================== #
# Branch on the event. Unknown events: do nothing, exit 0.
# =========================================================================== #
case "$EVENT" in
  PostToolUse) handle_post_tool_use ;;
  PreToolUse)  handle_pre_tool_use  ;;
  *)           exit 0 ;;
esac
