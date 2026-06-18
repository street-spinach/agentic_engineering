---
name: unit-testing-go
description: Stack-specific unit-testing idioms for Go. Use together with the shared unit-testing policy when the nearest manifest is go.mod (or the changed file is .go). Holds runner, layout, mocking, assertion, and coverage idioms only — the shared skill owns classification, coverage depth, and guardrails.
---

# Unit Testing — Go

Stack idioms only. Classification, coverage depth, and guardrails live in the
shared `skills/unit-testing/SKILL.md`. Mirror whatever the repo already uses.

## Framework & runner

Standard `testing` package, run via `go test`. Scope to a package with
`go test ./path/to/pkg`.

## File naming & location

`foo_test.go` **colocated** with `foo.go` in the same package. Use an external
`package foo_test` when you mean to test only the exported API.

## Mocking / stubbing idiom

Define small interfaces at the consumer and pass a hand-written fake, or
`gomock` if the repo already uses it. Inject a `Clock` rather than calling
`time.Now()`. `testify` (`assert` / `require`) is optional — match the repo.

## Assertion style

Plain `if got != want { t.Errorf("got %v, want %v", got, want) }`. Use
`require` to stop on a fatal precondition, `assert` to keep checking. `t.Helper()`
in assertion helpers.

## Idiomatic patterns

- **Table-driven tests**: a slice of cases looped with `t.Run(tc.name, ...)`.
- `t.Parallel()` only for independent, deterministic cases.
- Inject dependencies through interfaces for seams.

## Measuring coverage

`go test -cover ./...`, or `-coverprofile=cover.out` + `go tool cover`.

## Stack-specific anti-patterns

- Don't reach into unexported state from an external test package — test behavior.
- Don't assert on map iteration order (it's randomized).
- Don't build a mock framework where a tiny interface + fake struct suffices.
