#!/usr/bin/env python3
"""
adb_test.py — black-box Android UI testing over ADB. Python stdlib only.

Wraps the fiddly parts of driving an app on an emulator/device through `adb`
and the on-device `input`, `uiautomator`, `screencap`, `am`, `pm`, and
`logcat` tools. See ../SKILL.md for the workflow and ../references/ for the
raw command catalogue and troubleshooting.

Exit codes (consistent across every subcommand):
    0  success / assertion held
    1  test failure (expected element absent, crash found, etc.)
    2  environment error (no device, tool missing, bad args, adb error)

Device selection, in priority order:
    --serial <id>  >  $ANDROID_SERIAL  >  the only attached device
If several devices are attached and none is selected, commands that need a
device error out (code 2) and tell you to pick one.
"""

import argparse
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

# --- exit codes -------------------------------------------------------------
OK = 0
FAIL = 1
ENV = 2


class EnvError(Exception):
    """Environment/usage problem — maps to exit code 2."""


# --- low-level adb ----------------------------------------------------------

def _adb_base(serial):
    base = ["adb"]
    if serial:
        base += ["-s", serial]
    return base


def run(cmd, *, capture=True, text=True, check=False, timeout=120, binary=False):
    """Run a command. Returns CompletedProcess. Raises EnvError if the binary
    is missing or the call times out."""
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            text=False if binary else text,
            timeout=timeout,
            check=check,
        )
    except FileNotFoundError:
        raise EnvError(f"'{cmd[0]}' not found on PATH. Is the Android SDK installed "
                       f"and platform-tools/emulator on PATH?")
    except subprocess.TimeoutExpired:
        raise EnvError(f"timed out after {timeout}s: {' '.join(cmd)}")


def adb(args, serial, **kw):
    """Run `adb [-s serial] <args...>`."""
    return run(_adb_base(serial) + list(args), **kw)


def adb_shell(args, serial, **kw):
    """Run `adb [-s serial] shell <args...>`."""
    return adb(["shell"] + list(args), serial, **kw)


def adb_out(args, serial, timeout=120):
    """Run `adb exec-out <args...>` and return raw bytes (binary-safe)."""
    cp = adb(["exec-out"] + list(args), serial, binary=True, timeout=timeout)
    if cp.returncode != 0:
        raise EnvError(f"adb exec-out failed: {cp.stderr.decode('utf-8', 'replace')}")
    return cp.stdout


# --- device resolution ------------------------------------------------------

def attached_devices():
    """Return list of serials that are in 'device' state (booted, authorized)."""
    cp = run(["adb", "devices"])
    out = cp.stdout or ""
    devs = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line or "\t" not in line:
            continue
        serial, state = line.split("\t", 1)
        if state.strip() == "device":
            devs.append(serial.strip())
    return devs


def resolve_serial(explicit):
    """Pick the device serial to operate on, or raise EnvError."""
    if explicit:
        return explicit
    env = os.environ.get("ANDROID_SERIAL")
    if env:
        return env
    devs = attached_devices()
    if not devs:
        raise EnvError("no device attached (adb devices shows none in 'device' state). "
                       "Boot one first:  adb_test.py boot --avd <AVD>")
    if len(devs) > 1:
        raise EnvError("multiple devices attached: " + ", ".join(devs) +
                       ".  Pass --serial <id> or set ANDROID_SERIAL.")
    return devs[0]


# --- UI dump + element model ------------------------------------------------

class Node:
    __slots__ = ("text", "rid", "desc", "cls", "pkg", "clickable", "bounds")

    def __init__(self, attrib):
        self.text = attrib.get("text", "")
        self.rid = attrib.get("resource-id", "")
        self.desc = attrib.get("content-desc", "")
        self.cls = attrib.get("class", "")
        self.pkg = attrib.get("package", "")
        self.clickable = attrib.get("clickable", "false") == "true"
        self.bounds = _parse_bounds(attrib.get("bounds", ""))

    @property
    def center(self):
        if not self.bounds:
            return None
        (x1, y1), (x2, y2) = self.bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def label(self):
        bits = []
        if self.text:
            bits.append(f'text="{self.text}"')
        if self.rid:
            bits.append(f'id={self.rid}')
        if self.desc:
            bits.append(f'desc="{self.desc}"')
        if not bits:
            bits.append(self.cls or "<node>")
        c = self.center
        loc = f"@({c[0]},{c[1]})" if c else "@?"
        return f"{' '.join(bits)} {loc} clickable={self.clickable}"


_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def _parse_bounds(s):
    m = _BOUNDS_RE.search(s or "")
    if not m:
        return None
    x1, y1, x2, y2 = (int(g) for g in m.groups())
    return ((x1, y1), (x2, y2))


def dump_ui(serial, retries=4):
    """Return the current window's uiautomator XML as a string. Retries through
    the common transient failures ('could not get idle state', 'null root')."""
    last = ""
    for attempt in range(retries):
        # Dump to a known path on-device, then stream it out (robust across shells).
        cp = adb_shell(["uiautomator", "dump", "/sdcard/uidump.xml"], serial, timeout=30)
        combined = (cp.stdout or "") + (cp.stderr or "")
        if "ERROR" in combined or "null root node" in combined or "could not get idle" in combined.lower():
            time.sleep(0.6 * (attempt + 1))
            continue
        try:
            raw = adb_out(["cat", "/sdcard/uidump.xml"], serial, timeout=30)
        except EnvError:
            time.sleep(0.6 * (attempt + 1))
            continue
        xml = raw.decode("utf-8", "replace").strip()
        if xml.startswith("<?xml") or xml.startswith("<hierarchy"):
            return xml
        last = combined.strip() or xml[:200]
        time.sleep(0.6 * (attempt + 1))
    raise EnvError("uiautomator dump did not yield a UI tree after "
                   f"{retries} tries (last: {last!r}). The screen may be mid-animation, "
                   "a pure-Compose/WebView surface, or secure (FLAG_SECURE). "
                   "See references/troubleshooting.md.")


def parse_nodes(xml):
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise EnvError(f"could not parse UI dump: {e}")
    return [Node(el.attrib) for el in root.iter("node")]


def _matches(node, by, query):
    q = query.lower()
    if by == "text":
        return q in node.text.lower()
    if by == "id":
        # accept both full id and the bare name after '/'
        rid = node.rid.lower()
        return q == rid or rid.endswith("/" + q) or q in rid
    if by in ("desc", "description"):
        return q in node.desc.lower()
    if by == "any":
        return any(q in v.lower() for v in (node.text, node.rid, node.desc))
    raise EnvError(f"unknown --by '{by}' (use text|id|desc|any)")


def find_nodes(serial, by, query):
    return [n for n in parse_nodes(dump_ui(serial)) if _matches(n, by, query)]


def text_present(serial, needle):
    """Substring match across text + content-desc of every node."""
    q = needle.lower()
    for n in parse_nodes(dump_ui(serial)):
        if q in n.text.lower() or q in n.desc.lower():
            return True
    return False


# --- input helpers ----------------------------------------------------------

# input text treats these specially; %s for space, backslash-escape the rest.
_INPUT_ESCAPE = set(" ()<>|;&*\\~\"'`$#")


def encode_input_text(s):
    out = []
    for ch in s:
        if ch == " ":
            out.append("%s")
        elif ch in _INPUT_ESCAPE:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def tap_node(serial, node):
    c = node.center
    if not c:
        raise EnvError("matched element has no bounds to tap")
    adb_shell(["input", "tap", str(c[0]), str(c[1])], serial)


# --- subcommands ------------------------------------------------------------

def cmd_boot(a):
    serial = a.serial or os.environ.get("ANDROID_SERIAL")
    # Already have a usable device?
    devs = attached_devices()
    if serial and serial in devs:
        print(serial)
        _post_boot(serial)
        return OK
    if not serial and devs:
        serial = devs[0]
        print(serial)
        _post_boot(serial)
        return OK

    if not a.avd:
        raise EnvError("no booted device and no --avd given. "
                       "Pass --avd <name> (see: emulator -list-avds).")

    # Launch the emulator detached.
    em_args = ["emulator", "-avd", a.avd, "-no-snapshot-save"]
    if a.headless:
        em_args += ["-no-window", "-no-audio", "-gpu", "swiftshader_indirect"]
    print(f"booting AVD '{a.avd}'{' (headless)' if a.headless else ''} ...", file=sys.stderr)
    try:
        subprocess.Popen(em_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise EnvError("'emulator' not found on PATH ($ANDROID_HOME/emulator).")

    # Wait for a NEW device to appear, then wait for full boot.
    before = set(devs)
    deadline = time.time() + a.timeout
    serial = None
    while time.time() < deadline:
        now = attached_devices()
        fresh = [d for d in now if d not in before]
        if fresh:
            serial = fresh[0]
            break
        if not before and now:
            serial = now[0]
            break
        time.sleep(1)
    if not serial:
        raise EnvError(f"emulator did not attach within {a.timeout}s.")

    if not _wait_boot_completed(serial, deadline):
        raise EnvError(f"'{serial}' attached but did not finish booting within {a.timeout}s.")
    print(serial)
    _post_boot(serial)
    return OK


def _wait_boot_completed(serial, deadline):
    adb(["wait-for-device"], serial, timeout=60)
    while time.time() < deadline:
        bc = adb_shell(["getprop", "sys.boot_completed"], serial).stdout.strip()
        anim = adb_shell(["getprop", "init.svc.bootanim"], serial).stdout.strip()
        if bc == "1" and anim == "stopped":
            return True
        time.sleep(1)
    return False


def _post_boot(serial):
    """Disable animations and dismiss the keyguard for stable testing."""
    for ns, key in (("global", "window_animation_scale"),
                    ("global", "transition_animation_scale"),
                    ("global", "animator_duration_scale")):
        adb_shell(["settings", "put", ns, key, "0"], serial)
    adb_shell(["wm", "dismiss-keyguard"], serial)


def cmd_install(a):
    serial = resolve_serial(a.serial)
    if not os.path.isfile(a.apk):
        raise EnvError(f"APK not found: {a.apk}")
    flags = ["-r", "-g"]
    cp = adb(["install"] + flags + [a.apk], serial, timeout=300)
    out = (cp.stdout or "") + (cp.stderr or "")
    if cp.returncode != 0 or "Failure" in out or "Error" in out:
        raise EnvError(f"install failed:\n{out.strip()}")
    print(f"installed {os.path.basename(a.apk)}")
    return OK


def cmd_uninstall(a):
    serial = resolve_serial(a.serial)
    cp = adb(["uninstall", a.package], serial)
    print((cp.stdout or "").strip() or "uninstalled")
    return OK


def _launchable_activity(serial, pkg):
    """Best-effort resolve of the launchable activity component, else None."""
    cp = adb_shell(["cmd", "package", "resolve-activity", "--brief", pkg], serial)
    for line in (cp.stdout or "").splitlines():
        line = line.strip()
        if "/" in line and line.startswith(pkg):
            return line
    return None


def cmd_launch(a):
    serial = resolve_serial(a.serial)
    if a.activity:
        comp = a.activity if "/" in a.activity else f"{a.package}/{a.activity}"
        cp = adb_shell(["am", "start", "-n", comp, "-W"], serial)
        out = (cp.stdout or "") + (cp.stderr or "")
        if "Error" not in out and cp.returncode == 0:
            print(f"launched {comp}")
            return OK
        raise EnvError(f"could not start {comp}:\n{out.strip()}")

    comp = _launchable_activity(serial, a.package)
    if comp:
        cp = adb_shell(["am", "start", "-n", comp, "-W"], serial)
        out = (cp.stdout or "") + (cp.stderr or "")
        if "Error" not in out and cp.returncode == 0:
            print(f"launched {comp}")
            return OK

    # Fallback: monkey launcher.
    cp = adb_shell(["monkey", "-p", a.package, "-c", "android.intent.category.LAUNCHER", "1"],
                   serial)
    out = (cp.stdout or "") + (cp.stderr or "")
    if "No activities found" in out or "aborted" in out:
        raise EnvError(f"could not launch {a.package}: {out.strip()}")
    print(f"launched {a.package} (monkey)")
    return OK


def cmd_current_activity(a):
    serial = resolve_serial(a.serial)
    cp = adb_shell(["dumpsys", "activity", "activities"], serial)
    for pat in (r"mResumedActivity:.*\{[^ ]* ([^ }]+)",
                r"ResumedActivity:.*?([\w.]+/[\w.$]+)",
                r"mCurrentFocus=.*?([\w.]+/[\w.$]+)"):
        m = re.search(pat, cp.stdout or "")
        if m:
            print(m.group(1))
            return OK
    # mResumedActivity fallback via window
    cp2 = adb_shell(["dumpsys", "window"], serial)
    m = re.search(r"mCurrentFocus=.*?([\w.]+/[\w.$]+)", cp2.stdout or "")
    if m:
        print(m.group(1))
        return OK
    raise EnvError("could not determine the current activity")


def cmd_screenshot(a):
    serial = resolve_serial(a.serial)
    png = adb_out(["screencap", "-p"], serial, timeout=60)
    if not png.startswith(b"\x89PNG"):
        raise EnvError("screencap did not return a PNG")
    d = os.path.dirname(os.path.abspath(a.path))
    os.makedirs(d, exist_ok=True)
    with open(a.path, "wb") as f:
        f.write(png)
    print(a.path)
    return OK


def cmd_find(a):
    serial = resolve_serial(a.serial)
    nodes = find_nodes(serial, a.by, a.query)
    if not nodes:
        print(f"no match for --by {a.by} '{a.query}'", file=sys.stderr)
        return FAIL
    for n in nodes:
        print(n.label())
    return OK


def cmd_tap_text(a):
    serial = resolve_serial(a.serial)
    nodes = [n for n in find_nodes(serial, "text", a.text) if n.center]
    if not nodes:
        print(f"no tappable element with text '{a.text}'", file=sys.stderr)
        return FAIL
    # Prefer a clickable match.
    node = next((n for n in nodes if n.clickable), nodes[0])
    tap_node(serial, node)
    print(f"tapped text '{a.text}' @{node.center}")
    return OK


def cmd_tap_id(a):
    serial = resolve_serial(a.serial)
    nodes = [n for n in find_nodes(serial, "id", a.resid) if n.center]
    if not nodes:
        print(f"no element with id '{a.resid}'", file=sys.stderr)
        return FAIL
    node = next((n for n in nodes if n.clickable), nodes[0])
    tap_node(serial, node)
    print(f"tapped id '{a.resid}' @{node.center}")
    return OK


def cmd_tap_desc(a):
    serial = resolve_serial(a.serial)
    nodes = [n for n in find_nodes(serial, "desc", a.desc) if n.center]
    if not nodes:
        print(f"no element with content-desc '{a.desc}'", file=sys.stderr)
        return FAIL
    node = next((n for n in nodes if n.clickable), nodes[0])
    tap_node(serial, node)
    print(f"tapped desc '{a.desc}' @{node.center}")
    return OK


def cmd_tap(a):
    serial = resolve_serial(a.serial)
    adb_shell(["input", "tap", str(a.x), str(a.y)], serial)
    print(f"tapped ({a.x},{a.y})")
    return OK


def cmd_type(a):
    serial = resolve_serial(a.serial)
    adb_shell(["input", "text", encode_input_text(a.text)], serial)
    if a.enter:
        adb_shell(["input", "keyevent", "66"], serial)  # KEYCODE_ENTER
    print(f"typed {len(a.text)} chars{' + enter' if a.enter else ''}")
    return OK


# Friendly aliases for common keys -> Android keycodes.
_KEYMAP = {
    "enter": "66", "back": "4", "home": "3", "tab": "61", "menu": "82",
    "del": "67", "delete": "67", "search": "84", "space": "62",
    "up": "19", "down": "20", "left": "21", "right": "22",
    "power": "26", "volup": "24", "voldown": "25", "appswitch": "187",
}


def cmd_key(a):
    serial = resolve_serial(a.serial)
    code = _KEYMAP.get(a.key.lower(), a.key)
    adb_shell(["input", "keyevent", code], serial)
    print(f"keyevent {a.key} ({code})")
    return OK


def cmd_swipe(a):
    serial = resolve_serial(a.serial)
    adb_shell(["input", "swipe", str(a.x1), str(a.y1), str(a.x2), str(a.y2),
               str(a.duration)], serial)
    print(f"swiped ({a.x1},{a.y1})->({a.x2},{a.y2}) {a.duration}ms")
    return OK


def cmd_wait_text(a):
    serial = resolve_serial(a.serial)
    deadline = time.time() + a.timeout
    while True:
        try:
            if text_present(serial, a.text):
                print(f"found '{a.text}'")
                return OK
        except EnvError:
            # Transient dump failure mid-animation — keep polling until timeout.
            pass
        if time.time() >= deadline:
            print(f"TIMEOUT after {a.timeout}s waiting for '{a.text}'", file=sys.stderr)
            return FAIL
        time.sleep(a.poll)


def cmd_assert_text(a):
    serial = resolve_serial(a.serial)
    if text_present(serial, a.text):
        print(f"OK: '{a.text}' present")
        return OK
    print(f"ASSERT FAILED: '{a.text}' not found on screen", file=sys.stderr)
    return FAIL


def cmd_clear(a):
    serial = resolve_serial(a.serial)
    cp = adb_shell(["pm", "clear", a.package], serial)
    if "Success" in (cp.stdout or ""):
        print(f"cleared data for {a.package}")
        return OK
    raise EnvError(f"pm clear failed: {(cp.stdout or cp.stderr or '').strip()}")


def cmd_stop(a):
    serial = resolve_serial(a.serial)
    adb_shell(["am", "force-stop", a.package], serial)
    print(f"force-stopped {a.package}")
    return OK


def cmd_logcat_clear(a):
    serial = resolve_serial(a.serial)
    adb(["logcat", "-c"], serial)
    # -b crash may not exist on all images; ignore failure.
    adb(["logcat", "-b", "crash", "-c"], serial)
    print("logcat cleared")
    return OK


_CRASH_PATTERNS = [
    re.compile(r"FATAL EXCEPTION", re.I),
    re.compile(r"\bANR in\b", re.I),
    re.compile(r"beginning of crash", re.I),
    re.compile(r"Process: .*, PID:.*", re.I),
]


def cmd_crashes(a):
    serial = resolve_serial(a.serial)
    # Pull the crash buffer (and main as backup), non-blocking dump.
    chunks = []
    for buf in ("crash", "main"):
        cp = adb(["logcat", "-b", buf, "-d", "-v", "brief"], serial, timeout=60)
        if cp.returncode == 0 and cp.stdout:
            chunks.append(cp.stdout)
    blob = "\n".join(chunks)
    if not blob:
        print("no logcat output to scan (was logcat-clear run?)", file=sys.stderr)
        return OK

    pkg = a.package
    hits = []
    lines = blob.splitlines()
    for i, line in enumerate(lines):
        if any(p.search(line) for p in _CRASH_PATTERNS):
            window = "\n".join(lines[i:i + 6])
            if not pkg or pkg in window or pkg in line:
                hits.append(window)
    if hits:
        print(f"CRASH/ANR detected ({len(hits)} marker(s)):", file=sys.stderr)
        for h in hits[:5]:
            print("  " + h.replace("\n", "\n  "), file=sys.stderr)
        return FAIL
    print("no crashes or ANRs found")
    return OK


def cmd_kill_emulator(a):
    serial = a.serial or os.environ.get("ANDROID_SERIAL")
    if not serial:
        devs = attached_devices()
        emus = [d for d in devs if d.startswith("emulator-")]
        if len(emus) == 1:
            serial = emus[0]
        elif not emus:
            print("no emulator attached", file=sys.stderr)
            return OK
        else:
            raise EnvError("multiple emulators attached; pass --serial <id>")
    adb(["emu", "kill"], serial)
    print(f"killed {serial}")
    return OK


# --- argument parsing -------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="adb_test.py",
        description="Black-box Android UI testing over ADB (stdlib only).")
    p.add_argument("--serial", help="target device serial (else $ANDROID_SERIAL "
                                     "or the sole attached device)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("boot", help="boot an AVD (or reuse a running device) and wait for full boot")
    s.add_argument("--avd", help="AVD name (emulator -list-avds)")
    s.add_argument("--headless", action="store_true", help="no window / no audio (CI)")
    s.add_argument("--timeout", type=int, default=180, help="boot timeout seconds")
    s.set_defaults(fn=cmd_boot)

    s = sub.add_parser("install", help="adb install -r -g <apk>")
    s.add_argument("apk")
    s.set_defaults(fn=cmd_install)

    s = sub.add_parser("uninstall", help="uninstall a package")
    s.add_argument("package")
    s.set_defaults(fn=cmd_uninstall)

    s = sub.add_parser("launch", help="launch an app by package")
    s.add_argument("package")
    s.add_argument("--activity", help="explicit activity (.Foo or pkg/.Foo)")
    s.set_defaults(fn=cmd_launch)

    s = sub.add_parser("current-activity", help="print the resumed activity component")
    s.set_defaults(fn=cmd_current_activity)

    s = sub.add_parser("screenshot", help="save a PNG screenshot")
    s.add_argument("path")
    s.set_defaults(fn=cmd_screenshot)

    s = sub.add_parser("find", help="list UI elements matching a query")
    s.add_argument("--by", default="text", choices=["text", "id", "desc", "description", "any"])
    s.add_argument("query")
    s.set_defaults(fn=cmd_find)

    s = sub.add_parser("tap-text", help="tap the element whose text matches")
    s.add_argument("text")
    s.set_defaults(fn=cmd_tap_text)

    s = sub.add_parser("tap-id", help="tap the element with this resource-id")
    s.add_argument("resid")
    s.set_defaults(fn=cmd_tap_id)

    s = sub.add_parser("tap-desc", help="tap the element with this content-desc")
    s.add_argument("desc")
    s.set_defaults(fn=cmd_tap_desc)

    s = sub.add_parser("tap", help="tap raw coordinates")
    s.add_argument("x", type=int)
    s.add_argument("y", type=int)
    s.set_defaults(fn=cmd_tap)

    s = sub.add_parser("type", help="type text into the focused field")
    s.add_argument("text")
    s.add_argument("--enter", action="store_true", help="press Enter afterwards")
    s.set_defaults(fn=cmd_type)

    s = sub.add_parser("key", help="send a keyevent (name or numeric code)")
    s.add_argument("key", help="enter|back|home|tab|del|... or a numeric keycode")
    s.set_defaults(fn=cmd_key)

    s = sub.add_parser("swipe", help="swipe between two points")
    s.add_argument("x1", type=int); s.add_argument("y1", type=int)
    s.add_argument("x2", type=int); s.add_argument("y2", type=int)
    s.add_argument("--duration", type=int, default=300, help="ms")
    s.set_defaults(fn=cmd_swipe)

    s = sub.add_parser("wait-text", help="poll until text appears (test fail on timeout)")
    s.add_argument("text")
    s.add_argument("--timeout", type=int, default=15, help="seconds")
    s.add_argument("--poll", type=float, default=0.7, help="seconds between dumps")
    s.set_defaults(fn=cmd_wait_text)

    s = sub.add_parser("assert-text", help="exit 1 if text is not on screen")
    s.add_argument("text")
    s.set_defaults(fn=cmd_assert_text)

    s = sub.add_parser("clear", help="pm clear app data")
    s.add_argument("package")
    s.set_defaults(fn=cmd_clear)

    s = sub.add_parser("stop", help="am force-stop the app")
    s.add_argument("package")
    s.set_defaults(fn=cmd_stop)

    s = sub.add_parser("logcat-clear", help="clear the logcat buffers")
    s.set_defaults(fn=cmd_logcat_clear)

    s = sub.add_parser("crashes", help="scan logcat for FATAL/ANR (exit 1 if found)")
    s.add_argument("--package", help="restrict to crashes mentioning this package")
    s.set_defaults(fn=cmd_crashes)

    s = sub.add_parser("kill-emulator", help="shut the emulator down (adb emu kill)")
    s.set_defaults(fn=cmd_kill_emulator)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except EnvError as e:
        print(f"error: {e}", file=sys.stderr)
        return ENV
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return ENV


if __name__ == "__main__":
    sys.exit(main())
