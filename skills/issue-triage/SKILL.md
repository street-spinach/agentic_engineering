---
name: Issue Triage
description: Classify a GitHub issue by type (bug vs feature/other) and complexity (low/medium/high), then route it down the cheapest correct path — low/medium bugs straight to implementation, everything else to spec, and only medium/high complexity through the harden gate. Parks issues too vague to classify or reproduce. Routes only; never writes product code. The entry filter for /issue-loop.
---

# Issue Triage

## Purpose

The entry filter for `/issue-loop`. It decides how much process an issue earns —
no more, no less. Trivial bugs shouldn't pay the spec+harden tax; risky or
ambiguous work shouldn't skip it. Triage maps each issue to the **cheapest correct
path** and hands `/issue-loop` a routing verdict plus a small seed for the next
step. It classifies; it never implements.

## When to Use

Invoked by `/issue-loop` once per fetched issue, before any spec or code. Not a
standalone entry point — for a single hand-authored feature, use the normal
`/spec-interviewer` front door instead.

## Inputs

The issue number, title, body, labels, and comments, plus any linked/blocking
issues and the code areas the text points at.

## Routing

| Type            | Complexity     | Route                          |
|-----------------|----------------|--------------------------------|
| Bug             | low / medium   | `implement` (skip spec)        |
| Bug             | high           | `spec` → harden → implement    |
| Feature / other | low            | `spec` → implement (no harden) |
| Feature / other | medium / high  | `spec` → harden → implement    |

- The **spec gate** is skipped only for low/medium bugs.
- The **harden gate** (`/harden-spec`) fires whenever complexity is medium or high.
- **Park** is orthogonal to the table: if the issue can't be classified or
  reproduced from the available evidence, route `park` regardless of complexity.

## Complexity Heuristic

- **low** — localized and well understood: a single file/area, a clear repro, an
  obvious fix shape.
- **medium** — several files/areas, or a few unknowns to resolve, but no
  architectural or contract change.
- **high** — cross-cutting, architectural, ambiguous root cause, or a
  migration / API-contract change.

When in doubt between two levels, pick the higher one — under-processing risky work
is the more expensive mistake.

## Hard Rules

- **Classify from evidence** in the issue (text, repro steps, linked code), not
  assumptions about what the reporter "probably" meant.
- **Route per the table** — never let a medium/high item skip the harden gate.
- **Park, don't guess.** If the issue lacks enough detail to spec or reproduce,
  route `park`: label it `needs-human`, comment naming exactly what's missing, and
  return so `/issue-loop` skips it. A guessed fix on a vague issue is worse than a
  parked one.
- **Triage only.** Emit a routing verdict and a seed — never product code, never a
  commit.

## Output

A compact verdict for `/issue-loop` to act on:

```
{ issue: <n>, type: bug|feature, complexity: low|medium|high,
  route: implement | spec | spec+harden | park,
  seed: <for implement: expected behaviour + acceptance, drawn from the issue;
         for spec routes: the spec seed (problem, repro, affected surface);
         for park: the list of missing information> }
```

## Failure Behavior

- **Unlabelled / no body** → if nothing classifiable, `park` with a comment.
- **Conflicting signals** (e.g. labelled bug but reads as a feature) → favour the
  higher-process route and note the ambiguity in the seed.
- **Looks like several issues in one** → flag for splitting; park unless one clear
  sub-fix dominates.
