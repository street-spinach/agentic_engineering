# Raw `simctl` + `idb` command catalogue

Everything `scripts/sim_test.py` wraps, plus the commands it doesn't. iOS splits
the job: **`simctl`** owns lifecycle (ships with Xcode), **`idb`** owns UI
interaction and inspection (`brew install idb-companion && pip3 install fb-idb`).

> Convention below: `<udid>` is the target simulator's UDID. With `idb` you pass
> it as `--udid <udid>`; with `simctl` it's a positional argument. Set
> `$SIM_UDID` or pass `--udid`/`--device` to the helper to avoid repeating it.

## simctl — lifecycle

| Command | Purpose |
|---|---|
| `xcrun simctl help` | sanity-check that the Xcode tools are present |
| `xcrun simctl list devices available` | simulators that can boot |
| `xcrun simctl list devices -j` | same, as JSON (what the helper parses) |
| `xcrun simctl list runtimes` | installed iOS runtimes |
| `xcrun simctl create "<name>" <devicetype> <runtime>` | create a new simulator |
| `xcrun simctl boot <udid>` | boot a simulator (windowless) |
| `open -a Simulator` | open the Simulator GUI window (shows booted sims) |
| `xcrun simctl bootstatus <udid> -b` | block until the boot completes |
| `xcrun simctl shutdown <udid>` (or `all`) | shut a simulator down |
| `xcrun simctl erase <udid>` (or `all`) | factory-reset (wipe all apps & data) |
| `xcrun simctl delete <udid>` | delete the simulator entirely |

## simctl — apps

| Command | Purpose |
|---|---|
| `xcrun simctl install <udid> MyApp.app` | install a **.app** bundle (not .ipa) |
| `xcrun simctl uninstall <udid> <bundle-id>` | remove the app |
| `xcrun simctl launch <udid> <bundle-id>` | launch (prints `bundle: pid`) |
| `xcrun simctl launch --console <udid> <bundle-id>` | launch and stream stdout/stderr |
| `xcrun simctl terminate <udid> <bundle-id>` | kill the app |
| `xcrun simctl get_app_container <udid> <bundle-id> [data]` | path to the app/data container |
| `xcrun simctl spawn <udid> launchctl list` | running processes (grep `UIKitApplication:<bundle-id>` to check liveness) |

### Finding the bundle id

From a built **.app**:
```bash
plutil -extract CFBundleIdentifier raw MyApp.app/Info.plist
# or
defaults read "$PWD/MyApp.app/Info" CFBundleIdentifier
```
From an **installed** app's container, or from the Xcode build settings:
```bash
xcodebuild -showBuildSettings -scheme MyApp | grep PRODUCT_BUNDLE_IDENTIFIER
```

## simctl — media, permissions, environment

| Command | Purpose |
|---|---|
| `xcrun simctl io <udid> screenshot shot.png` | screenshot (PNG) |
| `xcrun simctl io <udid> recordVideo out.mov` | record video (Ctrl-C to stop) |
| `xcrun simctl openurl <udid> "<scheme://...>"` | open a deep link / universal link |
| `xcrun simctl privacy <udid> grant <service> <bundle-id>` | pre-grant a permission |
| `xcrun simctl privacy <udid> revoke <service> <bundle-id>` | revoke it |
| `xcrun simctl addmedia <udid> photo.jpg` | add media to the Photos library |
| `xcrun simctl ui <udid> appearance dark` | switch light/dark mode |
| `xcrun simctl status_bar <udid> override --time 9:41 --batteryLevel 100` | clean status bar for screenshots |
| `xcrun simctl push <udid> <bundle-id> payload.apns` | deliver a test push |

`<service>` for privacy: `photos`, `camera`, `microphone`, `location`,
`contacts`, `calendar`, `notifications`, or `all`.

## idb — UI interaction

| Command | Purpose |
|---|---|
| `idb list-targets` | simulators/devices idb can see (companion up?) |
| `idb ui tap --udid <udid> <x> <y>` | tap a point |
| `idb ui swipe --udid <udid> <x1> <y1> <x2> <y2> [--duration <s>]` | swipe / scroll |
| `idb ui text --udid <udid> "<string>"` | type into the focused field |
| `idb ui key --udid <udid> <hid-code>` | press a key (HID usage codes below) |
| `idb ui key-sequence --udid <udid> <c1> <c2> ...` | press several keys in order |
| `idb ui button --udid <udid> <BUTTON>` | hardware button (table below) |
| `idb ui describe-all --udid <udid> --json` | dump the whole accessibility tree (JSON) |
| `idb ui describe-point --udid <udid> <x> <y>` | describe just the element at a point |

### idb accessibility element fields (`describe-all --json`)

Each element is an object; the keys the helper matches on:

| Field | Meaning | Helper `--by` |
|---|---|---|
| `AXLabel` | accessibility label (visible text) | `label`, `text` |
| `AXUniqueId` | accessibility identifier (set in-app) | `id` |
| `AXValue` | current value (e.g. field contents) | `text` |
| `title` | element title | `text` |
| `type` | element type/role (Button, TextField, …) | `type` |
| `frame` | `{x, y, width, height}` → tap center | — |

The most stable selector is `AXUniqueId`. Set it in the app:
SwiftUI `.accessibilityIdentifier("login_button")`, UIKit
`view.accessibilityIdentifier = "login_button"`.

### HID key usage codes (for `idb ui key`)

| Key | Code | Key | Code |
|---|---|---|---|
| Return/Enter | 40 | Escape | 41 |
| Backspace/Delete | 42 | Tab | 43 |
| Space | 44 | Right arrow | 79 |
| Left arrow | 80 | Down arrow | 81 |
| Up arrow | 82 | | |

The helper accepts names (`sim_test.py key enter`) and maps them to these.

### Hardware buttons (for `idb ui button`)

`HOME`, `LOCK`, `SIDE_BUTTON`, `SIRI`, `APPLE_PAY`. The helper maps the
lower-case names `home`, `lock`, `side`, `siri`, `applepay`.

## idb — apps & files (alternatives to simctl)

| Command | Purpose |
|---|---|
| `idb install --udid <udid> MyApp.app` | install (idb's own installer) |
| `idb launch --udid <udid> <bundle-id>` | launch |
| `idb terminate --udid <udid> <bundle-id>` | kill |
| `idb list-apps --udid <udid>` | installed apps + process state (pipe-separated) |
| `idb file push/pull --udid <udid> ... --bundle-id <id>` | move files in the app sandbox |

## Crash reports

Simulator crash reports land on the **Mac**, not in the simulator:
```
~/Library/Logs/DiagnosticReports/<AppName>-YYYY-MM-DD-*.ips
```
`.ips` (modern) / `.crash` (older) / `.panic`. The helper's `crash-mark` records a
timestamp and `crashes --name <AppName>` reports any report newer than the mark.
To read one: `cat ~/Library/Logs/DiagnosticReports/MyApp-*.ips` (the first JSON
line is a summary header; the rest is the body).
