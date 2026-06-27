---
name: Slice Planner
description: Turn a Goldfish-verified SPEC.md into an executable, iterative delivery plan (TASKS.md) of small end-to-end slices ordered by dependency and value, each with a measurable goal/acceptance criteria, impacted files, dependencies, risk, and validation steps. Also maintains TASKS.md as the build reveals new work. Plans only; never implements. References SPEC.md, never restates it.
---

# Slice Planner

## Purpose

`/plan-slices` is the **execution spine** between a verified spec and the
per-slice build loop. `SPEC.md` is durable **design** memory — what we're
building and why. `TASKS.md` is durable **execution** memory — its twin. If the
agent loses all context mid-build, reading `TASKS.md` (and the `SPEC.md` it
points to) re-orients it: what's done, what's in flight, what's left, and what
"done" means for the current slice.

The main/orchestrator agent runs this skill **directly** — no subagent. Planning
shares context with the implementer and is updated inline as the build proceeds.

## When to Use

- **Once**, right after `/harden-spec` returns PASS — to derive `TASKS.md`.
- **Continuously** thereafter, during implementation — to keep it current.

Skip it if there is no verified `SPEC.md`; there is nothing to plan from.

## Two Modes

**DERIVE (run once).** Read the verified `SPEC.md` and enumerate *all* the work it
implies — app code, unit + integration/e2e tests where relevant, config,
migrations, docs, observability, rollout/compat. Then decompose that into vertical
end-to-end slices and write `TASKS.md`, ordered by dependency, then delivery
value. This is the only time you build the plan from scratch.

**MAINTAIN (continuous).** As the build reveals reality, keep `TASKS.md` true: flip
statuses, add discovered work, re-order when dependencies shift, refine
later-slice detail as earlier slices teach you. Update `TASKS.md` as the **first
and last action of every slice** — read it to pick up the next slice, write it to
record the slice's outcome.

## Hard Rules

- **Plan only from a verified spec.** `SPEC.md` must carry
  `<!-- VERIFIED by GOLDFISH -->`. If the marker is absent, **stop** and point to
  `/harden-spec` — do not plan against an unverified spec.
- **Slices are vertical and end-to-end**, never technical layers. A slice is valid
  only if you can name the human action that demonstrates it (Spec Interviewer's
  value-check). **Reuse that check — don't re-derive it here.**
- **Preserve existing behavior** unless `SPEC.md` explicitly requires a change.
  This is a standing invariant on every slice: existing tests stay green; no
  API/contract change unless the spec says so.
- **Plan, don't implement.** This skill never writes product code, runs builds, or
  commits. Testing lives *inside* each slice, risk-based, delegated to
  `unit-test-generator` — it is never a final phase tacked on at the end.
- **`TASKS.md` references `SPEC.md`; it does not restate it.** Point to the spec's
  sections for the *why* and the *what*; `TASKS.md` carries only the *how/when* of
  delivery.

## Ordering & Detail Heuristics

- **Walking skeleton first.** Slice 1 goes thinly through *every* layer to de-risk
  integration early — the smallest end-to-end path that proves the pieces connect.
- **Then dependency, then value.** A slice that unblocks others, or delivers the
  most learning per unit of work, comes earlier.
- **Rolling-wave detail.** Fully specify only the **next 1–2 slices**. Keep later
  slices coarse — a name and a rough goal — and refine them as earlier slices
  teach you. Don't over-plan; the plan is a living document, not a contract.

## TASKS.md Format

Lightweight Markdown. Keep it scannable — this is execution memory, not a
re-spec.

```markdown
# TASKS — <feature>   (source: SPEC.md, verified <marker/commit>)
Invariants: existing tests stay green; no API/contract change unless SPEC says so.
Status: Slice 2 of 5 — in progress

## Slice 1 — <thin end-to-end name>   ✅ done
Goal / acceptance: <the measurable outcome that means this slice is done>
Demonstrated by: <human action or check — "user does X, sees Y">
Impacted: <files / components>
Depends on: —    Risk: low
Validation: lint · unit (core) · review APPROVE
- [x] app code: …
- [x] unit tests (core paths + negative): …
- [x] docs: …

## Slice 2 — <name>   🔄 in progress
Goal / acceptance: …    Demonstrated by: …
Impacted: …    Depends on: Slice 1    Risk: high
Validation: lint · unit (edge+negative) · integration · review APPROVE
- [ ] …

## Discovered (added during build)
- [ ] follow-up from Slice 2: …

## Out of scope (from SPEC non-goals)
- …
```

## The Slice / Goal / Loop

Each slice runs one cycle. The **goal is the loop's exit condition** — set it,
measure against it, stop when it's met:

1. **Plan the slice** — lock the goal (acceptance criteria), impacted files, and
   validation steps. *(Set the target.)*
2. **Implement** — code for this slice only; the lint hook gives live feedback.
3. **Test as part of the slice** — delegate to `unit-test-generator`, risk-based,
   at the depth the slice's risk warrants (per Hard Rules; not a final phase).
4. **Run checks** — lint + test-runner hooks. *(Measure.)*
5. **Verify against acceptance** — `/code-verifier` must APPROVE **and** the goal
   must be met. *(Compare.)*
6. **Fix** — address findings/failures; back to step 4. *(Correct.)*
7. **Gate + advance** — only when green **and** acceptance met **and** APPROVE →
   `/auto-commit`, mark the slice done, log discovered work. *(Exit condition met
   → next slice.)*
8. **Compact** — after `/auto-commit` at the slice boundary, run `/compact`;
   TASKS.md and SPEC.md rehydrate the next slice. Compact at seams, not mid-edit;
   if the window passes ~60% off a seam, checkpoint to TASKS.md and compact early
   (see `CLAUDE.md` → Compact Instructions).

## Goals & Loops

- **The goal = acceptance criteria = the loop's exit condition**, and it must be
  measurable. "Handle errors well" is not a goal. "Returns 422 with the offending
  field list on invalid input, covered by a test" is. The deterministic hooks and
  the review verdict are the **sensors** that measure the build against the goal;
  that's what closes the loop.
- **Inner loop** = the per-slice cycle above. **Outer loop** = repeat slices until
  *every* `TASKS.md` slice is done **and** `SPEC.md`'s Verification section
  passes. Each slice's acceptance criteria ladder up to that spec-level
  verification.
- **The goal cuts both ways.** It prevents **under-building** — the gate won't pass
  until the behavior actually exists — and **gold-plating** — extra ideas don't get
  built; they go to *Discovered*. "This and no more."

## Failure / Edge Behavior

- **Spec not verified** → the verified-spec Hard Rule applies: stop and point to
  `/harden-spec`.
- **No Verification or Non-Goals section in `SPEC.md`** → note the gap (so the
  outer-loop exit condition and the Out-of-scope list are weaker than they should
  be) and proceed conservatively.
- **Vague acceptance criteria** → tighten them until checkable *before* starting
  the slice. A slice whose goal you can't measure has no exit condition.
