# Engineering Process Charter

This document holds the persistent rules and is loaded every session (via
CLAUDE.md or a skill). Per-cycle instructions live in `PROMPT.md`; scheduling,
budgets, and the billing preflight live in `run-loop.sh` — a prompt cannot
check billing before running, because reading the prompt is already a billed
request. The outer loop owns overall completion and quality; the inner loop
owns correct implementation and validation of each issue; the harness owns
scheduling, budgets, and the billing route.

## 0. Billing & environment preconditions

- This process runs only on the official Claude Code CLI under subscription
  billing. `run-loop.sh` refuses to start if any API-routing variable is set:
  `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`,
  `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`.
- Agent-side backstop: the first action of every session is the billing check
  in `PROMPT.md` step 0. On any match, report `BILLING-ROUTE VIOLATION`, do no
  work, and stop. Never unset the variable yourself — halt and surface.
- Rate limits are handled by the harness: on a rate/usage-limit error it
  sleeps and resumes, and a rate-limited cycle never counts against any
  failure budget. If a limit hits mid-session, checkpoint state to the issue
  (or TASKS.md) and stop cleanly rather than thrash.

## 1. Specification

- Develop and refine the spec with `/spec-interviewer` (plus `/harden-spec`
  when triage routes there). A human approves the spec before planning.

## 2. Planning → issues

- Convert the approved spec into small, independently deliverable slices
  (`/plan-slices`). Log each slice as a GitHub issue containing scope,
  acceptance criteria, dependencies, and test expectations; label it
  `agent-ready` plus a priority label. A human approves the issue set before
  the loop starts. Prefer small verifiable slices over broad batches.

## 3. Outer loop — owns overall completion and quality

- Done means `./verify.sh` exits 0, which requires all of: zero open
  `agent-ready` issues (`gh issue list --label agent-ready --state open`
  returns none — this replaces the PLAN.md predicate), lint, typecheck, unit
  tests, build, functional/e2e where applicable, and a clean committed tree.
  `blocked` issues stay open and keep the gate red by design: completion of a
  blocked slice requires a human, not more iterations.
- Exactly one issue per iteration, then stop; the harness starts the next
  iteration in a fresh session. Order by dependency first, then priority;
  skip `verified` and `blocked`.
- All cross-iteration state lives on disk and GitHub (issue comments,
  TASKS.md, commits) — never in conversation memory.

## 4. Inner loop — owns correct implementation of each issue

- Delegate, don't reimplement: `/issue-triage` routes
  (`implement | spec | spec+harden | park`; park → skip) → spec path if
  routed → read the issue, spec, architecture, and existing code → implement
  → `unit-test-generator` → lint + test-runner hooks including integration →
  `/code-verifier` must APPROVE → `/auto-commit` → merge-first → `/deploy`
  classifies the surface → `/post-deploy-verify` for surface-changing issues.
- Add or update tests proportionate to business and technical risk. Fix
  failures and iterate until acceptance criteria are met. "This and no more":
  extra ideas become new issues, not scope creep.
- Update the issue with implementation notes, test results, risks, and
  follow-ups before closing.

## 5. Verification — who decides what

- Mechanical gates: a gate passes only when its designated command exits 0
  (hooks, `./verify.sh`, CI). Never conclude "tests pass" from reading code,
  from memory of an earlier run, or from intent — re-run the command.
- Judgment gates: fresh-eyes subagents decide, never the implementing
  session. `code-verifier` judges the diff against the spec pre-merge;
  `deploy-verifier` judges the deployed surface against the issue's
  acceptance post-deploy.
- Close an issue only after mechanical green AND the required judgment PASS,
  then comment the evidence and add the `verified` label.

## 6. Failure budgets

- Circuit breaker: after 3 failed verify cycles on one issue — revert `main`
  to green, post the accumulated logs to the issue, label it `blocked`, halt
  the run, and surface a human. Park or surface; never silently stall.
- Harness budgets: `MAX_ITERS` total iterations; `STALL_LIMIT` consecutive
  iterations producing no new commit → halt for human review.
- A rate-limit wait is not a failure and consumes no budget (§0).

## 7. Integrity — non-negotiable

- Never modify `verify.sh`, CI config, or hooks, and never weaken, skip, or
  delete tests to make a gate pass. Fix product code or escalate; `verify.sh`
  fails itself if tampered with.
- Never bypass gates with `--no-verify` or a force-push; `/auto-commit`
  hard-stops (secrets, protected branch, out-of-scope files) always apply.
- Autonomy boundary: push, PR, merge, and staging deploy are autonomous.
  Production release is human-gated, always.
