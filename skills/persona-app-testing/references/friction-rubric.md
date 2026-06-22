# UX friction rubric

Use this to score friction findings consistently in SKILL Step 5. A finding is a
place where the app *fought the persona* — distinct from a functional failure
(crash, error, dead control). A flow can fully work and still be riddled with
friction; report both.

Every finding gets a **heuristic** (which dimension it offends) and a **severity**
(high / medium / low), and must point at a **screenshot** and the **persona+step**
where it bit.

## The heuristics (the `heuristic` field)

- **discoverability** — can the persona *find* the path forward? Hidden entry
  points, unlabeled icon buttons, actions buried in menus, no search when the data
  demands it.
- **clarity** — do labels and copy mean what they say? Jargon, ambiguous buttons,
  idioms a non-native speaker misreads, unexplained states.
- **effort** — how much work to reach the goal? Excess taps/steps, long mandatory
  forms, no skip/shortcut, repetition, no defaults.
- **feedback** — does the app tell the persona what's happening? Missing loading
  indicators, no confirmation of success, unexplained waits, silent failures.
- **error-recovery** — when something goes wrong, can they get out? No undo, harsh
  or unclear validation, no confirmation before destructive actions, dead-ends
  with no Back.
- **accessibility** — can a constrained user operate it? Missing accessibility
  labels (judge from `dump`/`describe-all`), tiny/crowded tap targets, low
  contrast, layout that breaks at large text (judge from screenshots).
- **trust** — does the app earn what it asks? Permission/payment/account requests
  before delivering value, unclear pricing, weak first impression, asking for
  sensitive data without reason.

## Severity scale (the `severity` field)

- **high** — *a real user would abandon, fail, or be harmed here.* The persona
  can't complete their goal, loses data, is blocked, hits a crash-equivalent
  dead-end, or is pushed into an action they didn't intend. A `blocked` journey
  almost always contains at least one `high`.
- **medium** — *significant friction; the persona pushes through but is annoyed or
  delayed.* Confusing labels they eventually decode, several wasted steps, missing
  feedback that causes a double-tap or a worried pause, an accessibility gap that
  slows but doesn't stop a constrained user.
- **low** — *a papercut.* Cosmetic or minor: slightly-off copy, a small
  inconsistency, a nice-to-have shortcut that's missing. Real, worth noting, but
  no user abandons over it.

## Keeping severity honest

- **Calibrate to abandonment, not to taste.** "I'd have designed it differently"
  is not a finding. "This persona, with these traits, would quit here" is a `high`.
- **Don't inflate.** Every `high` that isn't really high trains the reader to
  ignore the `high` column. When unsure between two levels, pick the lower and say
  why in the detail.
- **Tie severity to the persona.** The same screen can be `low` for the power user
  and `high` for the low-vision user — score it *for the persona who hit it*. That
  per-persona lens is the point of the whole skill.
- **One finding per problem.** If the same missing label bites three personas,
  it's still one underlying issue — note that it recurs rather than triple-counting
  it, and score it at its worst observed severity.
