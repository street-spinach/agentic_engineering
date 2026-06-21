---
name: Distill Spec
description: >-
  On feature completion — every TASKS.md slice done and SPEC.md's Verification passing, just
  before the ephemeral SPEC.md/TASKS.md are discarded — lift the durable decisions into a new
  immutable ADR and refresh ARCHITECTURE.md. Use to capture the lasting "why" (Decisions +
  rejected alternatives) and "how it works now" before throwing away the point-in-time spec.
  Don't keep stale specs as documentation; distill them. Run this at the end of a feature, after
  the last slice's auto-commit and before merge.
---

# Distill Spec

## Purpose

`SPEC.md` and `TASKS.md` are ephemeral working memory — gitignored, discarded once a feature
ships. But two things inside them are worth keeping forever: *why* we decided what we decided,
and *how the system now works*. This skill lifts those out before the spec is thrown away, so
the repo keeps the signal and drops the noise. A stale spec misleads; a dated ADR never does.

## When to Use

- A feature is complete: every `TASKS.md` slice is done and `SPEC.md`'s Verification section
  passes.
- Right before discarding or overwriting the ephemeral `SPEC.md` / `TASKS.md` — typically after
  the last slice's `/auto-commit` and before merge.

Skip it when nothing architecturally meaningful was decided — a trivial change has no lasting
*why*. Say you skipped it and why, rather than writing an empty record.

## Workflow

1. **Read the finished `SPEC.md`** — focus on the **Decisions** and **Alternatives Considered
   and Rejected** sections, plus anything that changed the system's shape (new components, data
   flow, contracts).
2. **Decide what's durable.** One ADR per *significant* decision. Bundle tightly-related choices
   into one record; don't split hairs, and don't manufacture ADRs for trivia.
3. **Write the ADR(s).** Copy `docs/adr/TEMPLATE.md` to `docs/adr/NNNN-<slug>.md`, where `NNNN`
   is the next zero-padded number after the highest existing ADR and `<slug>` comes from the
   decision title. Fill Context / Decision / Consequences / Alternatives from the spec. ADRs are
   **immutable** — never edit a shipped one; supersede it with a new ADR instead.
4. **Refresh `ARCHITECTURE.md`** *only if* the system's current shape changed — edit it in place
   to describe the new reality (it is current-state, not history). If nothing structural changed,
   leave it.
5. **Leave `SPEC.md` / `TASKS.md` alone** — they're gitignored and will be discarded or
   overwritten by the next feature. Don't commit them.
6. **Report** what you captured and what you deliberately skipped.

## Rules

- ADRs are immutable and append-only — supersede, never rewrite. `ARCHITECTURE.md` is
  current-state and edited in place.
- One ADR per significant decision; skip trivia and say you skipped it.
- Number ADRs sequentially, zero-padded (`0001`, `0002`, …); derive the slug from the title.
- Never commit `SPEC.md` or `TASKS.md`.
- This skill writes docs; it doesn't push. Commit the ADR + `ARCHITECTURE.md` through the normal
  `/auto-commit` flow.

## Output

A short report: the ADR(s) created (path + a one-line decision each), whether `ARCHITECTURE.md`
was updated, and any durable content you chose not to record, with the reason.
