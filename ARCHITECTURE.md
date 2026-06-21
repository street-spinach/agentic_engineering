# Architecture — agentic_eng

A reusable Claude Code workflow library: skills, subagents, hooks, and settings
that enforce a gated spec → build → review → commit loop. Installed into a project
as a plugin (`.claude-plugin/`), it adds the workflow without touching that
project's own code.

This document describes the system **as it is now**. For the *why* behind a given
choice, see `docs/adr/`. For *what's being built next*, see the ephemeral
`SPEC.md` / `TASKS.md` (gitignored working memory — not documentation).

## Components

**Skills (`skills/`) — model-invoked judgment.**

- `prompt-enhancer` — sharpens a rough first intent before spec/implementation.
- `spec-interviewer` — interviews the user (product + technical) to co-write `SPEC.md`.
- `harden-spec` — verification gate; runs the goldfish-spec-reviewer 3× and stamps `SPEC.md`.
- `plan-slices` — turns a verified `SPEC.md` into `TASKS.md` of vertical slices.
- `code-review` — orchestrates fresh-eyes review of a diff or PR.
- `auto-commit` — curated, scoped local commits.
- `test-backfill` — push-time safety net that fills missing tests.
- `unit-testing` (+ `python` / `go` / `nodejs` / `flutter-dart`) — shared testing policy + stack idioms.
- `android-app-testing` / `ios-app-testing` — black-box UI tests on an emulator/simulator (ADB; `xcrun simctl` + `idb`).
- `distill-spec` — on feature completion, lifts durable decisions into an ADR and refreshes this file.

**Subagents (`agents/`) — fresh-eyes, no memory of the build conversation.**

- `goldfish-spec-reviewer` — pressure-tests `SPEC.md` (comprehension / critic / readiness).
- `code-reviewer` — pressure-tests the diff against the verified spec.
- `unit-test-generator` — writes behavior-focused tests at the right depth.

**Hooks (`hooks/`) — deterministic, never call a model.**

- `lint-dispatch.sh` — per-edit lint (PostToolUse) + commit gate (PreToolUse).
- `test-runner.sh` — runs tests at the commit gate and after the generator (SubagentStop).
- `pre-push-test-backfill.sh` — fires `/test-backfill` in the background on `git push`.
- `cache-meter.sh` — reports prompt-cache hit-rate from the transcript on Stop.

**Wiring.** `settings.json` (hook + permission template), `.claude-plugin/`
(plugin + marketplace manifests that make skills/agents discoverable on install),
`CLAUDE.md` (the workflow gates).

## Control flow (the gates)

```
intent ─▶ prompt-enhancer / spec-interviewer ─▶ SPEC.md
        ─▶ harden-spec (goldfish ×3) ─▶ SPEC.md [VERIFIED]
        ─▶ plan-slices ─▶ TASKS.md
        ─▶ per slice: implement ─▶ lint+test hooks ─▶ code-review ─▶ auto-commit
        ─▶ (git push) pre-push hook ─▶ test-backfill ─▶ PR
        ─▶ feature done ─▶ distill-spec ─▶ docs/adr/* + ARCHITECTURE.md
```

## Design principles

- **Deterministic vs. judgment, split on purpose.** Mechanical, reproducible work
  (lint, test execution, push/PR/tag) lives in hooks/shell that never call a model;
  judgment (review, test design, spec verification) lives in skills/subagents. The
  gate is always the deterministic part.
- **Fresh-eyes isolation (Elephant–Goldfish).** Reviewers run as subagents with no
  memory of how the artifact was written, so they judge the work, not the author's
  rationalizations — and the main thread's context stays lean.
- **Ephemeral scaffolding vs. durable knowledge.** `SPEC.md`/`TASKS.md` are
  point-in-time working memory (gitignored, discarded after the feature). Lasting
  *why* is distilled into immutable ADRs; lasting *how it works now* is kept current
  here.
- **Progressive disclosure.** Skill bodies load only when invoked; the unit-testing
  policy pulls in one stack skill, not all four.

## Where things live

- Workflow rules → `CLAUDE.md`
- Durable decisions → `docs/adr/NNNN-*.md` (immutable, append-only)
- Current-state architecture → `ARCHITECTURE.md` (this file; kept current)
- Ephemeral build memory → `SPEC.md`, `TASKS.md` (gitignored)
