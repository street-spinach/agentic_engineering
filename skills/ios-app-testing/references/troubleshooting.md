# iOS testing — troubleshooting

Concrete fixes, including the one-time idb install. The helper is
`scripts/sim_test.py` (referred to as `sim_test.py`). **macOS only** — there is
no Linux/Windows path for the iOS Simulator.

## Installing idb (one time)

`simctl` can't touch the UI, so the OBSERVE/ACT steps need idb. Two pieces — a
native companion and the Python client:
```bash
brew tap facebook/fb
brew install idb-companion        # the native companion (talks to the simulator)
pip3 install fb-idb               # the `idb` CLI (Python 3.6+)
idb list-targets                  # verify: should list your booted simulators
```
If `idb` runs but reports no targets, start the companion explicitly or just let
the CLI auto-spawn it by running any `idb ui ...` command against a booted sim.
If `pip3 install fb-idb` fails on a managed Python, use a venv:
`python3 -m venv ~/.idbenv && ~/.idbenv/bin/pip install fb-idb` and call
`~/.idbenv/bin/idb`.

## Xcode / simctl not found

```bash
xcode-select -p                       # should print an Xcode path
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
xcrun simctl help >/dev/null && echo OK
```
If only the Command Line Tools are installed (no full Xcode), there is **no
Simulator**. Surface that to the user — **don't try to download Xcode yourself**
(it's a multi-GB App Store / developer-portal install).

## No simulators available

`xcrun simctl list devices available` is empty → no runtime installed. The user
adds one via Xcode → **Settings → Components** (download an iOS runtime), then
**Window → Devices and Simulators** to create a device. Or via CLI once a runtime
exists:
```bash
xcrun simctl list runtimes
xcrun simctl create "iPhone 15" "iPhone 15" "iOS17.5"
```

## Simulator won't boot / hangs

- `sim_test.py boot` calls `simctl bootstatus -b` which blocks until ready; if it
  times out, raise it: `--timeout 300`.
- Wedged sim: `xcrun simctl shutdown <udid>` then boot again. Nuclear option:
  `xcrun simctl shutdown all` then boot one.
- Corrupt state: `xcrun simctl erase <udid>` (factory reset — wipes installed
  apps and data) before booting.
- The window not appearing is normal — the sim runs headless. Pass `--show` (or
  `open -a Simulator`) if you want to watch.

## Multiple simulators booted

Commands error with "multiple simulators booted". Pick one:
```bash
xcrun simctl list devices | grep Booted     # see UDIDs
export SIM_UDID=<udid>                       # or pass --udid to each command
```

## `describe-all` is missing elements you can see

A known idb limitation — it uses private Apple accessibility APIs and sometimes
omits elements nested inside a `Group`/container. Fixes, in order:
1. `idb ui describe-point <x> <y>` to read one specific spot, then tap by
   coordinate.
2. Take a `screenshot`, find the location visually, `sim_test.py tap <x> <y>`.
3. Best fix is in the app: give key views accessibility identifiers/labels
   (below) so they surface in the tree.

## Element has no AXLabel / can't be found

Match on `AXUniqueId` (`--by id`) or `type` (`--by type`) instead of label. The
durable fix is in the app under test:
- SwiftUI: `.accessibilityIdentifier("login_button")` (and
  `.accessibilityLabel("Log In")` for VoiceOver text).
- UIKit: `view.accessibilityIdentifier = "login_button"`.
Then select with `sim_test.py tap-id login_button`, which is stable across copy
and localization changes.

## idb is flaky / errors intermittently / lags new Xcode

idb leans on private APIs and can be brittle, especially right after an Xcode
update. The helper already retries `describe-all`. If idb is broken on your Xcode
version:
```bash
pip3 install --upgrade fb-idb           # newer client
brew upgrade idb-companion              # newer companion
# kill stale companions, then retry:
pkill -f idb_companion ; idb list-targets
```
If a fresh Xcode broke idb entirely, pin to a known-good companion version or
fall back to **screenshot + coordinate taps** for the run.

## `type` goes nowhere

No field is focused. `idb ui text` types into whatever has focus — so
`tap-id`/`tap-label` the text field *first*, confirm focus (a caret / the
keyboard appears in a screenshot), then `type`. The helper's `--enter` sends HID
Return after typing.

## Permission dialogs (camera, location, notifications) block the flow

Pre-grant before launch so no dialog appears:
```bash
xcrun simctl privacy <udid> grant location <bundle-id>
xcrun simctl privacy <udid> grant photos   <bundle-id>
```
If a system alert is already up, it's part of the accessibility tree — `find`
its button ("Allow", "OK") and `tap-label` it.

## Reset to a clean state between tests

iOS has no per-app "clear data" like Android's `pm clear`. Either:
- uninstall → install → launch (the helper's documented reset), or
- `xcrun simctl erase <udid>` for a full factory reset (slower; wipes everything).

## App built for the wrong destination

`simctl install` needs a **simulator** `.app`, not a device build. Build with the
simulator SDK:
```bash
xcodebuild -scheme MyApp -sdk iphonesimulator -configuration Debug \
  -derivedDataPath build build
# product: build/Build/Products/Debug-iphonesimulator/MyApp.app
```
A device `.app`/`.ipa` will install-fail with an architecture/SDK mismatch.

## Crash check finds nothing after a crash

`crashes` compares report mtimes against the `crash-mark` you set — if you didn't
run `crash-mark` before the flow, it warns and reports all recent files. Reports
can also take a second to be written; re-run `crashes` after a short pause, or
look directly in `~/Library/Logs/DiagnosticReports/`.
