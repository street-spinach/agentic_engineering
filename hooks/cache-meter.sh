#!/usr/bin/env bash
#
# cache-meter.sh — deterministic prompt-cache measurement hook for Claude Code.
#
# The MEASUREMENT complement to the lint/test hooks. Like them it NEVER calls a
# model and NEVER judges intent — it only reads numbers Claude Code already wrote
# to the session transcript and reports them deterministically. "You can't tune
# what you don't watch": this turns the /cost habit into a mechanism.
#
# WIRING (in .claude/settings.json — Stop fires at the end of each turn/session):
#
#   "Stop": [ { "hooks": [ { "type": "command",
#       "command": "\"$CLAUDE_PROJECT_DIR/hooks/cache-meter.sh\"", "timeout": 15 } ] } ]
#
#   (Optional) add the same under "SubagentStop" to meter subagent runs too.
#
# WHAT IT DOES
#   Reads the hook JSON on stdin, finds `transcript_path`, streams the JSONL, and
#   sums the token usage every assistant turn records under `message.usage`:
#       cache_read_input_tokens      — served from cache (cheap)
#       cache_creation_input_tokens  — written to cache (one-time premium)
#       input_tokens                 — fresh, uncached input
#       output_tokens                — generated
#   Then it computes the read-rate = cache_read / (cache_read + cache_creation +
#   input) — the share of prompt-side tokens served from cache — appends one
#   record to the metrics log, and surfaces a one-line summary.
#
# DESIGN INVARIANTS (same spirit as lint-dispatch.sh / test-runner.sh)
#   * NEVER calls a model; pure arithmetic over the transcript.
#   * NEVER blocks — measurement is not a gate. ALWAYS exit 0.
#   * Fail OPEN: no jq, no transcript, or no usage yet => one short notice, exit 0.
#   * Read-only except for appending to the metrics log.
#
# MANUAL / TEST USE
#   Pass a transcript path as $1 instead of piping hook JSON:
#       ./hooks/cache-meter.sh /path/to/session.jsonl
#
# CONFIG
#   CACHE_METER_LOG   override the log path (default: $CLAUDE_PROJECT_DIR/.cache-metrics.log)
#   Add that file to .gitignore — it is local telemetry, not source.

set -u

note() { printf 'cache-meter: %s\n' "$1" >&2; exit 0; }

command -v jq >/dev/null 2>&1 || note "jq not found; skipping (fail-open)."

# --- inputs: hook JSON on stdin, or a transcript path as $1 for manual runs ---
# Guard against a blocking read: only consume stdin when it is NOT a terminal
# (a real hook pipes JSON and closes stdin, so cat returns immediately).
if [ -t 0 ]; then INPUT=""; else INPUT="$(cat 2>/dev/null || true)"; fi
TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null || true)"
EVENT="$(printf '%s'  "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null || true)"
SESSION="$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)"
# SubagentStop hands the subagent's own transcript under a different key:
[ -z "$TRANSCRIPT" ] && TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.agent_transcript_path // empty' 2>/dev/null || true)"
# manual/test fallback
[ -z "$TRANSCRIPT" ] && [ -n "${1:-}" ] && TRANSCRIPT="$1"

[ -n "$TRANSCRIPT" ] || note "no transcript_path in hook input; nothing to measure."
[ -r "$TRANSCRIPT" ] || note "transcript not readable ($TRANSCRIPT); skipping."

# --- sum usage across every assistant turn (streamed; memory-friendly) --------
STATS="$(jq -n '
  ( reduce inputs as $x ( {i:0, r:0, c:0, o:0};
      if ($x.type == "assistant") and ($x.message.usage != null) then
          .i += ($x.message.usage.input_tokens            // 0)
        | .r += ($x.message.usage.cache_read_input_tokens  // 0)
        | .c += ($x.message.usage.cache_creation_input_tokens // 0)
        | .o += ($x.message.usage.output_tokens            // 0)
      else . end ) ) as $t
  | ($t.i + $t.r + $t.c) as $p
  | { input:$t.i, read:$t.r, created:$t.c, output:$t.o, prompt:$p,
      rate: (if $p > 0 then (1000 * $t.r / $p | floor) / 10 else 0 end) }
' < "$TRANSCRIPT" 2>/dev/null || true)"

[ -n "$STATS" ] || note "could not parse transcript as JSONL; skipping."

READ=$(printf '%s' "$STATS"      | jq -r '.read')
CREATED=$(printf '%s' "$STATS"   | jq -r '.created')
INPUT_T=$(printf '%s' "$STATS"   | jq -r '.input')
OUTPUT_T=$(printf '%s' "$STATS"  | jq -r '.output')
PROMPT=$(printf '%s' "$STATS"    | jq -r '.prompt')
RATE=$(printf '%s' "$STATS"      | jq -r '.rate')

[ "$PROMPT" -gt 0 ] 2>/dev/null || note "no token usage recorded in this transcript yet."

SUMMARY="prompt-cache: read ${READ} · created ${CREATED} · fresh ${INPUT_T} · output ${OUTPUT_T} · read-rate ${RATE}% (of ${PROMPT} prompt tokens)"

# --- append one record to the local metrics log -------------------------------
LOG="${CACHE_METER_LOG:-${CLAUDE_PROJECT_DIR:-.}/.cache-metrics.log}"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
printf '%s\tsession=%s\tevent=%s\tread=%s\tcreated=%s\tinput=%s\toutput=%s\tprompt=%s\tread_rate=%s%%\n' \
  "$TS" "${SESSION:-?}" "${EVENT:-manual}" "$READ" "$CREATED" "$INPUT_T" "$OUTPUT_T" "$PROMPT" "$RATE" \
  >> "$LOG" 2>/dev/null || true

# --- surface the summary ------------------------------------------------------
# As a real hook, emit a systemMessage (valid JSON, non-blocking). Manually, print plain.
if [ -n "$EVENT" ]; then
  printf '{"systemMessage": %s}\n' "$(printf '%s' "$SUMMARY" | jq -Rs .)"
else
  printf '%s\n' "$SUMMARY"
fi
exit 0
