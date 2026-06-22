# `results.json` schema

The shape `scripts/persona_report.py` consumes. One top-level object: an `app`
block plus a `personas` array. Unknown fields are ignored, and most fields are
optional — the report degrades gracefully (a journey with no `steps` just omits
its storyboard). Screenshot paths are interpreted relative to the directory you
run the report from; the generator rewrites them relative to `--out` so they embed
correctly.

## Fields

```
app                     object   build/run metadata (all optional)
  .name                 string   shown in the report title
  .platform             string   "ios" | "android"
  .build                string   e.g. "Debug"
  .id                   string   bundle id / package name

personas[]              array    REQUIRED — the cast you tested
  .name                 string   persona name (shown as a section heading)
  .bio                  string   one-line bio (italicised under the heading)
  .traits[]             string[] the constraints you acted on
  .rationale            string   why this persona for this app

  .journeys[]           array    one goal-oriented path each
    .goal               string   what they tried to do
    .result             string   "pass" | "fail" | "blocked"
    .functional         object
       .status          string   "pass" | "fail" | "blocked"
       .detail          string   what happened / why it failed
    .steps[]            array     the storyboard, in order
       .n               number    step index (1,2,3…)
       .action          string    what the persona did
       .observation     string    what they saw next
       .status          string    "ok" | "warn" | "fail"
       .screenshot      string    path to the evidence PNG
    .friction[]         array     UX findings (see friction-rubric.md)
       .severity        string    "high" | "medium" | "low"
       .heuristic       string    discoverability|clarity|effort|feedback|
                                  error-recovery|accessibility|trust
       .title           string    short finding name
       .detail          string    what bit the persona, and why
       .screenshot      string    path to the evidence PNG
```

`result` / `status` values outside the known set are printed verbatim (no badge),
so a typo shows up in the report rather than crashing the run.

## Filled example

```json
{
  "app": { "name": "MyApp", "platform": "android", "build": "Debug", "id": "com.example.app" },
  "personas": [
    {
      "name": "Priya — impatient first-timer",
      "bio": "Downloaded on the bus on mobile data, ~30s of patience, non-technical.",
      "traits": ["low patience", "non-technical", "mobile-data only"],
      "rationale": "The app gates all value behind a 4-screen onboarding; impatient newcomers are the likeliest churn.",
      "journeys": [
        {
          "goal": "Sign up and reach the dashboard",
          "result": "blocked",
          "functional": { "status": "blocked", "detail": "No skip control on onboarding; persona quit at screen 2 of 4 before reaching sign-up." },
          "steps": [
            { "n": 1, "action": "Launch app", "observation": "Splash, then onboarding screen 1", "status": "ok", "screenshot": "artifacts/persona-tests/priya/p1_01_splash.png" },
            { "n": 2, "action": "Look for a way past onboarding", "observation": "No Skip/Next-to-end; only a small 'Continue'", "status": "warn", "screenshot": "artifacts/persona-tests/priya/p1_02_onboard.png" },
            { "n": 3, "action": "Tap Continue twice, hunting for sign-up", "observation": "Still in onboarding (screen 3 of 4)", "status": "fail", "screenshot": "artifacts/persona-tests/priya/p1_03_onboard3.png" }
          ],
          "friction": [
            { "severity": "high", "heuristic": "effort", "title": "No way to skip onboarding", "detail": "Four mandatory screens before any value or a sign-up entry point; an impatient user abandons here.", "screenshot": "artifacts/persona-tests/priya/p1_02_onboard.png" },
            { "severity": "medium", "heuristic": "discoverability", "title": "'Continue' easy to miss", "detail": "Low-contrast text button bottom-right; competes with nothing but is visually quiet.", "screenshot": "artifacts/persona-tests/priya/p1_02_onboard.png" }
          ]
        }
      ]
    },
    {
      "name": "Sam — returning power user",
      "bio": "Daily user with hundreds of saved items; wants speed.",
      "traits": ["high tech-savviness", "large existing data", "low patience for taps"],
      "rationale": "App map shows no search on the main list; power users with lots of data feel that most.",
      "journeys": [
        {
          "goal": "Find and open a specific saved item",
          "result": "pass",
          "functional": { "status": "pass", "detail": "Item reached via manual scroll; flow works." },
          "steps": [
            { "n": 1, "action": "Open saved list", "observation": "Long unsearchable list", "status": "warn", "screenshot": "artifacts/persona-tests/sam/p1_01_list.png" },
            { "n": 2, "action": "Scroll to target item", "observation": "Found after ~40 items", "status": "ok", "screenshot": "artifacts/persona-tests/sam/p1_02_found.png" }
          ],
          "friction": [
            { "severity": "high", "heuristic": "effort", "title": "No search/filter on saved list", "detail": "With hundreds of items the only way to a known item is manual scroll — works, but punishing at scale.", "screenshot": "artifacts/persona-tests/sam/p1_01_list.png" }
          ]
        }
      ]
    }
  ]
}
```
