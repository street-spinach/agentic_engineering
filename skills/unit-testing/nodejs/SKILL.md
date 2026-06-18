---
name: unit-testing-nodejs
description: Stack-specific unit-testing idioms for Node.js / TypeScript. Use together with the shared unit-testing policy when the nearest manifest is package.json (or the changed file is .js/.ts). Holds runner, layout, mocking, assertion, and coverage idioms only — the shared skill owns classification, coverage depth, and guardrails.
---

# Unit Testing — Node.js / TypeScript

Stack idioms only. Classification, coverage depth, and guardrails live in the
shared `skills/unit-testing/SKILL.md`. Mirror whatever the repo already uses.

## Framework & runner

Detect from `package.json` (deps + the `test` script): **jest**, **vitest**, or
**mocha**. Match the one already configured — never add a second runner.

## File naming & location

`*.test.ts` / `*.test.js` colocated, or under `__tests__/`. Follow the repo's
existing convention rather than imposing one.

## Mocking / stubbing idiom

`jest.mock` / `vi.mock` (or `sinon` with mocha). Mock module boundaries and the
clock (`jest.useFakeTimers` / `vi.useFakeTimers`); pass real plain objects.

## Assertion style

`describe` / `it` / `expect` with matchers (`toBe`, `toEqual`, `toThrow`,
`rejects.toThrow`). Use `expect.assertions(n)` in async tests that branch.

## Idiomatic patterns

- One behavior per `it`, named for the behavior.
- `it.each([...])` for table-driven cases over the same logic.
- Inject collaborators (clock, fetch, repo) so tests stay deterministic.

## Measuring coverage

The runner's own flag — `jest --coverage` / `vitest run --coverage`. Scope a
single change with `jest --findRelatedTests <files>`.

## Stack-specific anti-patterns

- Don't mock the unit under test, or assert on a mock's internal call order as a
  proxy for behavior.
- Don't `await` real timers / network — fake them.
- Don't snapshot large objects to dodge writing real assertions.
