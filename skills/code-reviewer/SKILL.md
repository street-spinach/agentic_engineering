---
name: code-reviewer
description: Basic, language-focused code review — the single source of truth for the language-level concerns to check on any change (correctness idioms, error handling, resource safety, concurrency, performance, readability). Loaded together with exactly one language skill (python, flutter-dart, nodejs, go), which supplies only that language's idioms and footguns. Checks language quality only; it does NOT judge a diff against SPEC.md — that is the `code-verifier`'s job.
---

# Code Reviewer — Shared Language Review

This is the **single source of truth** for language-level code review across every
stack. Load this file plus **one** language skill (`python` / `flutter-dart` /
`nodejs` / `go`); the language skill supplies only that language's idioms and
footguns. Nothing here is duplicated into the language skills — when this file and
a language skill seem to overlap, this file wins.

Scope: this skill judges **how the code is written in its language** — is it
correct, idiomatic, safe, and readable? It does **not** judge the change against
`SPEC.md` or the product intent — that is the **`code-verifier`**'s lane. Use this
for a quick, language-aware pass; use `/code-verifier` for the spec-gate review.

## What to check (every language)

- **Correctness idioms** — off-by-one, truthiness/equality traps, mutable defaults,
  integer/float surprises, copy-vs-reference mistakes, null/None/nil handling.
- **Error handling** — are errors caught at the right level, not swallowed? Is the
  failure path as deliberate as the happy path? No bare catch-all that hides bugs.
- **Resource safety** — files, sockets, locks, DB connections opened and always
  released (even on error). No leaks; deterministic cleanup.
- **Concurrency & async** — shared mutable state, races, unawaited work, blocking
  the event loop / main thread, deadlock-prone lock ordering.
- **Performance smells** — needless allocation in hot paths, N+1 calls, work inside
  a loop that belongs outside it, accidental O(n²). Flag only where it matters.
- **API & types** — public signatures clear and honestly typed; no leaking
  internals; immutability where it prevents bugs.
- **Readability & maintainability** — naming, dead code, duplication, over-clever
  constructs, comments that explain *why* not *what*.

## How to report

- **Be specific and idiomatic.** Quote `file:line`, name the language rule or smell,
  and show the idiomatic fix in that language ("use a context manager", "defer the
  Close", "await this").
- **Severity discipline.** `blocking` = a real bug or unsafe pattern; `recommended`
  = should fix; `nit` = style. Don't inflate; inflated highs get ignored.
- **Match the repo.** Follow the conventions already in the codebase over personal
  preference. A consistent codebase beats your favorite idiom.
- **Don't re-report lint.** Mechanical/style issues a linter or formatter catches
  are out of scope — focus on what a linter can't see.

## Common contract — language skill section order

Every language skill (`python`, `flutter-dart`, `nodejs`, `go`) is **thin** and
holds only language-specific concerns. Each MUST use exactly these sections, in
this order, and MUST NOT restate the checks above:

1. **Idioms & conventions** — what idiomatic code looks like here.
2. **Common bugs & footguns** — the language-specific traps to scan for.
3. **Error handling** — the idiomatic error model and its misuse.
4. **Concurrency / async** — the language's concurrency model and its hazards.
5. **Performance notes** — the allocations/patterns that bite in this language.
6. **Anti-patterns** — what to flag on sight.
