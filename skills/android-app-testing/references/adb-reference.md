# Raw `adb` command catalogue

Everything `scripts/adb_test.py` wraps, plus the commands it doesn't, so you can
drop to raw `adb` when the helper falls short. All device-targeted commands take
an optional `-s <serial>` (or set `$ANDROID_SERIAL`) — omitted below for brevity.

> Convention: `adb shell <cmd>` runs `<cmd>` *on the device*; `adb exec-out <cmd>`
> runs it on the device but streams **raw bytes** back (use for screenshots and
> file contents — `adb shell` mangles binary on some shells).

## Device & lifecycle

| Command | Purpose |
|---|---|
| `adb version` | platform-tools version (toolchain present?) |
| `adb devices -l` | attached devices + state (`device`, `offline`, `unauthorized`) |
| `adb start-server` / `adb kill-server` | restart the adb daemon (fixes `offline`) |
| `adb wait-for-device` | block until a device is attached |
| `adb get-state` | `device` / `offline` / `bootloader` |
| `adb shell getprop sys.boot_completed` | `1` when the framework is up |
| `adb shell getprop init.svc.bootanim` | `stopped` when the boot animation is done |
| `adb reboot` | reboot the device |
| `adb emu kill` | shut an **emulator** down cleanly |
| `emulator -list-avds` | list creatable AVDs |
| `emulator -avd <name> [-no-window -no-audio -gpu swiftshader_indirect]` | boot an AVD (headless flags optional) |

## Apps (install / launch / data)

| Command | Purpose |
|---|---|
| `adb install -r -g app.apk` | install, **r**eplace existing, **g**rant runtime perms |
| `adb install-multiple *.apk` | install a split/app-bundle set |
| `adb uninstall <pkg>` | remove the app |
| `adb shell pm list packages` | list installed packages (`-3` = third-party only) |
| `adb shell pm list packages -f <pkg>` | show the APK path for a package |
| `adb shell pm clear <pkg>` | wipe the app's data (fresh-install state) |
| `adb shell pm path <pkg>` | print on-device APK path(s) |
| `adb shell am start -n <pkg>/<activity> -W` | start an activity, wait for launch |
| `adb shell am start -a android.intent.action.VIEW -d "<uri>"` | open a deep link |
| `adb shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1` | launch via the launcher intent (fallback) |
| `adb shell am force-stop <pkg>` | kill the app |
| `adb shell cmd package resolve-activity --brief <pkg>` | resolve the launchable activity component |

### Finding the package name and launchable activity

From an **installed** app:
```bash
adb shell pm list packages | grep -i <hint>          # find the package
adb shell cmd package resolve-activity --brief <pkg> # -> com.x/.MainActivity
```
From an **APK file** (needs build-tools on PATH):
```bash
aapt dump badging app.apk | grep -E "package: name|launchable-activity"
# or, newer build-tools:
aapt2 dump badging app.apk | grep -E "package: name|launchable-activity"
```

## Input (taps, text, keys, gestures)

| Command | Purpose |
|---|---|
| `adb shell input tap <x> <y>` | tap a pixel |
| `adb shell input text "<str>"` | type into the focused field (space=`%s`, escape specials) |
| `adb shell input keyevent <code>` | press a key (table below) |
| `adb shell input swipe <x1> <y1> <x2> <y2> [ms]` | swipe / fling (long ms = slow drag) |
| `adb shell input roll <dx> <dy>` | trackball roll |
| `adb shell input draganddrop <x1> <y1> <x2> <y2> [ms]` | drag and drop (API 24+) |

### Common keycodes

| Name | Code | Name | Code | Name | Code |
|---|---|---|---|---|---|
| HOME | 3 | BACK | 4 | ENTER | 66 |
| DPAD_UP | 19 | DPAD_DOWN | 20 | DPAD_LEFT | 21 |
| DPAD_RIGHT | 22 | DPAD_CENTER | 23 | TAB | 61 |
| SPACE | 62 | DEL (backspace) | 67 | MENU | 82 |
| SEARCH | 84 | APP_SWITCH | 187 | POWER | 26 |
| VOLUME_UP | 24 | VOLUME_DOWN | 25 | ESCAPE | 111 |

The helper accepts the lower-case names (`adb_test.py key back`) or a raw code.

## Screenshots & recording

| Command | Purpose |
|---|---|
| `adb exec-out screencap -p > shot.png` | screenshot (binary-safe via `exec-out`) |
| `adb shell screenrecord /sdcard/v.mp4` | record video (Ctrl-C / `--time-limit N` to stop) |
| `adb pull /sdcard/v.mp4 .` | copy the recording to the host |

> Don't use `adb shell screencap -p > f.png` — some shells corrupt the PNG by
> translating `\n`. Always go through `exec-out` (what the helper does).

## UI hierarchy (uiautomator)

| Command | Purpose |
|---|---|
| `adb shell uiautomator dump /sdcard/uidump.xml` | dump the current window's view tree to XML |
| `adb exec-out cat /sdcard/uidump.xml` | stream the dump back to the host |

The XML `<node>` attributes you match on: `text`, `resource-id`, `content-desc`,
`class`, `clickable`, and `bounds="[x1,y1][x2,y2]"`. Tap center =
`((x1+x2)/2, (y1+y2)/2)`. The helper's `find` / `tap-*` / `wait-text` parse
exactly these.

## logcat (logs & crashes)

| Command | Purpose |
|---|---|
| `adb logcat -c` | clear the buffers (do this before a test run) |
| `adb logcat -b crash -c` | clear the dedicated crash buffer too |
| `adb logcat -d -v brief` | dump the buffer once (non-blocking) and exit |
| `adb logcat -b crash -d` | dump only the crash buffer |
| `adb logcat *:E` | follow, errors and worse only |
| `adb logcat --pid=$(adb shell pidof <pkg>)` | follow only the app's process |

Crash/ANR markers to grep for: `FATAL EXCEPTION`, `beginning of crash`,
`ANR in <pkg>`, `Process: <pkg>, PID:`. The helper's `crashes` does this and
scopes to a package.

## Files, settings, misc

| Command | Purpose |
|---|---|
| `adb push <local> <remote>` / `adb pull <remote> <local>` | copy files |
| `adb shell settings put global window_animation_scale 0` | disable window animations |
| `adb shell settings put global transition_animation_scale 0` | disable transitions |
| `adb shell settings put global animator_duration_scale 0` | disable animators |
| `adb shell wm dismiss-keyguard` | dismiss the lock screen |
| `adb shell wm size` / `wm density` | report (or override) screen size / dpi |
| `adb shell dumpsys activity activities` | current task/activity stack |
| `adb shell dumpsys window | grep mCurrentFocus` | focused window/activity |
| `adb shell pidof <pkg>` | the app's PID (empty if not running) |
| `adb root` / `adb unroot` | restart adbd as root (emulators/userdebug only) |
