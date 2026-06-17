---
name: Spec Interviewer
description: Interview a user to co-write a spec in Markdown (spec.md) — from problem through technical plan to verification. Use to turn a rough idea or feature request into a structured spec covering problem, technical plan, alternatives, implementation, and verification. Don't draft from one prompt — interview first, propose the design yourself, and build incrementally.
---

# Spec Interviewer

## Purpose

Help a user turn a rough idea into a clear spec (`spec.md`) — from problem through technical plan to verification. Interview first, propose the design yourself, build incrementally. Never write the full spec from a single prompt.

## When to Use

- The user wants a product or feature spec.
- The requirement is vague, broad, or partly unstated.
- Drafting now would mean guessing scope or details.

Skip it for trivial, fully-specified tasks.

## Classify and Scope-Gate (Do This First)

Before interviewing, classify the requirement by altitude. A vague *problem* is fine — that's what the interview is for. An unbounded *solution* is not — interviewing a too-big requirement just produces a sprawling, unbuildable spec. Triage first, then gate.

**Altitude tiers:**

- **Epic / Initiative** — reshapes or adds a major capability to the system. Spans multiple subsystems, weeks+ of work, many moving parts. *Examples: "add an agentic layer to our app," "make the platform multi-tenant," "migrate to microservices," "build an AI assistant into the product."*
- **Feature** — one coherent capability a single spec can cover end-to-end. Days to a couple of weeks. One primary user flow. *Examples: "add SSO login," "let users export reports as PDF," "add a retry queue for failed webhooks."*
- **Task** — a single well-bounded change. Hours to a day. *Examples: "add a rate limit to the login endpoint," "add a `created_at` column."*

**The gate:** Only **Feature** and **Task** requirements are ready to interview. If you classify the requirement as **Epic**, **stop and push back** — do not start the problem interview. Tell the user the requirement is too high-level for one spec, and ask them to slice it into independent, end-to-end features first. Offer a candidate breakdown yourself (3–6 features, each standing alone and delivering value) so the user has something concrete to react to, then ask which one slice to spec now. Spec exactly one slice per session.

Signals that a requirement is an Epic and must be sliced before interviewing:
- It names a *layer*, *platform*, *system*, or *capability* rather than a behavior ("agentic layer," "analytics platform").
- It bundles several distinct user flows or subsystems under one phrase.
- You can't name the single end-to-end check that would prove it done.
- "Implement / extend the system to do X" where X is open-ended.

State your classification explicitly ("This reads as an Epic — let's slice it") so the user can correct you if you misjudged the altitude.

## Value Check: Every Slice Must Be a Vertical Slice

A slice is only valid if a real user or stakeholder can *exercise it and judge its value* within one feedback cycle. The point of the work is to ship business/consumer value we can test quickly and learn from — not to land plumbing nobody can see.

**Reject layer-only slices** — they deliver nothing testable on their own:
- *Backend-only* (API/service/schema with no surface a user touches) — the user can't see or judge it.
- *Agent-only* (a model, tool, or capability not wired into the chat/UI the user actually uses) — building it without the wiring proves nothing.
- *Frontend-only* against stubs — looks real, delivers no actual behavior.

A valid slice crosses **every layer needed for the value to be felt**: e.g. a new agent capability is sliced *together with* its wiring into the chat interface; a backend feature is sliced *together with* the UI or endpoint a user exercises. If you can't name the human action that demonstrates the slice ("user types X in chat and sees Y"), it isn't a slice yet.

**The tension — and how to resolve it.** Going end-to-end can balloon a slice until it rivals "do the whole thing." When that happens, **scope down by narrowing the behavior, not by dropping layers.** Keep it thin *vertically* (still crosses all layers), thin *horizontally* in what it does:
- One happy path, not all cases. One user/role, not all. One input type, not many.
- Hardcode or stub the edges (config, error handling, scale) and note them as follow-ups.
- Defer breadth (more flows, more entities) to later slices.

Strongly push toward further scoping whenever the end-to-end slice is still large. A smaller slice that a user can touch tomorrow beats a complete one they see next month. State the trade explicitly: "We can ship just the happy path through chat this week and get feedback — the rest becomes follow-up slices."

## Run in Plan Mode

Conduct the entire interview in **plan mode**. Plan mode is read-only — it blocks file edits and code changes — which mechanically enforces this skill's core discipline: don't implement, or touch the codebase, while the spec is still being shaped. Soft rules get violated by accident; plan mode can't be.

- **Enter plan mode at the start**, before classifying.
- **Everything read-only:** classify, interview, propose the design, slice, and draft the spec *content shown in the chat* incrementally. No codebase edits are possible, so the discovery phase can't drift into implementation.
- **`ExitPlanMode` is the finalization gate.** Writing `spec.md` is a file write, so it can't happen mid-interview. Present the assembled spec for approval via `ExitPlanMode`; only on approval, exit and write `spec.md`.

If the user isn't in plan mode when the skill starts, ask to switch into it before interviewing.

## Workflow

0. **Classify and gate.** Run the triage above. If it's an Epic, push back and slice before going further. Proceed only with a single Feature- or Task-sized slice.
1. **Frame the problem.** Ask what they want to build and why. One or two questions.
2. **Interview in small batches.** Ask 2–4 focused questions at a time. Cover, in order: goal, users, problem, scope, constraints, success criteria. Wait for answers before moving on.
3. **Slice the work.** Break the requirement into end-to-end product slices. Each slice stands alone, delivers value, and makes sense without the others. Run the Value Check on every slice: reject layer-only slices (backend-only, agent-only-without-wiring, frontend-on-stubs), and if an end-to-end slice is too big, scope it down by narrowing the behavior — never by dropping layers.
4. **Propose the design — don't react to theirs.** Once you understand the system, draft the first design yourself in prose and a block diagram. A real proposal exposes your understanding and the user's blind spots; asking them to propose first lets their blind spots survive.
5. **Record what you rejected.** For each major choice, note the alternatives considered and why they lost. Rejections become guardrails — they stop later work from drifting back into a ruled-out approach.
6. **Plan the implementation.** List every file to be created or changed, and why.
7. **Define verification.** Specify the end-to-end check that proves the feature works.
8. **Draft incrementally.** Fill the spec section by section. Show progress; don't dump a finished doc.
9. **Track the unknowns.** Log assumptions, decisions, open questions, and non-goals as they surface.

## Spec Template

````markdown
# <Product / Feature Name>

## Goal
What we're building and why. One paragraph.

## Users
Who this is for.

## Problem
The pain or need — in plain English a casual reader can follow.

## Scope
What's included.

## Non-Goals
What's explicitly out.

## Slices
End-to-end pieces, each valuable on its own. For each, name the human action that demonstrates its value (e.g. "user types X in chat → sees Y") — if you can't, it's a layer, not a slice.
- Slice 1: ... — Demonstrated by: ...
- Slice 2: ... — Demonstrated by: ...

## Technical Plan
How it works, in prose, plus a block diagram of the major components.

```
[ Component A ] --> [ Component B ] --> [ Component C ]
```

## Alternatives Considered and Rejected
Options we ruled out, and why. These guard against drifting back.
- Alternative: ... — Rejected because ...

## Detailed Implementation
Every file to be created or changed, and why.
- `path/to/file` — what changes, and why.

## Constraints
Limits: time, tech, budget, policy.

## Success Criteria
How we'll know it works.

## Verification
The end-to-end check that proves the feature works.

## Assumptions
What we're taking as true.

## Decisions
Choices made, and why.

## Open Questions
Unresolved items.
````

## Rules

- Interview in plan mode. Stay read-only through classify, interview, design, and slicing; treat `ExitPlanMode` as the gate that finalizes and writes `spec.md`.
- Classify before interviewing. State the altitude (Epic / Feature / Task). Push back on Epics — make the user slice them into independent features first, and spec only one slice per session.
- Every slice must be a vertical slice — testable end-to-end value, not a layer in isolation. Reject backend-only, agent-only-without-wiring, and frontend-on-stubs. When end-to-end gets too big, narrow the behavior (one happy path, one user), never drop the layers. Optimize for value a user can test fast.
- Interview before drafting. No full spec from one prompt.
- Ask in small batches; one topic at a time. Don't overwhelm.
- Propose the design yourself, in prose and a block diagram — don't ask the user to propose first.
- Resist sycophancy. Challenging the user's thinking is the helpful behavior, not agreeing. If the session slides into easy agreement, push back and name the risks. When challenged ("why do you think that?"), re-examine your reasoning instead of folding.
- Document rejected alternatives — they keep later work from sliding back into a ruled-out approach.
- Don't jump to implementation while still framing the problem; reach the technical plan only after the slices are agreed.
- Keep slices independent, valuable, and end-to-end.
- No implementation or design detail beyond the spec's own sections unless the user asks.
- Be concise. Cut filler words.
- Capture assumptions, decisions, open questions, and non-goals as you go.

## Final Output

A clean `spec.md` with the sections above filled in — problem, technical plan, alternatives, detailed implementation, and verification, alongside the product framing. Concise, no bloat. Leave open questions visible rather than guessing.
