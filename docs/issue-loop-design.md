# Issue-Loop — Design Brief

**Status:** design locked, pre-implementation. Captures an autonomous issue-fixing
loop that wraps the existing spec → build → review → commit machinery with
GitHub-issue ingestion and an adaptive deploy → verify stage. Not yet built.

## Problem

Today the workflow starts from a human-authored `SPEC.md`. We want a second entry
point: read open GitHub issues and autonomously fix → unit-test → integration-test
→ deploy → verify-the-deployed-surface → next issue. Incremental and vertical per
issue — never a waterfall where everything is fixed and only then tested. The loop
runs hands-off through staging and stops only before a production release.

## Goals

- Drive fixes directly from GitHub issues labelled `agent-ready`.
- Reuse the existing per-slice inner build loop essentially unchanged.
- Add a deploy + post-deploy verification gate that exercises the *actually
  deployed* surface, scoped to what changed.
- Run autonomously through staging; one human gate at production.

## Non-goals

- Ephemeral preview envs + a merge queue (the higher-infra path to fully parallel
  integration). The opt-in worktree parallel mode fans out the fix phase without
  them; the integration lane stays serial.
- Replacing `spec-interviewer` / `harden-spec` / `plan-slices` — these are reused.
- Automating the production release — that stays human-gated.

## Triage routing

Triage assigns each issue a **type** (bug vs feature/other) and a **complexity**
(low/med/high) from the issue text and affected scope, then routes:

| Type            | Complexity   | Path                                    |
|-----------------|--------------|-----------------------------------------|
| Bug             | low / medium | → implement (skip spec)                 |
| Bug             | high         | → spec → harden → implement             |
| Feature / other | low          | → spec → implement (skip harden)        |
| Feature / other | medium/high  | → spec → harden → implement             |

Gate rules: the **spec gate** is skipped only for low/medium bugs; the **harden
gate** fires whenever complexity is medium or high. **Park** is orthogonal — if
triage can't classify an issue well enough to spec it, it is labelled
`needs-human`, skipped, and the loop continues.

## Control flow

1. Fetch open `agent-ready` issues via `gh`; order by dependency links then
   priority label; process sequentially.
2. **Triage & route** per the table above. Spec, when needed, is derived from the
   issue text + comments (no live interview); `harden-spec` runs goldfish ×3. If
   readiness can't be reached from the text, the issue is parked.
3. **Inner build loop (existing):** implement · `unit-test-generator` ·
   lint+test hooks **+ integration tests (testcontainers)** · `code-verifier`
   APPROVE · `auto-commit`.
4. **Classify + surface check (from diff):** the model infers whether the change
   exposes an observable interface.
   - **No surface** (internal/refactor): gate on unit + integration, merge, next.
   - **Has surface:** continue.
5. **Merge-first:** open PR and merge to `main` on a green inner loop.
6. **Deploy `main` → shared staging:** backend (api/bff/agent) deploys the service;
   an app change builds and installs on an emulator.
7. **Verify deployed surface (diff-scoped, model-inferred):** backend → Postman /
   Newman against the changed endpoints; app → `android/ios/persona` app-testing
   skills against the changed screens.
8. **Verify gate:** green → comment results + `verified` label + close issue →
   next. Red → revert `main` + redeploy + fix (re-enter the inner loop), iterate
   until green.
9. **Circuit breaker:** after **3** failed verify cycles on one issue, halt the run
   with `main` reverted to a green state, post the accumulated logs to the issue,
   and surface to a human.
10. **Outer loop** repeats until the queue is empty and every issue is verified.
11. **Production release** is batched and human-gated — the only stop point.

## Components

**New (to build):** `/issue-loop` (outer orchestrator + circuit-breaker
bookkeeping), `/issue-triage` (type + complexity routing), `/deploy` (adaptive
backend/app deploy + the diff → surface classify step), `/post-deploy-verify`
orchestrates scoped Newman / app-test evidence), and a new fresh-eyes subagent
**`deploy-verifier`** that judges the deployed surface against the issue's
acceptance — the `code-verifier` pattern, one layer out. Plus wiring: a CLAUDE.md front-door
entry ("issue intent → `/issue-loop`") and the plugin manifest update.

**Reused unchanged:** `spec-interviewer`, `harden-spec`, `goldfish-spec-reviewer`,
`plan-slices`, `unit-test-generator`, `code-verifier`, `code-reviewer`,
`auto-commit`, the lint/test hooks, and the `android/ios/persona` app-testing
skills. The only inner-loop addition is integration tests (testcontainers) in the
existing test stage, for changes that warrant them.

## Failure & safety

- Verify red → revert `main` + redeploy + fix, iterate until green.
- Circuit breaker at 3 failed cycles → halt, `main` green, logs posted, human
  surfaced (the escape hatch for non-convergent issues, since the queue is
  sequential and would otherwise stall).
- Hard-stops always halt regardless of autonomy: secrets, a direct commit to a
  protected branch, out-of-scope files.
- Push / PR / merge / staging-deploy are authorised by the loop itself; only the
  production release is interactive.
- Re-runs are idempotent — closed and `verified` issues are skipped, so the loop is
  resumable and can later become a scheduled task.

## Efficiency & scaling (optional)

- **Context health.** Heavy reads (triage's issue + linked-code scan, the
  verifiers' log reading) run inside subagents, whose intermediate tokens never
  enter the orchestrator's window; the loop `/compact`s at each issue boundary. The
  orchestrator carries only verdicts + `TASKS.md` / issue state — never N issues'
  worth of context.
- **Telemetry.** Claude Code's native OpenTelemetry (see `observability/`) exports
  token + cost by model and the cache-read/creation split to a local Collector →
  Prometheus → Grafana stack; `hooks/cache-meter.sh` stays as the inline per-turn
  signal. Session-scoped per-issue cost makes model tiering and the parallel-mode
  decision evidence-based.
- **Parallel mode (worktrees).** A concurrency dial `N` (default 1 = sequential):
  the fix phase fans out across worktree-isolated workers; merge → deploy → verify
  stays serial (shared `main` + staging). See the issue-loop skill's Parallel mode.

## Verification (how we'll know the loop works)

- Dry-run on a seeded test repo with a mix of issues (low/med/high bug + feature)
  → routing matches the table.
- A surface-changing bug → merges, deploys, Newman verifies the changed endpoint,
  issue closes with results commented.
- A deliberately non-convergent issue → circuit breaker halts after 3 cycles with
  `main` left green.
- An internal-only refactor → merges via unit + integration, deploy skipped.

## Open items (need project specifics at build time)

- The staging deploy command per stack — `/deploy` needs the project's deploy
  entrypoint(s) for backend services and the app build/install command.
- Newman collection location; diff → request mapping is inferred at runtime, with a
  path → surface manifest as a fallback if inference mis-scopes.
- Complexity thresholds (low/med/high) — calibrate against real issues.
