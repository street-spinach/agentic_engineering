# agentic_eng

## Workflow (gates)

1. Spec: /spec-interviewer -> /harden-spec must stamp SPEC.md before any code.
2. Per slice: implement -> lint+tests -> /code-review (must APPROVE) -> /auto-commit.
   This local loop runs autonomously: code-review <-> coder-fix repeats (bounded)
   until APPROVE, then /auto-commit commits locally without prompting. It halts and
   asks only on a hard stop (secrets, out-of-scope files, protected branch), if the
   review doesn't converge, or at push/PR/merge (always explicit).
   Tests are split: while implementing, the coder writes only a couple of smoke
   tests for the unit it is building (to confirm intent), following the
   unit-testing skills' conventions — never full coverage. Delegate complete
   behavioral coverage to the `unit-test-generator` subagent before /code-review;
   do not hand-write exhaustive edge/negative/state tests in the main loop.
3. Never commit unreviewed or lint-failing code; never push or open a PR unless asked.
4. PR: push -> /code-review (PR mode) -> fix findings -> ready for merge (human merges).
5. Backfill (safety net): a local pre-push hook runs /test-backfill on `git push` —
   it scopes to code new since the last marker (never the whole history), delegates
   coverage gaps to the `unit-test-generator`, validates via the test-runner, and
   opens a PR with the added tests for human review + merge.

Test-runner hook results route as: A -> coder fixes code; B -> unit-test-generator
fixes the test; C -> report, don't hard-block; missing core coverage -> back to the
generator. No commit with failing tests on core logic.

Rules for each step live in that skill/subagent — don't restate them here.
