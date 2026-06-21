# 0001. Ephemeral specs/tasks; durable ADRs + ARCHITECTURE.md

- **Status:** Accepted
- **Date:** 2026-06-21

## Context

The workflow produces `SPEC.md` (design intent) and `TASKS.md` (slice plan) for
every feature, and the gates depend on them *during* the build: `harden-spec`
stamps `SPEC.md`, `code-review` judges the diff against it, and `/compact`
rehydrates from `TASKS.md`. But once the code ships, a spec describes a point in
time and drifts from the code — a stale spec actively misleads the next reader,
human or model. We want the build-time benefits without accumulating misleading
documents in the repo.

## Decision

We will treat `SPEC.md` and `TASKS.md` as ephemeral working memory: created per
feature, read/updated by the agent during the build, and **gitignored** so they
are never committed. On feature completion, `/distill-spec` lifts the durable
parts — the **Decisions** and the **Alternatives Considered and Rejected** — into
a new immutable ADR under `docs/adr/`, and refreshes `ARCHITECTURE.md` if the
system's shape changed. Durable *why* lives in ADRs; durable *how it works now*
lives in `ARCHITECTURE.md`; new features read those, not old specs.

## Consequences

- The repo stays free of stale specs; the knowledge that lasts is captured
  deliberately rather than by accident.
- ADRs are dated history and never drift; `ARCHITECTURE.md` is kept current in
  place.
- Cost: the exact spec that gated a change is not in `main` history by default. If
  an audit trail is needed, keep the spec on the feature branch / PR (preserved by
  the PR) without merging it to `main`.
- Caveat: a single gitignored root `SPEC.md`/`TASKS.md` suits serial, one-feature
  work. Parallel feature branches need per-branch scoping (`.agent/<branch>/`),
  because gitignored files persist across branch switches and would otherwise
  cross-contaminate.

## Alternatives considered

- **Keep specs/tasks committed in-tree (e.g. `docs/specs/<feature>/`)** — rejected:
  full traceability, but it accumulates point-in-time docs that drift and mislead.
- **Keep nothing; no durable docs** — rejected: loses the *why*, forcing future
  readers to reverse-engineer decisions from code.
- **One growing `architecture.md` holding all notes** — rejected: it becomes a junk
  drawer. Mixing immutable decisions with current-state description makes both
  untrustworthy. Splitting into immutable ADRs + a current-state doc keeps each
  honest.
