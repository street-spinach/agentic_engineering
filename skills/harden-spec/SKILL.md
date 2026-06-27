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
4. **Run the Goldfish checks** (below) by invoking the `goldfish-spec-reviewer` subagent, **once per check**. Each invocation is a fresh Goldfish with no shared memory. On the first hardening, run all three; on a re-run, run only the failed mode(s) and pass in the findings you addressed (see *The Three Goldfish Checks*).
5. **Consolidate** the three outputs into one **Harden Spec Report** (format below). Judge only on the Goldfish findings and the spec itself.
6. **Decide the verdict and handle the marker** (see *Verdict & Marker*).

## The Three Goldfish Checks

Invoke the `goldfish-spec-reviewer` subagent by name (via the Task tool, or `@goldfish-spec-reviewer`) **three separate times — once per mode** — telling it which mode to run:

1. **Goldfish 1 — Comprehension** — is the doc self-sufficient? *(model: sonnet — the agent default)*
2. **Goldfish 2 — Critic** — what did we miss? (flag correctness only) *(model: opus — override the agent default on this invocation)*
3. **Goldfish 3 — Readiness** — could a newcomer build it in one pass? *(model: sonnet — the agent default)*

The subagent owns the canonical `claude -p` prompt and the output sections for each mode — `agents/goldfish-spec-reviewer.md` is the **single source of truth**. Name the mode rather than copying its prompt here, so the prompts live in one place and cannot drift.

**Model per check.** The critic carries the heaviest correctness reasoning, so run **Goldfish 2 on Opus** — pass the model override (`model: opus`) on that Task-tool invocation. Goldfish 1 and 3 use the agent's default (`sonnet`), so they need no override. If you fall back to the headless `claude -p` line, prefix Goldfish 2's with `--model opus`.

**Round 1 runs all three. Later rounds re-run only what failed.** On the first hardening of a spec, run all three checks. On any re-run after a NEEDS HARDENING fix, re-run **only the mode(s) that produced the blocking findings**, plus a quick Goldfish 1 comprehension sanity check if the edits were structural. Re-running clean modes just invites a fresh memoryless reviewer to invent net-new deep questions on parts that were already sound — that is the churn we are eliminating.

**Pass the prior round's findings into the re-run.** When you re-invoke a mode, include in the prompt the list of findings from the last round that you addressed (and how), so the Goldfish focuses on *whether they're resolved and whether anything still blocks building* — not on hunting deeper. The agent's output rules tell it to honor this.

Claude Code skill frontmatter cannot bind a subagent, so this skill invokes it explicitly by name. If the subagent is unavailable, run that mode's canonical `claude -p` line (from the agent) headless as a fallback — same prompt, same mode.

## Verdict & Marker

- **PASS** — and only on PASS — add the marker as the **first line** of `SPEC.md`:

  ```
  <!-- VERIFIED by GOLDFISH -->
  ```

  This means the spec has passed the Goldfish verification gate and is ready for the coding agent to consume.
- **NEEDS HARDENING** — do **not** add the marker.
- **Stale marker** — if `SPEC.md` already contains `<!-- VERIFIED by GOLDFISH -->` but the current run does **not** PASS, **remove** the marker and report that it was stale and must not be trusted. A failed run must never leave the spec marked verified.

**PASS criteria (severity-based).** Each Goldfish tags findings `[BLOCKER]`, `[GAP]`, or `[NIT]`.
PASS requires:

- **Zero BLOCKERs** across all three checks, and
- **Zero un-parked GAPs** — every GAP is either fixed in `SPEC.md` or *parked*: written into the
  spec's **Open Questions** table with an owner, as a deliberate "decide later" call.

**NITs never block.** A spec with only NITs PASSes. Comprehension is still a gate: a `[BLOCKER]`
from Goldfish 1 (it cannot explain the system from the doc alone) forces NEEDS HARDENING.

Parking a GAP as an Open Question is a legitimate resolution, not a cop-out — it is the escape
valve that lets the loop terminate when a question is genuinely a "later" decision rather than a
"can't build without it" decision. Don't park a true BLOCKER; those must be fixed.

## Final Report Format

Consolidate the three Goldfish outputs into one report with exactly these sections:

```markdown
# Harden Spec Report

## Verdict
PASS or NEEDS HARDENING (with round number, e.g. "NEEDS HARDENING — round 2 of 3")

## Findings by Severity
- BLOCKERs: <count> (must be zero to PASS)
- Un-parked GAPs: <count> (must be zero to PASS — fix or park in Open Questions)
- NITs: <count> (never block)

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
The concrete changes needed in SPEC.md — BLOCKERs (must fix) and GAPs (fix or park as Open
Question). Label each.

## Nitpicks to Ignore
NIT-severity findings. Listed for transparency; they do not block and need no action.

## Verification Marker
Whether <!-- VERIFIED by GOLDFISH --> was added, removed, preserved, or not added.

## Human Sign-Off Recommendation
Whether the spec is ready for human sign-off.
```

## After a NEEDS HARDENING Verdict

`/harden-spec` is a gate, not a fixer — on NEEDS HARDENING it returns the report and stops. Remediation is the Elephant's job, so the fresh-eyes review stays honest. Hand the report back to whoever owns the spec — the author / design step (e.g. the `spec-interviewer` skill) — **not** to implementation, and run this loop:

1. **Triage the report by severity:**
   - **BLOCKERs** — must be fixed in `SPEC.md`; they cannot be parked.
   - **GAPs** — either fix now, **or** park as an Open Question with an owner (a deliberate
     "decide later"). Parking is allowed only when there's genuinely no need to resolve it
     before building — not as a way to dodge a real fix.
   - **NITs** — do nothing; they never block.
2. **Update `SPEC.md`** with the fixes, the resolved decisions, and any parked GAPs (in Open
   Questions). Keep the edits minimal and targeted — don't re-expand the spec while fixing it;
   bloat is what slows the next round.
3. **Re-run `/harden-spec`**, re-running only the failed mode(s) and passing in the list of
   findings you just addressed (see *The Three Goldfish Checks*). The revised spec must still
   stand on its own, but the reviewer is now focused on whether your fixes landed — not on
   inventing deeper questions.
4. **Repeat until PASS** (zero BLOCKERs, zero un-parked GAPs) — typically 1–2 rounds for a Task,
   2–3 for a Feature. Then **recommend human sign-off**.

**Round cap — converge or escalate.** If after **3 remediation rounds** the spec still has
BLOCKERs or un-parked GAPs, **stop looping and escalate to the human**. Hand them the residual
findings as decisions to make, and park the open GAPs in Open Questions. Endless re-hardening on
a memoryless reviewer is a smell — either the spec is genuinely under-specified (a human call is
needed) or the reviewer is chasing diminishing returns. Either way, a human decides; do not burn
more rounds. Never hand-add the marker to escape the loop.

Never hand-add the marker to skip the loop: a run that is not PASS must leave `SPEC.md` unmarked (and any stale marker removed). Because coding agents gate on `<!-- VERIFIED by GOLDFISH -->`, implementation cannot legitimately begin until the loop converges.

## Rules

- Fix the **spec, not the Goldfish**. Every finding exists to make `SPEC.md` stronger.
- **Gate on severity, not finding count.** PASS = zero BLOCKERs and zero un-parked GAPs. NITs
  never block; do not loop to drive the NIT count to zero.
- **A GAP may be parked** as an Open Question (with an owner) instead of fixed — that is the
  escape valve. BLOCKERs must be fixed.
- **Cap at 3 remediation rounds**, then escalate residuals to the human (see *After a NEEDS
  HARDENING Verdict*). Don't keep feeding a verbose spec to fresh reviewers hoping it converges.
- Keep remediation edits minimal — fixing a finding by bloating the spec just hands the next
  round more surface to nitpick.
- If the comprehension Goldfish cannot explain the system from the doc alone, that is a BLOCKER — mark the spec **NEEDS HARDENING**.
- Do not start implementation. Do not write or modify product code — the marker line in `SPEC.md` is the only allowed write.
- Coding agents must implement **only** specs that contain `<!-- VERIFIED by GOLDFISH -->`. `/harden-spec` is the only workflow allowed to add this marker, and only on a PASS — zero BLOCKERs and zero un-parked GAPs.
- A failed Goldfish run must never leave the spec marked verified.
- On NEEDS HARDENING, fix the spec and re-run until only nitpicks remain, then recommend human sign-off — see *After a NEEDS HARDENING Verdict*.
