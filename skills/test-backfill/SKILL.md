---
name: test-backfill
description: Recurring safety-net that completes missing unit tests for RECENTLY committed code only — never the whole history. Scopes to commits new since a marker (the git tag test-backfill/last), delegates each coverage gap to the unit-test-generator subagent, validates the result via the test-runner hook, then opens a PR with the added tests for human review. Advances the marker on success. Intended to run headless from CI on push; also runnable by hand. Never merges, never scans the whole repo, never reimplements the generator's judgment.
---

# Test Backfill

## Purpose

Per-slice, the coder delegates full coverage to the `unit-test-generator` before
review. Things still slip through — a slice committed in a hurry, a gate skipped.
`/test-backfill` is the **safety net** that catches those: on each push it looks
at **only the code committed since the last backfill**, fills the missing tests,
and opens a PR. It is the test-coverage analog of the lint hook — a deterministic
trigger wrapping an LLM judgment — but it runs at the push boundary, not per edit.

It **orchestrates**; it does not re-judge. Coverage decisions belong to the
`unit-test-generator` and the `unit-testing` skills (single source of truth);
execution belongs to the `test-runner` hook. This skill only scopes the work,
delegates it, and packages the result as a PR.

## When to Use

- **Local pre-push hook** — the primary trigger (see the
  `hooks/pre-push-test-backfill.sh` template). On `git push` it fires on your
  machine, scoped to the pushed commits, and runs this skill in the background
  inside a throwaway worktree — so your push isn't blocked and your working tree
  isn't disturbed.
- **By hand** — when you want to sweep recent commits for coverage gaps before a PR.

Skip it when there are no new commits since the marker — "nothing recent to backfill."

## Scope — the marker (recent code only)

The marker is the git tag **`test-backfill/last`**, pointing at the last commit
already backfilled. Scope is always `test-backfill/last..HEAD` — never the whole
history.

- **No marker yet (first run)** — do **not** scan the repo. Scope to only the
  pushed commits: the hook passes `BACKFILL_PREV..BACKFILL_BASE` env hints (the
  old and new tips of the pushed branch); use `BACKFILL_PREV..BACKFILL_BASE`, or
  just `BACKFILL_BASE`'s own new commits when `BACKFILL_PREV` is empty (a brand-new
  branch). The history before the first run is intentionally left alone.
- **Advance on success** — move `test-backfill/last` to `HEAD` only after tests
  are generated and validated. Caveat: the marker advances at **generation** time,
  not at PR-merge time. If you close a backfill PR unmerged, those tests are lost
  and won't regenerate — re-run `/test-backfill` by hand, or reset the marker
  (`git tag -f test-backfill/last <older-sha>`).

## Workflow

1. **Compute scope.** `git diff <marker>..HEAD --name-only`, keeping only source
   files (skip the marker-absent case per *Scope*). If empty, stop — nothing recent.
2. **Resolve packages.** Group the changed files by nearest manifest, exactly as
   the generator does — resolve per package in a monorepo.
3. **Delegate to the generator.** Invoke the `unit-test-generator` subagent (Task
   tool, or `@unit-test-generator`) on the changed units. It classifies, picks the
   stack skill, and writes only the tests that are warranted — including writing
   none, with reasons. You do **not** decide coverage here.
4. **Validate.** The `test-runner` hook fires on the subagent finishing
   (SubagentStop) and again at the commit gate. Route its result: tag A → flag for
   the coder (code bug, do **not** commit); tag B → hand back to the generator to
   fix the test; tag C → report, don't block.
5. **Commit locally on a branch.** On the feature branch the run is on
   (`test-backfill/<short-sha>`), run **`/auto-commit`** (auto mode) — it stages
   only the vetted test files, scans for secrets, and makes a **local** commit.
   The test-runner commit gate validates here. **Stop at the local commit** — do
   not push or open the PR yourself.
6. **Hand off push + PR + marker to deterministic steps.** Pushing the branch,
   opening the PR, and advancing the `test-backfill/last` tag are git-ref *writes*,
   not judgment — the pre-push hook's background runner (plain shell) does them, so
   they never route through Claude's `git push` permission and your `settings.json`
   stays untouched. Run by hand, you push + `gh pr create` + move the tag yourself.
7. **Report** (format below). Recommend `/code-review` (PR mode) on the new PR.

## Hard Rules

- **Recent only.** Scope is always marker-bounded. Never scan or backfill the
  whole history.
- **Don't re-judge.** Coverage depth, classification, and stack idioms come from
  the `unit-test-generator` + `unit-testing` skills. This skill never writes tests
  itself and never weakens the policy.
- **Tests only.** The generator writes test files, never production code. A tag-A
  failure (real code bug) is **reported, not patched** — that's the coder's job.
- **Never merge; never commit to `main`.** Always a feature branch + PR; a human
  reviews and merges. Reuse `/auto-commit` (auto mode) for the local commit's
  staging + secret scan — don't reimplement it, and don't push from the skill.
- **Push, PR, and marker writes stay deterministic.** They live in the pre-push
  hook's runner (plain shell), not in Claude — so the skill needs no relaxed
  `git push` permission and `settings.json` is never modified.
- **Never bypass gates.** No `--no-verify`; the test-runner commit gate must pass
  (tag-A/B failures block the commit just as in a normal slice).

## Output

```markdown
# Test Backfill Report

## Scope
Commits <marker>..HEAD — N files across M package(s). (Or: nothing recent.)

## Tests added
file → behavior pinned down (from the generator's report).

## Deliberately skipped
What the generator chose not to test, and why.

## Test-runner result
Pass / fail counts; any A/B/C failures and how they were routed.

## PR
Branch + PR link, or why no PR was opened.

## Marker
test-backfill/last advanced to <sha> (or held, with reason).
```

## Failure Behavior

- **No marker + first run** → set the marker, backfill only the pushed range, say so.
- **Nothing recent** → "nothing to backfill," exit cleanly, marker unchanged.
- **Tag-A failure (real bug)** → stop before commit, report it for the coder; do
  not open a PR of tests that encode a bug.
- **Tag-C (couldn't run)** → report, leave the marker unadvanced so the next run
  retries the same scope.
- **No local commit produced** (generator wrote nothing, or a gate blocked it) →
  the hook runner's push/PR/marker steps no-op; report why and hold the marker.
