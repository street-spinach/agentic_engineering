# agentic_eng

## Workflow (gates)

0. Front door (new intent): triage before anything else. Just messy wording ->
   /prompt-enhancer to sharpen it. Unclear scope/requirements -> /spec-interviewer.
   Already sharp (and SPEC verified) -> proceed. Run /prompt-enhancer before spec or
   implementation whenever only the wording needs work. Working the GitHub issue
   backlog (fix open bugs/issues) -> /issue-loop: it triages/routes each issue,
   reuses this same per-slice loop, and adds a merge -> deploy -> verify gate;
   autonomous through staging, production stays human-gated.
1. Spec: /spec-interviewer -> /harden-spec must stamp SPEC.md before any code.
   After /harden-spec PASS -> /plan-slices produces TASKS.md -> work slices from
   TASKS.md (plan -> implement -> checks -> review -> fix -> commit; testing inside
   each slice). Keep TASKS.md current; preserve existing behavior unless SPEC
   requires a change. SPEC.md and TASKS.md are ephemeral working memory —
   gitignored, never committed (durable knowledge is distilled at step 6).
2. Per slice: implement -> lint+tests -> /code-verifier (must APPROVE) -> /auto-commit.
   This local loop runs autonomously: code-verifier <-> coder-fix repeats (bounded)
   until APPROVE, then /auto-commit commits locally without prompting. It halts and
   asks only on a hard stop (secrets, out-of-scope files, protected branch), if the
   verification doesn't converge, or at push/PR/merge (always explicit).
   Tests are split: while implementing, the coder writes only a couple of smoke
   tests for the unit it is building (to confirm intent), following the
   unit-testing skills' conventions — never full coverage. Delegate complete
   behavioral coverage to the `unit-test-generator` subagent before /code-verifier;
   do not hand-write exhaustive edge/negative/state tests in the main loop.
   After /auto-commit at a slice boundary, run /compact — TASKS.md and SPEC.md
   rehydrate the next slice.
3. Never commit unreviewed or lint-failing code; never push or open a PR unless asked.
4. PR: push -> /code-verifier (PR mode) -> fix findings -> ready for merge (human merges).
5. Backfill (safety net): a local pre-push hook runs /test-backfill on `git push` —
   it scopes to code new since the last marker (never the whole history), delegates
   coverage gaps to the `unit-test-generator`, validates via the test-runner, and
   opens a PR with the added tests for human review + merge.
6. Distill (on feature completion): when all TASKS.md slices are done and SPEC.md's
   Verification passes, run /distill-spec -> lift Decisions + rejected alternatives
   into docs/adr/NNNN (immutable) and refresh ARCHITECTURE.md (current-state); both
   are committed. SPEC.md/TASKS.md are then discarded. New work reads ARCHITECTURE.md
   + docs/adr/ for the "why", not old specs.

Test-runner hook results route as: A -> coder fixes code; B -> unit-test-generator
fixes the test; C -> report, don't hard-block; missing core coverage -> back to the
generator. No commit with failing tests on core logic.

## Context health

Keep the active window high-signal (fight context rot: stale tool output, superseded
plans, resolved errors dilute attention long before the token limit). Durable state
lives outside the window (SPEC.md, TASKS.md, ARCHITECTURE.md/ADRs, issue state);
heavy reads run in subagents (only the verdict returns); the thread holds pointers,
not payloads. Compact at seams, proactively — never lean on reactive auto-compact.
Seams: each slice/issue close (after /auto-commit), and after harden (spec frozen)
and code-verifier APPROVE (diff frozen). If mid-unit context passes ~60% off a seam,
checkpoint to TASKS.md and compact early. Full strategy: docs/context-management.md.

### Compact Instructions
When compacting, ALWAYS preserve: the TASKS.md pointer + the current slice/issue and
its acceptance criteria; the list of modified files; open review/verify findings;
and any decision not yet written to SPEC.md or an ADR. DROP: resolved errors,
superseded plans, old diffs, exploratory dead-ends. Never compact across a gate
whose verdict has not been recorded to durable memory first.

Rules for each step live in that skill/subagent — don't restate them here.
