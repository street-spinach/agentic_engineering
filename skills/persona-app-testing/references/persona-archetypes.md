# Persona archetypes & trait axes

This is a *starter library*, not a fixed cast. The goal is to pick 3–6 personas
that cover the blind spots in **this** app — so always ground each one in a goal
the app map (SKILL Step 1) actually surfaced. A persona with no tie to what the
app does produces a generic, useless report.

## How to choose a covering set

Don't pick six variations of the same person. Vary deliberately across the trait
axes below so the set spans real differences in who uses the app:

| Axis | Low end | High end | Why it changes behavior |
|---|---|---|---|
| **Tech-savviness** | never-used-this-kind-of-app | power user / developer | what they recognize, how fast they recover from a dead-end |
| **Patience** | bails after ~30s of friction | will grind through anything | whether they read onboarding, retry, or quit |
| **Goal clarity** | browsing, unsure what they want | knows the exact task | how they navigate — wandering vs. beelining |
| **Accessibility** | low vision / motor / cognitive load | no needs | reliance on labels, tap-target size, contrast, text size |
| **Trust / caution** | privacy-anxious, reads permissions | clicks "allow" reflexively | behavior at permission gates, sign-up, payment |
| **Context** | one-handed on mobile data, interrupted | wifi, focused, two hands | tolerance for latency, large downloads, long forms |
| **Locale / language** | non-native speaker, RTL, other region | native, default locale | how literally they read labels; layout/format breakage |
| **Account state** | brand-new, empty data | returning, lots of data | empty states vs. full states; onboarding vs. deep features |

A good set usually mixes a **first-timer**, a **returning/power user**, an
**accessibility-constrained** user, and at least one **edge-context** user
(low-connectivity, non-native, privacy-anxious) — adjusted to the app.

## Archetypes to draw from

Treat each as a seed: rename it, give it a real goal from the app map, and pin the
traits that will actually bend its behavior.

- **The impatient first-timer.** Just installed it, ~30s of patience, skips copy,
  expects value immediately. Surfaces: heavy onboarding, no skip, unexplained
  waits, jargon, mandatory sign-up before any payoff.
- **The cautious newcomer.** New, but reads before tapping; privacy- and
  cost-aware. Surfaces: scary/unclear permission prompts, hidden pricing,
  ambiguous destructive actions, missing reassurance copy.
- **The returning power user.** Knows the app, wants speed and shortcuts, has lots
  of existing data. Surfaces: too many taps for common tasks, no search/filters,
  poor handling of large data sets, missing keyboard/quick actions.
- **The low-vision user.** Relies on accessibility labels, larger text, and
  contrast. Surfaces: unlabeled controls (icon-only buttons), tiny tap targets,
  low-contrast text, layout that breaks at large text sizes. (You can judge labels
  from `dump`/`describe-all` and contrast/target-size from screenshots.)
- **The motor-impaired / one-handed user.** Limited reach and precision, often
  one thumb. Surfaces: tiny or crowded targets, controls in hard-to-reach corners,
  gestures with no button alternative, accidental destructive taps.
- **The interrupted multitasker.** Gets pulled away mid-flow (call, app switch,
  screen lock). Surfaces: lost form state, broken resume, re-auth loops, work
  silently discarded on backgrounding.
- **The low-connectivity user.** Slow or flaky network, on mobile data. Surfaces:
  no loading feedback, no offline/empty handling, silent failures, huge downloads,
  timeouts with no retry.
- **The non-native speaker / other locale.** Reads labels literally, may use a
  different region/RTL. Surfaces: idiomatic or ambiguous labels, untranslated or
  truncated strings, date/number/currency format breakage, layout overflow.
- **The skeptical evaluator.** Deciding whether to keep the app; trust-sensitive.
  Surfaces: weak first impression, unclear value prop, asking for too much too
  soon (permissions, payment, account) before earning it.
- **The error-prone fat-finger.** Mistypes, taps the wrong thing, hits Back.
  Surfaces: no undo, harsh validation, no confirmation on destructive actions,
  state lost on an accidental Back press.

## Writing a persona down

Each confirmed persona needs exactly what the journey execution and report will
use:

- **name + one-line bio** — concrete enough to roleplay ("Priya, 52, downloaded on
  the bus on mobile data, 30 seconds of patience").
- **goal(s)** — what they came to the app to do (drives the journeys in Step 3).
- **traits / constraints** — the 2–4 that will actually change their behavior
  during execution; don't list traits you won't act on.
- **rationale** — why this persona for this app, and what in the app map prompted
  them. This is what lets the user sanity-check the cast at the confirm gate.
