# Android testing — troubleshooting

Concrete fixes for the things that actually go wrong. Read the moment something
misbehaves. The helper is `scripts/adb_test.py` (referred to as `adb_test.py`).

## Toolchain not found

`adb`/`emulator` not on PATH — they live under the SDK:
```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"      # macOS default
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
adb version && emulator -list-avds
```
If `$ANDROID_HOME` is unset, look in `~/Library/Android/sdk` (macOS),
`~/Android/Sdk` (Linux), or `%LOCALAPPDATA%\Android\Sdk` (Windows). **Don't try
to download the SDK** — surface the gap to the user.

## No AVDs to boot

`emulator -list-avds` is empty. The user must create one — you can't do it
without a system image. Options to give them:
- Android Studio → **Device Manager** → *Create device*.
- CLI: `sdkmanager "system-images;android-34;google_apis;arm64-v8a"` then
  `avdmanager create avd -n Pixel_7_API_34 -k "system-images;android-34;google_apis;arm64-v8a" -d pixel_7`.

## Emulator boots but never becomes "ready"

`boot` waits for `sys.boot_completed=1` **and** `init.svc.bootanim=stopped`. If it
times out:
- Cold boots are slow on first run — re-run `boot` with `--timeout 300`.
- A wedged emulator: `adb emu kill` (or `adb_test.py kill-emulator`), then boot
  again. As a last resort wipe state: `emulator -avd <name> -wipe-data`.
- Headless/CI with no GPU: boot with `--headless` (the helper passes
  `-no-window -no-audio -gpu swiftshader_indirect`).

## `device offline` or `unauthorized`

```bash
adb kill-server && adb start-server && adb devices
```
`unauthorized` on a physical device → accept the "Allow USB debugging" prompt on
the device. Emulators shouldn't show this; if one does, cold-boot it.

## Multiple devices attached

Commands error with "multiple devices". Pick one:
```bash
adb devices                       # see serials
export ANDROID_SERIAL=emulator-5554   # or pass --serial to each command
```

## `uiautomator dump` fails / "could not get idle state" / "null root node"

The single most common flake. Causes and fixes:
- **Mid-animation.** The screen never goes idle. `boot` disables the three
  animation scales; if you booted the device yourself, disable them manually
  (see adb-reference). The helper also retries a few times.
- **Jetpack Compose UI.** A pure-Compose tree exposes *nothing* to uiautomator
  unless the app opts in with `Modifier.semantics { testTagsAsResourceId = true }`
  (set on the root) and `Modifier.testTag("...")` on elements. Without that, fall
  back to **screenshot + coordinate `tap`**, or read the rendered text via OCR
  out of band.
- **WebView content** is largely invisible to uiautomator. Same fallback.
- **Secure window** (`FLAG_SECURE`, e.g. payment/DRM screens) refuses dumps *and*
  screenshots by design. There's no black-box workaround.

When you must use coordinates, take a `screenshot` first, read the pixel
location off it, then `adb_test.py tap <x> <y>`.

## Element not found though you can clearly see it

The visible label often isn't the matchable `text`. In order of reliability:
1. `adb_test.py find --by any "<partial>"` — dumps every node that mentions the
   string in `text`, `resource-id`, *or* `content-desc`. See what's actually
   exposed.
2. Match on `--by id <resource-id>` (most stable) or `--by desc <content-desc>`
   (accessibility label) instead of `text`.
3. The node may be off-screen — `swipe` to scroll it into view, then re-find.

## `type` drops spaces or special characters

`adb shell input text` treats space as a word separator and chokes on shell
metacharacters. The helper sends space as `%s` and backslash-escapes
`` ()<>|;&*\~"'`$# ``. For exotic Unicode/emoji that still fail, paste via the
clipboard instead:
```bash
adb shell am broadcast -a clipper.set -e text "💡 unicode ok"   # if a clipper app is present
# or, more portable, use a content provider / Compose testTag path
```
In practice: type the ASCII parts with `type`, and for the rest set the field
value in the app under test if you control it.

## Screenshot file is corrupt / zero bytes

Use `adb_test.py screenshot` (it uses `adb exec-out screencap -p`, binary-safe,
and validates the PNG magic). Never pipe `adb shell screencap -p > f.png` — some
shells corrupt the stream. If even `exec-out` yields garbage, the screen may be
`FLAG_SECURE` (see above).

## App won't launch / wrong screen

- `adb_test.py launch <pkg>` resolves the launchable activity, then falls back to
  the monkey launcher. If both miss, pass `--activity` explicitly with the right
  component (find it with `cmd package resolve-activity --brief <pkg>` or
  `aapt dump badging`).
- "No activities found to run" from monkey → the package isn't installed, or its
  manifest has no LAUNCHER activity (a library/service-only APK).

## Crash check reports nothing after an obvious crash

`crashes` scans the logcat buffer — if you didn't `logcat-clear` at the start, the
crash may have scrolled out, or your `--package` filter is too strict. Re-run
without `--package` to see all markers, or dump the raw buffer:
`adb logcat -b crash -d`.

## Runtime permission dialogs block the flow

Install with `-g` (the helper's default) to pre-grant. To grant/revoke after
install:
```bash
adb shell pm grant  <pkg> android.permission.CAMERA
adb shell pm revoke <pkg> android.permission.ACCESS_FINE_LOCATION
```

## GPU / headless rendering issues

On CI or over SSH with no display, boot `--headless`. If the UI renders black or
the emulator crashes on GPU init, try `-gpu swiftshader_indirect` (software, the
headless default) or `-gpu off`.
