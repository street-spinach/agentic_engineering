---
name: Prompt Enhancer
description: >-
  Sharpen a rough or casual intent into one clear, direct, well-worded prompt for the
  coding agent. Use when a request is vague or messy and you want it to read solid
  before handing it over. Improves and tidies the wording — it does NOT rebuild the
  spec: scope, constraints, acceptance criteria, and verification stay in SPEC.md and
  are referenced, not restated. Keeps the prompt short.
---

# Prompt Enhancer

## Purpose

Take a rough intent and return a sharper, cleaner version of the same ask — clear,
direct, and tidy. It improves and "decorates" the prompt so it reads solid; it does
not expand it into a mini-spec. Anything SPEC.md already owns is referenced, not
repeated.

## When to Use

- The request is casual, vague, or awkwardly worded ("make login better", "fix the slow page").
- You want the ask to read clean before handing it to the coding agent.
- Skip it when the prompt is already sharp, or when the real gap is spec-level (use Spec Interviewer instead).

## Principles

- Clarity and directness: state the ask plainly, in active voice.
- Specific where it's cheap: name the obvious target (file, component, flow).
- Keep the intent: sharpen the wording, don't change what was asked.
- Defer to the spec: scope, constraints, acceptance criteria, and verification live in SPEC.md — reference it, don't restate it.
- Stay short: a sentence or a few. Cut filler; no scaffolding fields.

## Workflow

1. Read the raw intent.
2. Fix vagueness and tighten the wording; name the target if it's obvious.
3. If the details live in SPEC.md, point to it instead of inlining them.
4. Return the improved prompt — nothing else.

## Example

Raw: "fix the slow dashboard"
Enhanced: "Diagnose and fix the slow initial load on the dashboard, per SPEC.md."

## Rules

- Produce the improved prompt only — don't implement, and don't write a spec.
- Don't restate what SPEC.md / TASKS.md own; reference them.
- Shorter is better: prefer the tightest wording that removes the ambiguity.
- One ask per prompt; split a multi-part intent.
