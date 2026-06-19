---
name: Auto Commit
description: Prepare and create a clean git commit after a coding task — survey the diff, classify changes against the task scope, scan for secrets, run configured lint/tests, then write a conventional-commit message and stage only vetted files. The curator at the door of version control. Guarantees — stages only specific vetted files (never `git add .`/`-A`), hard-stops on secrets, defaults to a local commit, and never pushes, opens a PR, or uses `--no-verify` unless explicitly asked. Optional `gh` PR creation only on request.
---

# Auto Commit

## Purpose

Auto Commit is the curator at the door of version control — the third gate after the Goldfish spec gate (is the plan sound?) and the lint hook (is the code mechanically clean?). It asks: is this change set clean, scoped, safe, and well-described before it enters history? Everything up to `git commit` is local and reversible, so the default endpoint is a **local commit**. Push and PR cross into shared space and are **always explicit, separate steps** — never automatic.

## When to Use

- A task's changes are complete and lint/tests pass.
- The user asks to commit, save, or check in the work.

Skip it if there are no changes, or if checks are still failing — fix those first.

## Task Context

Derive the intended scope from `SPEC.md` (if present) plus the conversation about what was just built. Map the diff against that scope. If the scope is unclear and the diff is ambiguous, **ask** — never guess what belongs in the commit.

## Hard Rules

- **Stage only specific, vetted files** — `git add <path> ...`. Never `git add .` or `-A`, even though `settings.local.json` permits it.
- **Hard-stop on secrets** — `.env`, credentials, keys, tokens, `*.pem`, `id_rsa`, `*.key`, high-entropy strings. Name the file/pattern, never echo the value.
- **Never commit junk** — logs, build artifacts, temp files. Flag un-ignored junk instead of committing it.
- **Never push or open/merge a PR** unless explicitly requested.
- **Never use `--no-verify`** — it would bypass the lint commit-gate hook. Never amend or force-push pushed history.
- **Never commit directly to a protected branch** (`main`/`master`) — warn and offer to branch first.
- **Don't guess intent** — ask when the change set or purpose is unclear.

## Workflow

Enforce this order.

1. **Survey (read-only).** `git status --short`, `git diff`, `git diff --staged`, `git diff --stat`.
2. **Classify.** Map each changed path to the task. Flag anything unrelated, suspicious, or untracked (`??`).
3. **Safety scan.** Check filenames *and* diff content for secrets/sensitive/junk. Hard-stop on hits; never echo a secret value.
4. **Verify.** Run the configured lint/test commands if present; stop on failure. If none are configured, say so — "no checks configured."
5. **Compose.** Write a conventional-commit message derived from the *actual* diff. If the diff spans multiple concerns, propose splitting into atomic commits.
6. **Stage precisely.** `git add <specific files>` — vetted only, never `.` or `-A`.
7. **Re-review.** `git diff --staged` again, right before commit — last chance to catch a stray file.
8. **Confirm.** Autonomous by default: for a clean, unambiguous change set, show the
   staged set + message and proceed **without a prompt**. A hard stop or genuine
   ambiguity (below) halts and surfaces instead of committing. Ask for a manual
   confirmation checkpoint only when explicitly requested.
9. **Commit.** `git commit -m "<message>"` (local).
10. **Optional, explicit only.** `git push -u origin <branch>`, then `gh pr create --title ... --body ... --base ...`.

## Safety Checks

- **Relatedness.** Changed paths vs task/SPEC scope; out-of-scope files are held back, not staged.
- **Accidental changes.** Debug prints, commented-out code, whitespace-only churn, lockfile changes with no dependency change, surprisingly large diffs.
- **Sensitive files.** Name + content matching; hard stop.
- **Lint/test status.** Run and confirm; never imply success when unconfigured.
- **Branch.** Refuse/warn on protected branches; the PR flow needs a feature branch.
- **Confirmation.** Autonomous by default: a clean, unambiguous change set commits without a prompt — the staged set + message are shown, not gated on an OK.
- **What autonomy never skips.** It skips *only* the confirmation prompt. It never skips the safety scan and never overrides a hard stop — secrets, out-of-scope/untracked files, a protected branch, a multi-concern split, or a huge/ambiguous diff still halt and surface. Push / PR / merge stay explicit and are never autonomous.

## Commit Message Format

Conventional commits: `type(scope): subject` — imperative mood, ~50-char subject, lowercase, no trailing period. Optional body for the *why*. Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `style`.

```
feat: add automatic lint hook
fix: handle missing config file
chore: clean up generated files
docs: update workflow guide
```

## Failure Behavior

Each case leaves the working tree untouched, or clearly reports what was staged.

- **Tests fail** → stop, name which failed, stage nothing.
- **Unrelated files** → list them with reasons, stage only the related ones (or stop and ask).
- **Secrets** → stop immediately, name the file/pattern (not the value), stage nothing.
- **No changes** → "nothing to commit," exit cleanly.
- **Not a repo / no commits yet / detached HEAD / merge in progress** → explain the state and the fix.
- **`gh` missing or unauthenticated** (PR step only) → explain, skip the PR, keep the local commit.

## Output

Open with a one-line run report — files staged · unrelated held back · secrets · checks — then the result message.

```
✓ Committed locally on feature/lint-hook
  feat: add automatic lint dispatch hook
  3 files staged · 0 unrelated · 0 secrets · lint+tests passed
  Nothing pushed. Say "push" or "open a PR" to share it.

✗ Stopped — possible secret detected: .env contains KEY=********. Nothing staged.
✗ Stopped — tests failed (npm test: 2 failing). Nothing staged. Fix and re-run.
! Staged 2 task files; held back 3 (build artifact, untracked note, out-of-scope file). Confirm if any belong.
· Working tree clean — nothing to commit.
· Not a Git repository (no .git). Run `git init` or open the repo first.
```

## Edge Cases

- **Pre-staged changes** — reconcile them against the task; don't blind-commit what was already staged.
- **Untracked files (`??`)** — require an explicit decision: add or ignore. Never auto-stage.
- **Protected branch** — offer to create a feature branch before committing.
- **Multi-concern diff** — propose splitting into atomic commits.
- **Huge diff** — summarize it and require confirmation before staging.
- **`.gitignore` gaps** — flag un-ignored junk and suggest an ignore entry instead of committing it.

## Rules

The do-not list lives in **Hard Rules** and the procedure in **Workflow** (with **Safety Checks**) — this skill's rules are stated there, not restated here.
