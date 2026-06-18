# agentic_eng

## Workflow (gates)

1. Spec: /spec-interviewer -> /harden-spec must stamp SPEC.md before any code.
2. Per slice: implement -> lint+tests -> /code-review (must APPROVE) -> /auto-commit.
   When a slice changes testable logic, delegate test generation to the
   `unit-test-generator` subagent before /code-review.
3. Never commit unreviewed or lint-failing code; never push or open a PR unless asked.
4. PR: push -> /code-review (PR mode) -> fix findings -> ready for merge (human merges).

Test-runner hook results route as: A -> coder fixes code; B -> unit-test-generator
fixes the test; C -> report, don't hard-block; missing core coverage -> back to the
generator. No commit with failing tests on core logic.

Rules for each step live in that skill/subagent — don't restate them here.
