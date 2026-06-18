---
name: unit-testing
description: Shared, stack-agnostic unit-testing policy — the single source of truth for WHAT to test and how thoroughly. Defines the core-vs-plumbing classification rubric, the behavioral coverage policy, the brittleness guardrails, and the common section order every stack skill must follow. Loaded by the unit-test-generator together with exactly one stack skill (flutter-dart, nodejs, python, go). Decides judgment only; the test-runner hook owns execution.
---

# Unit Testing — Shared Policy

This is the **single source of truth** for unit-testing judgment across every
stack. The `unit-test-generator` loads this file plus **one** stack skill; the
stack skill supplies only idioms. Nothing here is duplicated into the stack
skills — when policy and idiom seem to overlap, this file wins.

This skill decides **what** to test and **how thoroughly**. It never runs tests —
the `test-runner.sh` hook does that, deterministically. Judgment and execution
are split on purpose.

## Classification rubric (per UNIT, not per file)

Classify each **unit** of behavior, not each file — one file often holds both a
core calculation and plumbing around it.

- **CORE — test thoroughly.** Domain rules, calculations, validations, state
  machines and transitions, decision / branching logic, parsers and
  transformers, money / date / unit math, algorithms, authorization — anything
  where a conditional encodes business meaning.
- **PLUMBING — test light, or not at all.** Thin wrappers and adapters, DI /
  wiring, config loading, DTO / serialization passthrough, simple CRUD
  forwarding, framework glue, getters / setters, logging, generated code.

**Signals.** A unit that *owns a decision* or *transforms data* is core; one that
*forwards a call unchanged* is plumbing. Branchy, pure logic leans core; thin I/O
glue leans plumbing. Behavior **named in `SPEC.md` is core**. When classification
is ambiguous **and there is real branching**, default to **core**. Always surface
the classification in the report so the call is visible.

## Coverage policy (behavioral, not a percentage)

- **CORE:** happy path + edge cases (boundaries, empty / null, overflow, invalid
  input) + negative paths (errors / exceptions raised and handled) + key state
  transitions.
- **PLUMBING:** happy path + the one or two failure modes that actually matter.
- **Never test** the framework, generated code, third-party libraries, or trivial
  passthrough.
- A numeric coverage floor for core modules is a **signal only**, never the goal.
  High line coverage with no edge or negative cases is worse than fewer, sharper
  tests.

## Guardrails (against noisy, brittle, low-value tests)

- **Test behavior / the public contract**, not private internals. A refactor that
  preserves behavior must keep the tests green.
- **No change-detector tests; no over-mocking.** Prefer real collaborators where
  they are cheap and deterministic; mock only true boundaries (network, clock,
  filesystem, randomness).
- **Never assert on volatile things** — timestamps, unordered collection order,
  log strings, exact formatting, memory addresses.
- **Deterministic only.** Control time, randomness, and I/O. No live network, no
  `sleep`, no order-dependence between tests.
- **One behavior per test**, named for the behavior it pins down (so a failure
  name reads as a spec line).
- **Don't re-test what types or lint already guarantee.**
- **Report skips.** Omissions must be visible, not silent — the generator lists
  what it deliberately left untested and why.

## Common contract — stack skill section order

Every stack skill (`flutter-dart`, `nodejs`, `python`, `go`) is **thin** and
holds only stack-specific idioms. Each MUST use exactly these sections, in this
order, and MUST NOT restate the policy above:

1. **Framework & runner**
2. **File naming & location**
3. **Mocking / stubbing idiom**
4. **Assertion style**
5. **Idiomatic patterns**
6. **Measuring coverage**
7. **Stack-specific anti-patterns**
