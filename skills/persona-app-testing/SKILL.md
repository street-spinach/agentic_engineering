---
name: persona-app-testing
description: >-
  Verify a freshly-built mobile app with FRESH EYES — exploratory, persona-driven
  testing that catches what the developer is blind to. Study the app (source +
  the running build), derive a handful of realistic user personas, walk each
  persona through their goal journeys on the simulator/emulator, and produce one
  readable Markdown report covering both whether flows WORK and where they cause
  friction. Use this skill after building or changing an app and the user wants to
  "verify it", "test it like a real user", "do a usability / UX pass", "find what
  I missed", "QA the build", "check it with fresh eyes", "run persona testing", or
  "make sure it actually works before shipping". This is the layer ABOVE the
  ios-app-testing and android-app-testing skills — it orchestrates their helpers
  (boot / install / launch / find / tap / wait-text / screenshot / crashes) rather
  than reimplementing device control. Picks iOS or Android per run based on what
  the app and machine support.
---

# Persona app testing — verifying a build with fresh eyes

You just built (or changed) an app. You know the happy path by heart, which is
exactly why you can't see its rough edges. This skill borrows other people's eyes:
you derive a small set of realistic **personas**, then walk each one through the
goals they came to the app for — *as they would, not as you would* — and report
both **functional** outcomes (did the journey work) and **UX friction** (where it
fought them).

It does not drive the device itself. It **orchestrates** the platform skills:

- **iOS** → `ios-app-testing` (`scripts/sim_test.py`, simctl + idb)
- **Android** → `android-app-testing` (`scripts/adb_test.py`, ADB)

Both expose the **same command names** — `boot`, `install`, `launch`, `find`,
`tap-id` / `tap-text` (Android) / `tap-label` (iOS), `type`, `wait-text`,
`assert-text`, `screenshot`, `crashes`. So a journey reads almost identically on
either platform; only the selectors and the launch identifier differ. Read the
relevant platform SKILL before driving — it owns the device rules (especially
**OBSERVE → ACT → WAIT**, which still governs every step here).

## The one discipline that makes this worth doing: stay in fresh eyes

You study the source to know *what the app is supposed to do* and *who its users
are*. You do **not** use that insider knowledge to breeze through the flow. When
executing a journey:

- **Navigate by what's on screen**, the way a real user would — read the visible
  labels with `find` / `describe` / `dump`, not the resource-ids you happen to
  know from the code. If a button is mislabeled or buried, the persona should get
  stuck exactly where a real user would.
- **Honor the persona's constraints.** An impatient user doesn't read the
  onboarding copy; a low-vision user relies on accessibility labels; a non-native
  speaker takes button text literally. Let those constraints change what you tap.
- **Record friction, don't route around it.** The moment you think "a real user
  would be confused here" — that *is* the finding. Note it; don't quietly fix it
  in your head and move on.

The source study makes you a better test *designer*. The execution must stay
naive. Holding that tension is the whole skill.

## Step 0 — Pick the platform and confirm the environment

Decide which platform(s) to test, then hand off to that skill's **Step 0** to
verify the toolchain — don't re-implement those checks here.

- If the user named a platform, use it. Otherwise infer from the project (a
  `*.xcodeproj` / `.app` / `Package.swift` → iOS; `build.gradle` / `*.apk` /
  `AndroidManifest.xml` → Android) and from what the machine can run (iOS needs
  macOS + Xcode). If both are viable and the user didn't say, **ask** which one
  (or both) before booting — don't assume.
- Then run the platform skill's environment checks (`xcrun simctl …` / `idb
  list-targets`, or `adb version` / `emulator -list-avds`). Surface any gap to the
  user rather than trying to install SDKs yourself.

Boot **headless** — neither a Simulator window nor an emulator window is needed;
screenshots and UI dumps work windowless on both. (iOS is headless by default;
Android is now headless by default too — pass `--show` on either only if the user
wants to watch.)

## Step 1 — Study the app → build an "app map"

Look at the app from both sides so personas and journeys are grounded in reality,
not guesses.

- **White-box (read the source + artefacts).** Map the screens, primary flows,
  navigation, key features, and the user-facing strings. Read `ARCHITECTURE.md`,
  `docs/adr/`, any product/spec docs, and the screen/route definitions. Note the
  intended happy paths *and* the edges the code hints at (error states, empty
  states, permission gates, paywalls, locale handling).
- **Black-box (crawl the running build).** Boot → install → launch via the
  platform helper, then walk the reachable screens: `screenshot` each, `dump` /
  `describe-all` to see what's actually exposed (labels, ids, tappables). This
  ground-truths the source map — screens that exist in code but are unreachable,
  or labels that differ from the strings file, are themselves signals.
- **If there's no source** (testing a prebuilt APK/.app only), skip white-box and
  build the map from the crawl alone. Say so in the report — the persona set will
  be coarser.

Write the map down (a short list of screens + the goals the app clearly supports).
It's the input to persona derivation and the journey list.

## Step 2 — Derive personas, then confirm with the user (hybrid)

From the app map, synthesize **3–6 personas** — enough to cover distinct user
shapes, few enough to actually run. Each persona must be *grounded*: tie it to
something the app does, not a generic stereotype. For each, capture:

- a **name + one-line bio**, their **goal(s)** in this app, and their **traits /
  constraints** (tech-savviness, patience, accessibility needs, device/locale,
  motivation) — the traits are what will bend their behavior during execution.
- a **rationale**: why this persona, and what about the app made you pick them.

`references/persona-archetypes.md` has a starter library of archetypes and the
trait axes to vary across — use it to avoid blind spots, not as a fixed cast.

**Then present the set to the user and let them confirm, cut, or add** before you
test anything. This is the one human gate in the skill: testing the wrong people
wastes the whole run. If the user gave you personas up front, skip the synthesis
and just confirm coverage.

## Step 3 — Turn each persona into goal journeys

For every confirmed persona, define one or more **journeys** — a concrete,
goal-oriented path through the app, written from their point of view:

- **Goal:** what they're trying to accomplish ("sign up and see my first
  dashboard").
- **Success criteria:** the observable end-state that means they made it (a
  `wait-text` / `assert-text` target).
- **Friction lens:** what to watch for given *this* persona (e.g. for the
  impatient newcomer: step count, unexplained waits, jargon; for the low-vision
  user: missing accessibility labels, tap-target size, contrast you can judge from
  the screenshot).

Keep journeys small and independent so one failure doesn't cascade. Reset between
them with the platform's clean-slate step (`clear` on Android; uninstall →
reinstall on iOS).

## Step 4 — Run each journey (observe → act → wait), in persona

Drive the journey through the platform helper, capturing evidence at every beat so
the run reads like a storyboard. Take a crash baseline first
(`logcat-clear` / `crash-mark`), then for each step:

1. **OBSERVE** — `dump` / `describe` / `find` to see what's actually on screen.
2. **ACT** — as the persona would: tap the label they'd recognize, type what
   they'd type, give up scrolling where they'd give up.
3. **WAIT** — `wait-text` for the next state before doing anything else.
4. **Screenshot** every meaningful state with an ordered, descriptive name
   (`p1_01_welcome.png`, `p1_02_signup_filled.png`, …), namespaced per persona.

When the persona would be **blocked or confused**, stop and record it as a finding
(see Step 5) rather than using insider knowledge to push through. A journey can
end in `pass` (reached the goal), `fail` (a step broke — crash, error, dead
control), or `blocked` (the persona couldn't find the way forward — itself a
high-value UX finding). After the flow, scan for crashes
(`crashes --package …` / `crashes --name …`).

## Step 5 — Evaluate: functional AND friction

Judge each journey on both axes:

- **Functional** — did it work? `pass` / `fail` / `blocked`, with the failing
  step and the evidence (screenshot, crash, missing element).
- **Friction** — where did it fight the persona? Score each finding
  **high / medium / low** against the heuristics in
  `references/friction-rubric.md` (discoverability, clarity of labels, effort /
  step count, feedback & latency, error recovery, accessibility, trust). Tie every
  finding to a screenshot and to the persona+step where it bit.

Keep the two distinct: a flow can fully *work* and still be a friction nightmare,
and a *blocked* journey is usually both a functional and a UX failure. Don't
inflate severity — a `low` that's clearly minor keeps the `high`s credible.

## Step 6 — Report in a readable format

Don't hand-format the report — assemble the results as JSON and let the helper
render consistent Markdown every run:

```bash
python scripts/persona_report.py results.json \
  --out artifacts/persona-tests/report.md \
  --generated "$(date -u +%FT%TZ)"
```

The JSON shape (one object; see `references/results-schema.md` for the full
spec and a filled example):

```jsonc
{
  "app":   { "name": "MyApp", "platform": "ios", "build": "Debug", "id": "com.example.MyApp" },
  "personas": [{
    "name": "Priya — impatient first-timer",
    "bio":  "Downloaded on mobile data, 30 seconds of patience.",
    "traits": ["low patience", "non-technical", "mobile-data only"],
    "rationale": "App's value is gated behind a 4-screen onboarding.",
    "journeys": [{
      "goal": "Sign up and reach the dashboard",
      "result": "blocked",
      "steps": [
        { "n": 1, "action": "Launch app", "observation": "Landed on splash", "screenshot": "artifacts/persona-tests/priya/p1_01_splash.png", "status": "ok" },
        { "n": 2, "action": "Tap 'Get started'", "observation": "Onboarding screen 1 of 4", "screenshot": "…/p1_02_onboard.png", "status": "warn" }
      ],
      "functional": { "status": "blocked", "detail": "No skip on onboarding; persona quit at screen 2." },
      "friction": [
        { "severity": "high", "heuristic": "effort", "title": "No way to skip onboarding", "detail": "4 mandatory screens before any value; impatient users bail.", "screenshot": "…/p1_02_onboard.png" }
      ]
    }]
  }]
}
```

The generated report opens with a summary (personas × journeys pass/fail grid and
a friction count by severity), then a section per persona — bio, then each journey
as a screenshot storyboard with its functional verdict and friction findings —
and ends with all findings sorted by severity. Embedded screenshots use relative
paths, so keep the report next to its `artifacts/` dir (default
`artifacts/persona-tests/`). Finally, give the user a short spoken summary: top
findings, anything that crashed, and where the report lives.

## Step 7 — Hand back

Leave the simulator/emulator as you found it unless asked — the user may want to
reproduce a finding. Defer teardown (`terminate`/`stop`, `shutdown`/`kill-emulator`)
to the platform skill's Step 6 only when the run is clearly throwaway.

## Worked shape (Android, abbreviated)

```bash
T="python ../android-app-testing/scripts/adb_test.py"     # the platform helper
$T boot --avd Pixel_7_API_34            # headless by default
$T install app/build/outputs/apk/debug/app-debug.apk
# --- per persona journey ---
$T clear com.example.app; $T logcat-clear; $T launch com.example.app
$T wait-text "Get started" --timeout 20
$T screenshot artifacts/persona-tests/priya/p1_01_welcome.png
$T find --by any "Skip"                 # impatient persona hunts for a skip…
# …none found -> record a 'high' friction finding, mark journey 'blocked'
$T crashes --package com.example.app
# repeat for each persona, collect into results.json, then:
python scripts/persona_report.py results.json --out artifacts/persona-tests/report.md
```

## Gotchas

- **Don't cheat the persona.** The most common failure of this skill is the agent
  using resource-ids and known coordinates from the source to sail through a flow
  a real user would fumble. If you didn't read the label off the screen, you're
  not testing with fresh eyes.
- **Personas are grounded, not decorative.** "Power user", "new user" with no tie
  to what the app does produce a generic report. Anchor each to a real goal the
  app map revealed.
- **Friction ≠ failure.** Report a working-but-painful flow as `pass` functionally
  with `high` friction — collapsing the two hides the most useful findings.
- **Compose, don't fork.** Drive devices only through the platform helpers; if one
  lacks a command, fix it in that skill, not here. This skill stays platform-shape
  and report-shape.
- **Severity discipline.** Inflated `high`s train the reader to ignore them. Reserve
  `high` for "a real user would abandon or fail here".

## Reference files

- `references/persona-archetypes.md` — a starter library of persona archetypes and
  the trait axes to vary across, so the cast covers real blind spots.
- `references/friction-rubric.md` — the UX heuristics and the high/medium/low
  severity scale used in Step 5, so findings are scored consistently.
- `references/results-schema.md` — the full `results.json` schema the report
  generator consumes, with a complete filled example.
