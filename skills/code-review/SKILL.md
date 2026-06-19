---
name: Code Review
description: Orchestrates a fresh-eyes code review via the `code-reviewer` subagent, in local or PR mode. Gathers the diff (and for PRs the comments, CI checks, and test output), runs the subagent against the Goldfish-verified SPEC.md, consolidates findings into a report with an APPROVE / CHANGES REQUESTED verdict, and gates the next step. On APPROVE (local) it triggers /auto-commit; on CHANGES REQUESTED it returns findings and stops. Never fixes code itself; never pushes or posts to a PR unless explicitly asked.
---

# Code Review

## Purpose

`/code-review` is the **code-level review gate** — the `harden-spec` analog one
layer down. Where `/harden-spec` pressure-tests `SPEC.md` with a fresh Goldfish,
`/code-review` pressure-tests the **diff** with a fresh `code-reviewer` subagent.

It is the second of three independent gates on each commit: the **lint hook**
(mechanical, deterministic) → **code review** (semantic, fresh-eyes LLM) →
**auto-commit** (scope / secret / curation). Each gate owns its lane and does not
do another's job. This skill owns the semantic lane.

A review the author runs in its own coding context rationalizes its own choices.
The `code-reviewer` subagent has **no memory** of that conversation, so it judges
the change on its merits against the verified spec. You orchestrate it; you do not
review the code yourself, and you do not fix it.

## When to Use

- **Local mode** — after a slice's lint + tests pass and **before** the commit.
- **PR mode** — after a branch is pushed and a PR exists.

Skip it if there are no changes — "nothing to review."

## Mode Detection

- **Local** — review the working-tree `git diff`.
- **PR** — review `gh pr diff` plus the PR description, `gh pr view` comments,
  `gh pr checks` (CI), and the test output.

Auto-detect the mode, or accept an explicit mode / PR number from the user.

## Workflow

1. **Determine mode and scope.** Local working tree, or PR #N.
2. **Confirm the spec is verified.** `SPEC.md` must exist and carry
   `<!-- VERIFIED by GOLDFISH -->`. If it is missing or unverified, **stop** and
   point to `/harden-spec` — review judges the diff against a *verified* spec.
3. **Gather inputs.** Run/read lint + tests. Local → `git diff`. PR → `gh pr diff`,
   the PR description and comments, `gh pr checks`, and test results.
4. **Invoke the `code-reviewer` subagent by name** (Task tool, or
   `@code-reviewer`), telling it the **mode** and **what** to review. Hand it **no
   code from chat** — it reads the diff itself. Use **deep mode** (multiple lens
   passes) only for large or high-risk changes. For high-risk security surface,
   **additionally** invoke the existing **`security-review`** skill — do not
   re-implement a deep scan here.
5. **Consolidate** the findings into a **Code Review Report** (format below).
6. **Decide the verdict** — `APPROVE` (no blocking findings) or
   `CHANGES REQUESTED` (≥ 1 blocking finding).
7. **Route on the verdict** (see *Routing*).

## Routing

- **CHANGES REQUESTED (local)** → the coder applies the blocking fixes and this
  skill **re-runs automatically** (a fresh subagent each round) **without prompting
  you**. Bound the loop to **3 rounds**; if it still has not reached `APPROVE`,
  **stop and hand the outstanding findings back to you** — do not keep looping or
  commit. Recommended / Nits are logged as follow-ups; they never block or extend
  the loop.
- **APPROVE (local)** → **automatically trigger `/auto-commit`**, which commits
  locally without a prompt. If the auto-commit skill is not present yet, stop at
  **"ready to commit"** instead.
- **APPROVE (PR)** → report **"ready for merge."** Posting a PR review
  (`gh pr review --approve` / `--request-changes` / `--comment`) is a **remote
  write** — do it **only when explicitly asked**. Merge is **always** a human action.

## Hard Rules

- **Review only a Goldfish-verified diff.** No `<!-- VERIFIED by GOLDFISH -->`,
  no review — point to `/harden-spec`.
- **Never fix code.** The coder fixes; the subagent and this skill return findings.
- **A blocking verdict cannot be bypassed.** `APPROVE` is required before
  `/auto-commit`.
- **Never push, post to a PR, or merge unless explicitly requested.**
- **Do not duplicate lint or spec verification** — the hook and the Goldfish own
  those lanes. Reuse **`security-review`** for security depth.

## Code Review Report Format

```markdown
# Code Review Report

## Verdict
APPROVE or CHANGES REQUESTED — one-line reason.

## Summary of change
What the diff does, in plain English.

## Blocking findings
file:line — what — why — suggested direction. (Must be empty to APPROVE.)

## Recommended
Should-fix findings that do not block.

## Nits
Minor; safe to defer.

## Test assessment
Whether the new behavior has real coverage, edge cases included. Name the gaps.

## Architecture alignment
Whether the change fits SPEC.md's plan, or drifts into a rejected alternative.

## Follow-ups
Recommended / Nits logged as non-blocking work.

## Next step
/auto-commit (local APPROVE) · ready for merge (PR APPROVE) · return to coder
(CHANGES REQUESTED).
```

## Failure Behavior

- **No changes** → "nothing to review," exit cleanly.
- **`SPEC.md` missing or unverified** → stop, point to `/harden-spec`.
- **`gh` missing or unauthenticated** (PR mode) → explain, skip the PR signals,
  review the diff only.
- **CI red** (PR mode) → surface as a **blocking finding**.
