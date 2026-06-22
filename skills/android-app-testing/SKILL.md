---
name: android-app-testing
description: >-
  Run black-box UI tests against an Android app on an emulator using only ADB
  (no Appium, no Maestro, nothing to install beyond the Android SDK). Use this
  skill whenever the user wants to test an Android app, launch an APK or AVD in
  an emulator and verify it works, automate Android UI flows, take screenshots
  of an app's screens, smoke-test a build, reproduce a bug on an emulator, or
  set up Android UI testing. Trigger even when the user only says things like
  "test my app", "check my Android app works", "does the login screen work", or
  mentions an emulator, AVD, .apk file, or `adb` in any testing context. Assumes
  the Android SDK + emulator are available locally (e.g. running under Claude
  Code on the user's machine).
---

# Android app testing over ADB

Drive an Android app on an emulator as a **black box** — no source code, no
instrumentation, no extra frameworks. Everything runs through `adb` and the
on-device `input`, `uiautomator`, `screencap`, `am`, `pm`, and `logcat` tools.

A helper, `scripts/adb_test.py` (Python stdlib only — nothing to install), wraps
the fiddly parts: boot polling, binary-safe screenshots, UI dumps, element
finding by text/id/description, tap-by-element, and crash detection. Prefer it
for routine steps; drop to raw `adb` for anything it doesn't cover (the full
command catalogue is in `references/adb-reference.md`).

## The one rule that makes tests reliable: OBSERVE → ACT → WAIT

Android UIs are asynchronous. A tap kicks off navigation, animation, and network
work that finish *later*. So never act and immediately assert. The loop is:

1. **OBSERVE** the current screen — `dump`, `find`, `screenshot`, or `current-activity`.
2. **ACT** — `tap-text` / `tap-id` / `type` / `key` / `swipe`.
3. **WAIT** for the *next* state to actually arrive — `wait-text` polls the UI
   until an expected element shows up (or it times out and fails the test).

`wait-text` is the workhorse. Reaching for fixed `sleep`s instead is the most
common cause of flaky Android tests — use it sparingly and prefer waiting on a
concrete element.

## Step 0 — Confirm the environment

Before anything, verify the toolchain is present. Run these and read the output:

```bash
adb version                 # platform-tools installed?
emulator -list-avds         # at least one AVD to boot?
adb devices                 # anything already attached?
echo "$ANDROID_HOME / $ANDROID_SDK_ROOT"
```

If `adb`/`emulator` aren't found, they live under the SDK
(`$ANDROID_HOME/platform-tools` and `$ANDROID_HOME/emulator`); add those to
`PATH`. If there are **no AVDs**, the user must create one (e.g. in Android
Studio's Device Manager, or `avdmanager create avd`); see
`references/troubleshooting.md`. Don't try to download the SDK yourself — surface
the gap to the user.

## Step 1 — Get an emulator running and booted

```bash
# Boots the named AVD if nothing suitable is running, waits for a FULL boot
# (not just the lock screen), disables animations, and prints the serial.
# Headless by default — no emulator window opens (uses -no-window + swiftshader).
python scripts/adb_test.py boot --avd Pixel_7_API_34
# Add --show to also open the emulator GUI window:
python scripts/adb_test.py boot --avd Pixel_7_API_34 --show
```

Capture the printed serial. If several devices are attached, pass `--serial <id>`
to later commands or `export ANDROID_SERIAL=<id>` once. A "booted" device can
still take a few seconds before the launcher is interactive — the first
`wait-text` will absorb that. Headless and windowed behave identically —
`screenshot`, `find`, taps, and UI dumps all work either way.

## Step 2 — Install (or build then install) the app

```bash
# Prebuilt APK — -r (replace) and -g (grant runtime permissions) are the default.
python scripts/adb_test.py install path/to/app-debug.apk
```

If the user has a **source project** instead of an APK, build first, then install
the produced artifact:

```bash
./gradlew assembleDebug                       # produces app/build/outputs/apk/debug/*.apk
python scripts/adb_test.py install app/build/outputs/apk/debug/app-debug.apk
```

You need the app's **package name** to launch it. If you don't know it, derive it
from the installed app or the APK — see `references/adb-reference.md`
("Finding the package name and launchable activity").

## Step 3 — Launch the app

```bash
python scripts/adb_test.py launch com.example.app
# If the default launcher activity is wrong, name one explicitly:
python scripts/adb_test.py launch com.example.app --activity .ui.LoginActivity
```

`launch` resolves the launchable activity automatically and falls back to the
monkey launcher if it can't. Confirm you landed where you expected:

```bash
python scripts/adb_test.py current-activity
```

## Step 4 — Run the test: observe, act, wait, assert

This is where you exercise the flow. Take a clean logcat window first so crash
detection is focused on this run:

```bash
python scripts/adb_test.py logcat-clear
python scripts/adb_test.py wait-text "Welcome" --timeout 20    # first screen is up
python scripts/adb_test.py screenshot artifacts/01_home.png    # evidence
```

Then interact. Find elements by **text**, **resource-id**, or **content-desc**
(accessibility label) — these are stable; raw coordinates are not. Use `find`
first when unsure what's on screen; it prints each match with its centre and
whether it's clickable:

```bash
python scripts/adb_test.py find --by text "Log in"
python scripts/adb_test.py tap-id  com.example.app:id/email
python scripts/adb_test.py type    "test@example.com"
python scripts/adb_test.py tap-id  com.example.app:id/password
python scripts/adb_test.py type    "hunter2" --enter
python scripts/adb_test.py tap-text "Log in"

# WAIT for the result of that tap before asserting anything about it:
python scripts/adb_test.py wait-text "Your dashboard" --timeout 25
python scripts/adb_test.py screenshot artifacts/02_dashboard.png
python scripts/adb_test.py assert-text "Welcome, test"      # exits 1 if absent
```

**Assertions and exit codes.** `assert-text` and `wait-text` exit `1` when the
expected thing isn't there (a normal *failed test*), `0` on success, and `2` on
an environment error. That makes them compose under `set -e` in a shell test
script, and lets you report pass/fail per step.

**Reset between independent tests.** To start a test from a clean slate without
reinstalling, clear the app's data and relaunch:

```bash
python scripts/adb_test.py clear  com.example.app
python scripts/adb_test.py launch com.example.app
```

## Step 5 — Check for crashes, then report

A screen looking right isn't proof nothing broke. After the flow, scan for fatal
crashes and ANRs in the window you opened at Step 4:

```bash
python scripts/adb_test.py crashes --package com.example.app   # exit 1 if any found
```

Then summarise for the user: which steps passed, which failed and why, the
package/activity reached, any crashes, and the screenshots you captured (saved
under whatever output dir you chose, e.g. `artifacts/`). Keep screenshot names
ordered and descriptive (`01_home.png`, `02_login_filled.png`, …) so the run
reads like a storyboard.

## Step 6 — Teardown

```bash
python scripts/adb_test.py stop com.example.app
# Optionally: python scripts/adb_test.py uninstall com.example.app
# Optionally shut the emulator down (skip if the user wants it kept open):
python scripts/adb_test.py kill-emulator
```

Don't kill the emulator or uninstall unless asked or it's clearly a throwaway —
the user may want to keep poking at it.

## Worked example — a login smoke test as a shell script

When the user wants a repeatable test, write it as a small shell script using the
helper. The structure: boot → install → reset → launch → (observe/act/wait)\* →
assert → crashes → report. Use `set -e` so any failed step stops the run:

```bash
#!/usr/bin/env bash
set -euo pipefail
T="python scripts/adb_test.py"
APK="app/build/outputs/apk/debug/app-debug.apk"
PKG="com.example.app"
mkdir -p artifacts

$T boot --avd Pixel_7_API_34
$T install "$APK"
$T clear "$PKG"
$T logcat-clear
$T launch "$PKG"

$T wait-text "Welcome" --timeout 20
$T screenshot artifacts/01_login.png
$T tap-id  "$PKG:id/email";    $T type "test@example.com"
$T tap-id  "$PKG:id/password"; $T type "hunter2"
$T tap-text "Log in"

$T wait-text "Your dashboard" --timeout 25   # fails the run if login didn't land
$T screenshot artifacts/02_dashboard.png
$T assert-text "Welcome, test"
$T crashes --package "$PKG"
echo "PASS: login smoke test"
```

## Gotchas (full list in references/troubleshooting.md)

- **`uiautomator dump` fails / "could not get idle state":** usually animation.
  The helper retries and `boot` disables animations, but a `Compose`-only UI may
  expose nothing unless the app sets `testTagsAsResourceId`, and `WebView`
  contents are largely invisible to it. Fall back to screenshots + coordinate
  taps for those, or read the dump XML directly.
- **Element not found though you can see it:** match on `content-desc` or
  `resource-id` rather than `text`; run `find --by any "<partial>"` to see what's
  actually exposed; the label may differ from what's rendered.
- **`type` drops spaces or special characters:** spaces are sent as `%s` and a
  set of shell-special characters are escaped, but exotic Unicode can still fail —
  see troubleshooting for the clipboard-paste workaround.
- **Screenshot file is corrupt:** always use the helper's `screenshot`
  (it uses `adb exec-out`); piping `adb shell screencap -p > f.png` corrupts the
  PNG on some shells.

## Reference files

- `references/adb-reference.md` — the full raw-`adb` command catalogue (device,
  app, input, screenshot/recording, UI dump, logcat, file transfer) and the
  keycode table. Read it when the helper doesn't cover what you need.
- `references/troubleshooting.md` — concrete fixes for boot hangs, dump
  failures, multiple/unauthorized devices, permissions, GPU/headless issues,
  and text-input edge cases. Read it the moment something misbehaves.