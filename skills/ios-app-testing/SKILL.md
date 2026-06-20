---
name: ios-app-testing
description: >-
  Run black-box UI tests against an iOS app on the iOS Simulator using xcrun
  simctl (lifecycle, screenshots, permissions) plus idb (tap/type/swipe and
  accessibility inspection). Use this skill whenever the user wants to test an
  iOS app, launch a .app/.ipa in the iOS Simulator and verify it works, automate
  iOS UI flows, take screenshots of an app's screens, smoke-test an iOS build,
  reproduce a bug on the Simulator, or set up iOS UI testing. Trigger even when
  the user only says things like "test my iOS app", "check the login screen on
  iPhone", "does my app work in the simulator", or mentions the iOS Simulator, a
  simulator UDID, simctl, idb, a .app bundle, or a bundle id in a testing
  context. REQUIRES macOS with Xcode, and idb installed (brew + pip) for the UI
  interaction parts.
---

# iOS app testing on the Simulator (simctl + idb)

Drive an iOS app on the Simulator as a **black box** — no source code, no XCUITest
target. This is the iOS counterpart to the Android ADB skill, but iOS splits the
job across two tools because, unlike `adb`, the built-in tooling can't touch the
UI:

- **`xcrun simctl`** (ships with Xcode, nothing to install) — the *lifecycle* half:
  boot, install, launch, terminate, screenshot, record, logs, permissions, deep
  links, appearance, status-bar overrides, erase.
- **`idb`** ("iOS Development Bridge"; one-time `brew` + `pip install fb-idb`) — the
  *interaction* half: `tap` / `text` / `swipe` / hardware buttons, and
  `describe-all`, the accessibility-hierarchy dump we match elements against.
  `simctl` has no tap/type/inspect command, which is why idb is required.

A helper, `scripts/sim_test.py` (Python stdlib only), wraps both behind one CLI
with the same command names as the Android helper. Prefer it for routine steps;
drop to raw `simctl`/`idb` for anything it doesn't cover — the full catalogue is in
`references/simctl-idb-reference.md`.

> **macOS only.** The iOS Simulator and Xcode toolchain run only on macOS. There is
> no Linux/Windows path. If `idb` isn't installed yet, see the install block in
> `references/troubleshooting.md` before Step 1.

## The one rule that makes tests reliable: OBSERVE → ACT → WAIT

iOS UIs animate and load asynchronously, so never act and immediately assert:

1. **OBSERVE** the current screen — `describe`, `find`, or `screenshot`.
2. **ACT** — `tap-label` / `tap-id` / `type` / `key` / `swipe`.
3. **WAIT** for the *next* state — `wait-text` polls the accessibility tree until an
   expected element shows up (or it times out and fails the test).

`wait-text` is the workhorse. Fixed `sleep`s instead of waiting on a concrete
element are the most common cause of flaky iOS tests.

## Step 0 — Confirm the environment

```bash
xcrun simctl help >/dev/null && echo "simctl OK"     # Xcode tools present?
xcrun simctl list devices available                  # which simulators exist?
idb list-targets                                      # idb installed + companion up?
```

If `idb` is missing, install it (see `references/troubleshooting.md`):
`brew install idb-companion` then `pip3 install fb-idb`. If there are no
simulators, create one in Xcode → **Settings → Components** (download a runtime),
then **Window → Devices and Simulators**. Don't try to download Xcode itself —
surface that gap to the user.

## Step 1 — Boot a simulator

```bash
# Boots the named simulator if not already up, waits for a FULL boot, prints UDID.
python scripts/sim_test.py boot --device "iPhone 15"
# Add --show to also open the Simulator GUI window (otherwise it runs windowless):
python scripts/sim_test.py boot --device "iPhone 15" --show
```

Capture the printed UDID. If several simulators are booted, pass `--udid <id>` to
later commands or `export SIM_UDID=<id>` once. A simulator runs fine without the
GUI window open — `screenshot`, `describe`, and taps all work either way.

## Step 2 — Install (or build then install) the app

iOS Simulators take a **`.app` bundle** (a directory), not a device `.ipa`:

```bash
python scripts/sim_test.py install path/to/MyApp.app
```

If the user has a **source project**, build a simulator `.app` first, then install
the product. The `.app` lands under DerivedData:

```bash
xcodebuild -scheme MyApp -sdk iphonesimulator -configuration Debug \
  -derivedDataPath build build
python scripts/sim_test.py install build/Build/Products/Debug-iphonesimulator/MyApp.app
```

You need the app's **bundle identifier** (e.g. `com.example.MyApp`) to launch it.
If you don't know it, read it from the build settings or the installed app's
`Info.plist` — see `references/simctl-idb-reference.md` ("Finding the bundle id").

## Step 3 — Launch the app

```bash
python scripts/sim_test.py launch com.example.MyApp
# Relaunch from scratch (kill any running instance first):
python scripts/sim_test.py launch com.example.MyApp --fresh
```

Confirm it actually came up rather than crashing on launch:

```bash
python scripts/sim_test.py running com.example.MyApp     # exit 1 if not alive
```

iOS has no externally-visible "current activity" like Android — navigation happens
inside the app. So you confirm which screen you're on with `wait-text` /
`assert-text` against the accessibility tree, not an activity name.

## Step 4 — Run the test: observe, act, wait, assert

Mark the crash baseline first, so crash detection is scoped to this run:

```bash
python scripts/sim_test.py crash-mark
python scripts/sim_test.py wait-text "Welcome" --timeout 20     # first screen is up
python scripts/sim_test.py screenshot artifacts/01_home.png
```

Then interact. Find elements by **AXLabel** (accessibility label), **AXUniqueId**
(accessibility identifier — set these in the app for stable selectors), or
**type** — these are stable; raw coordinates are not. Use `find` first when unsure
what's on screen; it prints each match with its centre and type:

```bash
python scripts/sim_test.py find --by label "Log In"
python scripts/sim_test.py tap-id  email_field
python scripts/sim_test.py type    "test@example.com"
python scripts/sim_test.py tap-id  pwd_field
python scripts/sim_test.py type    "hunter2" --enter
python scripts/sim_test.py tap-label "Log In"

# WAIT for the result of that tap before asserting on it:
python scripts/sim_test.py wait-text "Your dashboard" --timeout 25
python scripts/sim_test.py screenshot artifacts/02_dashboard.png
python scripts/sim_test.py assert-text "Welcome, test"      # exits 1 if absent
```

**Assertions and exit codes.** `assert-text` and `wait-text` exit `1` when the
expected thing isn't there (a normal *failed test*), `0` on success, and `2` on an
environment error — so they compose under `set -e` in a shell test script.

**Reset between independent tests.** iOS has no per-app "clear data" like Android's
`pm clear`. The clean reset is uninstall → reinstall → relaunch (or `erase` the
whole simulator for a factory-fresh state):

```bash
python scripts/sim_test.py uninstall com.example.MyApp
python scripts/sim_test.py install   path/to/MyApp.app
python scripts/sim_test.py launch    com.example.MyApp
```

## Step 5 — Check for crashes, then report

After the flow, scan for crash reports generated since the mark you set:

```bash
python scripts/sim_test.py crashes --name MyApp     # exit 1 if any new crash report
```

(Crash reports land on the Mac under `~/Library/Logs/DiagnosticReports/`; the helper
compares modification times against the mark.) Then summarise for the user: which
steps passed, which failed and why, whether the app stayed alive, any crashes, and
the screenshots captured (e.g. under `artifacts/`). Keep screenshot names ordered
and descriptive so the run reads like a storyboard.

## Step 6 — Teardown

```bash
python scripts/sim_test.py terminate com.example.MyApp
# Optionally shut the simulator down (skip if the user wants it kept open):
python scripts/sim_test.py shutdown
```

Don't shut the simulator down or uninstall unless asked or it's clearly a
throwaway — the user may want to keep poking at it.

## Worked example — a login smoke test as a shell script

```bash
#!/usr/bin/env bash
set -euo pipefail
T="python scripts/sim_test.py"
APP="build/Build/Products/Debug-iphonesimulator/MyApp.app"
BID="com.example.MyApp"
mkdir -p artifacts

$T boot --device "iPhone 15"
$T uninstall "$BID" || true      # clean slate; ignore "not installed"
$T install "$APP"
$T crash-mark
$T launch "$BID"
$T running "$BID"

$T wait-text "Welcome" --timeout 20
$T screenshot artifacts/01_login.png
$T tap-id email_field;   $T type "test@example.com"
$T tap-id pwd_field;     $T type "hunter2"
$T tap-label "Log In"

$T wait-text "Your dashboard" --timeout 25   # fails the run if login didn't land
$T screenshot artifacts/02_dashboard.png
$T assert-text "Welcome, test"
$T crashes --name MyApp
echo "PASS: login smoke test"
```

## Gotchas (full list in references/troubleshooting.md)

- **`describe-all` is missing elements you can see:** idb sometimes omits elements
  nested inside a `Group` container (a known idb limitation, since it uses private
  Apple accessibility APIs). Fall back to a screenshot + coordinate `tap`, or
  `idb ui describe-point X Y` to read one spot.
- **Element has no AXLabel:** match on `AXUniqueId` (accessibility identifier) or
  `type` instead. The best fix is in the app — set
  `.accessibilityIdentifier` / SwiftUI `.accessibilityIdentifier(...)` on key views
  so they're addressable.
- **idb is flaky or errors out:** it can intermittently fail (private-API quirk) and
  can lag the newest Xcode. The helper retries `describe-all`; if idb is broken on
  your Xcode version, see troubleshooting for version-pinning and reinstall steps.
- **`type` goes nowhere:** no field is focused — `tap-id`/`tap-label` the field
  first, then `type`.

## Reference files

- `references/simctl-idb-reference.md` — the full raw `simctl` + `idb` command
  catalogue (lifecycle, screenshots/recording, permissions, deep links, UI
  interaction, accessibility dump) and the idb key/button codes. Read it when the
  helper doesn't cover what you need.
- `references/troubleshooting.md` — install steps for idb, plus fixes for boot
  problems, describe-all gaps, missing labels, permission dialogs, and idb/Xcode
  version friction. Read it the moment something misbehaves.