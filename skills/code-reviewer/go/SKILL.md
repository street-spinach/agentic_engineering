---
name: code-reviewer-go
description: Language-specific code-review concerns for Go. Use together with the shared code-reviewer skill when the nearest manifest is go.mod (or the changed file is .go). Holds Go idioms, footguns, and anti-patterns only — the shared skill owns the cross-language checklist and severity rules.
---

# Code Reviewer — Go

Language concerns only. The cross-language checklist, severity rules, and report
style live in the shared `skills/code-reviewer/SKILL.md`. Mirror the repo's style.

## Idioms & conventions

Accept interfaces, return structs; small interfaces (1–2 methods). Zero values
usable where possible. `gofmt`-clean (assume it ran). Short names in small scopes.
Errors are values — return them, don't panic for ordinary failures.

## Common bugs & footguns

- **Loop variable capture** in goroutines/closures (pre-1.22) — copy into the loop.
- **`nil` interface != nil**: a typed nil stored in an interface is non-nil.
- Slices share backing arrays — `append` can mutate an aliased slice; `copy` when
  you need isolation. Appending to a sub-slice can clobber the parent.
- Map iteration order is random — don't depend on it.
- Comparing/ranging over a map concurrently without a lock.

## Error handling

Check **every** returned `err`; never `_`-discard one that matters. Wrap with
`fmt.Errorf("...: %w", err)` to preserve the chain; test with `errors.Is`/`As`.
Reserve `panic` for truly unrecoverable state. Don't log-and-return the same error.

## Concurrency / async

Goroutines need a clear exit — no leaks. Protect shared state with a mutex or a
channel, not both. Pass `context.Context` for cancellation/timeouts and honor it.
Close channels from the **sender**, once. Run the race detector (`-race`) mentally
on shared access. Beware unbuffered-channel deadlocks.

## Performance notes

Preallocate slices/maps with capacity when size is known; avoid per-iteration
allocation in hot loops; pass large structs by pointer. `defer` has small cost in
tight loops. Don't optimize without a reason.

## Anti-patterns

- Ignoring errors with `_` (outside genuinely safe cases).
- `panic`/`recover` used as control flow.
- Naked returns in long functions; `interface{}`/`any` where a type would do.
- Goroutine started with no way to stop or wait for it.
