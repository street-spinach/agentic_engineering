---
name: harden-spec
description: Verification gate for a completed SPEC.md, using the Elephant–Goldfish model. Run AFTER SPEC.md is written and BEFORE any implementation begins. Invokes the goldfish-spec-reviewer subagent three separate times — comprehension, critic, readiness — then consolidates the findings into one hardening report. Stamps SPEC.md with the marker <!-- VERIFIED by GOLDFISH --> only on a PASS verdict. Coding agents must implement only specs that carry this marker.
---

# Harden Spec

## Purpose

`/harden-spec` is the verification gate for a completed `SPEC.md`. It pressure-tests the spec with fresh eyes before any code is written, and stamps it as ready only when it survives three independent reviews.

It uses the **Elephant–Goldfish model**:

- **The Elephant** is the long-running design/spec process that produced `SPEC.md`. It remembers the whole design conversation.
- **The Goldfish** is a fresh `goldfish-spec-reviewer` subagent with **no memory** of that conversation. It judges `SPEC.md` only by what the document — and the files it references — actually says.

A spec that only makes sense to the Elephant is not done. This gate proves the spec stands on its own, so the coding agent can consume it safely.

## When to Use

- Right after `SPEC.md` is completed, and **before** implementation begins.
- Again after each round of spec edits, until findings degrade into nitpicks.

Do not run it mid-draft — harden a spec the author considers finished.

## Hard Rules

- Verification is performed by the **`goldfish-spec-reviewer` subagent**, not by you and not from this chat.
- **Do not** use prior conversation context as evidence. The only evidence is `SPEC.md`, the files it references, and the three Goldfish outputs.
- **Do not** inspect unrelated files or browse the wider codebase.
- **Do not** start implementation or write/modify product code.
- The **only** file write this skill may make is adding or removing the `<!-- VERIFIED by GOLDFISH -->` marker in `SPEC.md`.

## Workflow

1. **Confirm `SPEC.md` exists** in the current working directory. If it does not, stop and ask the user to create it or point you to the spec.
2. **Treat `SPEC.md` as the completed Elephant output** — the single source of truth for this run.
3. **Identify the files `SPEC.md` explicitly references** (use Glob/Grep). You hand the Goldfish nothing from this chat; it reads `SPEC.md` and those files itself.
4. **Run the three Goldfish checks** (below) by invoking the `goldfish-spec-reviewer` subagent **three separate times — once per check**. Each invocation is a fresh Goldfish with no shared memory.
5. **Consolidate** the three outputs into one **Harden Spec Report** (format below). Judge only on the Goldfish findings and the spec itself.
6. **Decide the verdict and handle the marker** (see *Verdict & Marker*).

## The Three Goldfish Checks

Invoke `goldfish-spec-reviewer` by name (e.g. via the Task tool, or `@goldfish-spec-reviewer`) once per check, passing the canonical prompt verbatim so the subagent runs the right mode. These prompts are the canonical definition of each check:

**Goldfish 1 — Comprehension** (is the doc self-sufficient?)

```
claude -p "Read SPEC.md and only the files it references. Explain what it is trying to accomplish and how the current system works. If anything is unclear or missing, list it."
```

**Goldfish 2 — Critic** (what did we miss?)

```
claude -p "You are a skeptical technical reviewer. Read SPEC.md and its referenced files. List faulty assumptions, missing edge cases, and ambiguities. Flag only what affects correctness."
```

**Goldfish 3 — Readiness** (could a newcomer build it in one pass?)

```
claude -p "You are an engineer new to this codebase. Read SPEC.md. Could you implement this in a single pass? List every question you would need answered first."
```

The `goldfish-spec-reviewer` subagent is the supported mechanism for these checks. Claude Code skill frontmatter cannot bind a subagent, so this skill invokes it explicitly by name in the body. If the subagent is unavailable, run the three `claude -p` lines above headless as a fallback — same prompts, same modes.

## Verdict & Marker

- **PASS** — and only on PASS — add the marker as the **first line** of `SPEC.md`:

  ```
  <!-- VERIFIED by GOLDFISH -->
  ```

  This means the spec has passed the Goldfish verification gate and is ready for the coding agent to consume.
- **NEEDS HARDENING** — do **not** add the marker.
- **Stale marker** — if `SPEC.md` already contains `<!-- VERIFIED by GOLDFISH -->` but the current run does **not** PASS, **remove** the marker and report that it was stale and must not be trusted. A failed run must never leave the spec marked verified.

PASS requires **all three** Goldfish checks to clear with **no correctness-blocking findings**. Comprehension is a gate: if Goldfish 1 cannot explain the system from the doc alone, the verdict is NEEDS HARDENING.

## Final Report Format

Consolidate the three Goldfish outputs into one report with exactly these sections:

```markdown
# Harden Spec Report

## Verdict
PASS or NEEDS HARDENING

## Self-Sufficiency
State whether SPEC.md can be understood without prior conversation context.

## Goldfish 1 — Comprehension Findings
Whether the Goldfish could explain:
- What the spec is trying to accomplish
- How the current system works
- What is unclear or missing

## Goldfish 2 — Correctness Findings
- Faulty assumptions
- Missing edge cases
- Correctness risks
- Ambiguities that affect correctness

## Goldfish 3 — Readiness Findings
- Whether a newcomer could implement this in one pass
- Blocking questions
- Missing decisions
- Missing acceptance criteria
- Missing test expectations

## Required SPEC.md Changes
The concrete changes needed in SPEC.md.

## Nitpicks to Ignore
Non-blocking findings that do not affect correctness.

## Verification Marker
Whether <!-- VERIFIED by GOLDFISH --> was added, removed, preserved, or not added.

## Human Sign-Off Recommendation
Whether the spec is ready for human sign-off.
```

## Rules

- Fix the **spec, not the Goldfish**. Every finding exists to make `SPEC.md` stronger.
- Prioritize correctness-impacting findings. Ignore style-only feedback unless it affects clarity.
- If the comprehension Goldfish cannot explain the system from the doc alone, mark the spec **NEEDS HARDENING**.
- Do not start implementation. Do not write or modify product code — the marker line in `SPEC.md` is the only allowed write.
- Coding agents must implement **only** specs that contain `<!-- VERIFIED by GOLDFISH -->`. `/harden-spec` is the only workflow allowed to add this marker, and only after all three Goldfish checks pass with no correctness-blocking findings.
- A failed Goldfish run must never leave the spec marked verified.
- Repeat `/harden-spec` after each `SPEC.md` update until findings degrade into nitpicks. Once only nitpicks remain, recommend human sign-off.
