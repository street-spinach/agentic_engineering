#!/usr/bin/env python3
"""
sim_test.py — black-box iOS UI testing on the Simulator. Python stdlib only.

Wraps two tools behind one CLI (same command names as the Android helper):
  * xcrun simctl  — lifecycle: boot, install, launch, terminate, screenshot, ...
  * idb           — interaction + inspection: tap / text / swipe / describe-all
`simctl` has no tap/type/inspect command, which is why idb is required for the
OBSERVE/ACT steps. See ../SKILL.md and ../references/ for details.

Exit codes (consistent across every subcommand):
    0  success / assertion held
    1  test failure (expected element absent, app not running, crash found)
    2  environment error (no simulator, tool missing, bad args, command error)

Simulator selection, in priority order:
    --udid <id>  >  $SIM_UDID  >  the only booted simulator
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time

OK = 0
FAIL = 1
ENV = 2

DIAG_DIR = os.path.expanduser("~/Library/Logs/DiagnosticReports")


class EnvError(Exception):
    """Environment/usage problem — maps to exit code 2."""


# --- low-level process ------------------------------------------------------

def run(cmd, *, timeout=120, binary=False):
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=not binary,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise EnvError(f"'{cmd[0]}' not found on PATH. "
                       f"{'Install idb: brew install idb-companion && pip3 install fb-idb' if cmd[0] == 'idb' else 'Is Xcode installed (xcode-select --install)?'}")
    except subprocess.TimeoutExpired:
        raise EnvError(f"timed out after {timeout}s: {' '.join(cmd)}")


def simctl(args, *, timeout=120, binary=False):
    return run(["xcrun", "simctl"] + list(args), timeout=timeout, binary=binary)


def idb(args, udid, *, timeout=120):
    cmd = ["idb"] + list(args)
    if udid:
        cmd += ["--udid", udid]
    return run(cmd, timeout=timeout)


# --- simulator resolution ---------------------------------------------------

def _all_devices():
    cp = simctl(["list", "devices", "-j"])
    if cp.returncode != 0:
        raise EnvError(f"simctl list failed: {cp.stderr.strip()}")
    try:
        data = json.loads(cp.stdout)
    except json.JSONDecodeError as e:
        raise EnvError(f"could not parse simctl device list: {e}")
    out = []
    for runtime, devs in data.get("devices", {}).items():
        for d in devs:
            d = dict(d)
            d["runtime"] = runtime
            out.append(d)
    return out


def booted_udids():
    return [d["udid"] for d in _all_devices() if d.get("state") == "Booted"]


def resolve_udid(explicit):
    if explicit:
        return explicit
    env = os.environ.get("SIM_UDID")
    if env:
        return env
    booted = booted_udids()
    if not booted:
        raise EnvError("no simulator booted. Boot one first:  "
                       "sim_test.py boot --device 'iPhone 15'")
    if len(booted) > 1:
        raise EnvError("multiple simulators booted: " + ", ".join(booted) +
                       ".  Pass --udid <id> or set SIM_UDID.")
    return booted[0]


def find_device_by_name(name):
    """Resolve a device name (e.g. 'iPhone 15') to a UDID. Prefers a booted or
    available device; among matches, the newest runtime wins."""
    matches = [d for d in _all_devices()
               if d.get("name") == name and d.get("isAvailable", True)]
    if not matches:
        # case-insensitive / substring fallback
        low = name.lower()
        matches = [d for d in _all_devices()
                   if low in d.get("name", "").lower() and d.get("isAvailable", True)]
    if not matches:
        raise EnvError(f"no available simulator named '{name}'. "
                       f"List them:  xcrun simctl list devices available")
    matches.sort(key=lambda d: (d.get("state") == "Booted", d.get("runtime", "")),
                 reverse=True)
    return matches[0]["udid"]


# --- accessibility tree (idb describe-all) ----------------------------------

class Elem:
    __slots__ = ("label", "uid", "type", "value", "title", "frame")

    def __init__(self, raw):
        self.label = raw.get("AXLabel") or ""
        self.uid = raw.get("AXUniqueId") or ""
        self.type = raw.get("type") or raw.get("role_description") or raw.get("role") or ""
        self.value = _as_text(raw.get("AXValue"))
        self.title = raw.get("title") or ""
        self.frame = raw.get("frame") or {}

    @property
    def center(self):
        f = self.frame
        if not f or "x" not in f:
            return None
        return (int(f["x"] + f.get("width", 0) / 2),
                int(f["y"] + f.get("height", 0) / 2))

    def texts(self):
        return [t for t in (self.label, self.value, self.title) if t]

    def render(self):
        bits = []
        if self.label:
            bits.append(f'label="{self.label}"')
        if self.uid:
            bits.append(f"id={self.uid}")
        if self.value:
            bits.append(f'value="{self.value}"')
        bits.append(f"type={self.type or '?'}")
        c = self.center
        bits.append(f"@({c[0]},{c[1]})" if c else "@?")
        return " ".join(bits)


def _as_text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    return str(v)


def _parse_describe(stdout):
    stdout = stdout.strip()
    if not stdout:
        return []
    # idb may emit a JSON array, or newline-delimited JSON objects.
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            return [Elem(x) for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [Elem(data)]
    except json.JSONDecodeError:
        pass
    elems = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            elems.append(Elem(json.loads(line)))
        except json.JSONDecodeError:
            continue
    return elems


def describe_all(udid, retries=3):
    last = ""
    for attempt in range(retries):
        cp = idb(["ui", "describe-all", "--json"], udid, timeout=40)
        if cp.returncode == 0 and cp.stdout.strip():
            elems = _parse_describe(cp.stdout)
            if elems:
                return elems
        last = (cp.stderr or cp.stdout or "").strip()
        time.sleep(0.6 * (attempt + 1))
    raise EnvError(f"idb describe-all returned no elements after {retries} tries "
                   f"(last: {last[:200]!r}). idb can be flaky or lag the newest "
                   f"Xcode — see references/troubleshooting.md.")


def _matches(e, by, query):
    q = query.lower()
    if by == "label":
        return q in e.label.lower()
    if by == "id":
        return q == e.uid.lower() or q in e.uid.lower()
    if by == "type":
        return q in e.type.lower()
    if by == "text":
        return any(q in t.lower() for t in e.texts())
    if by == "any":
        return any(q in t.lower() for t in e.texts() + [e.uid, e.type])
    raise EnvError(f"unknown --by '{by}' (use label|id|type|text|any)")


def find_elems(udid, by, query):
    return [e for e in describe_all(udid) if _matches(e, by, query)]


def text_present(udid, needle):
    q = needle.lower()
    for e in describe_all(udid):
        if any(q in t.lower() for t in e.texts()):
            return True
    return False


def tap_elem(udid, e):
    c = e.center
    if not c:
        raise EnvError("matched element has no frame to tap")
    cp = idb(["ui", "tap", str(c[0]), str(c[1])], udid)
    if cp.returncode != 0:
        raise EnvError(f"idb tap failed: {cp.stderr.strip()}")


# --- crash marker -----------------------------------------------------------

def _mark_path(udid):
    return os.path.join(tempfile.gettempdir(), f"sim_test_crashmark_{udid}")


# --- subcommands ------------------------------------------------------------

def cmd_boot(a):
    udid = a.udid or os.environ.get("SIM_UDID")
    if udid and udid in booted_udids():
        if a.show:
            run(["open", "-a", "Simulator"])
        print(udid)
        return OK
    if not udid:
        already = booted_udids()
        if already and not a.device:
            if a.show:
                run(["open", "-a", "Simulator"])
            print(already[0])
            return OK
        if not a.device:
            raise EnvError("no simulator booted and no --device given. "
                           "Pass --device 'iPhone 15'.")
        udid = find_device_by_name(a.device)

    if udid not in booted_udids():
        cp = simctl(["boot", udid])
        if cp.returncode != 0 and "current state: Booted" not in (cp.stderr or ""):
            raise EnvError(f"simctl boot failed: {cp.stderr.strip()}")

    if a.show:
        run(["open", "-a", "Simulator"])

    # Wait for full boot.
    cp = simctl(["bootstatus", udid, "-b"], timeout=a.timeout)
    if cp.returncode != 0:
        # bootstatus is best-effort; fall back to polling.
        deadline = time.time() + a.timeout
        while time.time() < deadline:
            if udid in booted_udids():
                break
            time.sleep(1)
        else:
            raise EnvError(f"simulator {udid} did not boot within {a.timeout}s")
    print(udid)
    return OK


def cmd_install(a):
    udid = resolve_udid(a.udid)
    if not os.path.exists(a.app):
        raise EnvError(f".app bundle not found: {a.app}")
    cp = simctl(["install", udid, a.app], timeout=300)
    if cp.returncode != 0:
        raise EnvError(f"install failed: {cp.stderr.strip()}")
    print(f"installed {os.path.basename(a.app)}")
    return OK


def cmd_uninstall(a):
    udid = resolve_udid(a.udid)
    cp = simctl(["uninstall", udid, a.bundle])
    if cp.returncode != 0 and "not installed" not in (cp.stderr or "").lower():
        raise EnvError(f"uninstall failed: {cp.stderr.strip()}")
    print(f"uninstalled {a.bundle}")
    return OK


def cmd_launch(a):
    udid = resolve_udid(a.udid)
    if a.fresh:
        simctl(["terminate", udid, a.bundle])  # ignore "not running"
    cp = simctl(["launch", udid, a.bundle])
    if cp.returncode != 0:
        raise EnvError(f"launch failed: {(cp.stderr or cp.stdout).strip()}")
    print((cp.stdout or "").strip() or f"launched {a.bundle}")
    return OK


def _is_running(udid, bundle):
    cp = simctl(["spawn", udid, "launchctl", "list"], timeout=30)
    if cp.returncode != 0:
        return False
    return f"UIKitApplication:{bundle}" in (cp.stdout or "")


def cmd_running(a):
    udid = resolve_udid(a.udid)
    if _is_running(udid, a.bundle):
        print(f"{a.bundle} is running")
        return OK
    print(f"{a.bundle} is NOT running", file=sys.stderr)
    return FAIL


def cmd_terminate(a):
    udid = resolve_udid(a.udid)
    simctl(["terminate", udid, a.bundle])
    print(f"terminated {a.bundle}")
    return OK


def cmd_screenshot(a):
    udid = resolve_udid(a.udid)
    d = os.path.dirname(os.path.abspath(a.path))
    os.makedirs(d, exist_ok=True)
    cp = simctl(["io", udid, "screenshot", a.path], timeout=60)
    if cp.returncode != 0 or not os.path.exists(a.path):
        raise EnvError(f"screenshot failed: {cp.stderr.strip()}")
    print(a.path)
    return OK


def cmd_find(a):
    udid = resolve_udid(a.udid)
    elems = find_elems(udid, a.by, a.query)
    if not elems:
        print(f"no match for --by {a.by} '{a.query}'", file=sys.stderr)
        return FAIL
    for e in elems:
        print(e.render())
    return OK


def cmd_tap_label(a):
    udid = resolve_udid(a.udid)
    elems = [e for e in find_elems(udid, "label", a.label) if e.center]
    if not elems:
        print(f"no element with label '{a.label}'", file=sys.stderr)
        return FAIL
    tap_elem(udid, elems[0])
    print(f"tapped label '{a.label}' @{elems[0].center}")
    return OK


def cmd_tap_id(a):
    udid = resolve_udid(a.udid)
    elems = [e for e in find_elems(udid, "id", a.uid) if e.center]
    if not elems:
        print(f"no element with id '{a.uid}'", file=sys.stderr)
        return FAIL
    tap_elem(udid, elems[0])
    print(f"tapped id '{a.uid}' @{elems[0].center}")
    return OK


def cmd_tap(a):
    udid = resolve_udid(a.udid)
    cp = idb(["ui", "tap", str(a.x), str(a.y)], udid)
    if cp.returncode != 0:
        raise EnvError(f"idb tap failed: {cp.stderr.strip()}")
    print(f"tapped ({a.x},{a.y})")
    return OK


def cmd_type(a):
    udid = resolve_udid(a.udid)
    cp = idb(["ui", "text", a.text], udid)
    if cp.returncode != 0:
        raise EnvError(f"idb text failed: {cp.stderr.strip()}")
    if a.enter:
        idb(["ui", "key", "40"], udid)  # HID Return
    print(f"typed {len(a.text)} chars{' + enter' if a.enter else ''}")
    return OK


# Friendly key names -> HID usage codes.
_HID = {
    "enter": "40", "return": "40", "tab": "43", "space": "44",
    "backspace": "42", "del": "42", "delete": "42", "escape": "41", "esc": "41",
    "up": "82", "down": "81", "left": "80", "right": "79",
}
# Hardware buttons go through `idb ui button`.
_BUTTONS = {"home": "HOME", "lock": "LOCK", "side": "SIDE_BUTTON",
            "siri": "SIRI", "applepay": "APPLE_PAY"}


def cmd_key(a):
    udid = resolve_udid(a.udid)
    name = a.key.lower()
    if name in _BUTTONS:
        cp = idb(["ui", "button", _BUTTONS[name]], udid)
    else:
        code = _HID.get(name, a.key)
        cp = idb(["ui", "key", code], udid)
    if cp.returncode != 0:
        raise EnvError(f"idb key failed: {cp.stderr.strip()}")
    print(f"key {a.key}")
    return OK


def cmd_swipe(a):
    udid = resolve_udid(a.udid)
    args = ["ui", "swipe", str(a.x1), str(a.y1), str(a.x2), str(a.y2)]
    if a.duration:
        args += ["--duration", str(a.duration)]
    cp = idb(args, udid)
    if cp.returncode != 0:
        raise EnvError(f"idb swipe failed: {cp.stderr.strip()}")
    print(f"swiped ({a.x1},{a.y1})->({a.x2},{a.y2})")
    return OK


def cmd_wait_text(a):
    udid = resolve_udid(a.udid)
    deadline = time.time() + a.timeout
    while True:
        try:
            if text_present(udid, a.text):
                print(f"found '{a.text}'")
                return OK
        except EnvError:
            pass  # transient idb hiccup — keep polling
        if time.time() >= deadline:
            print(f"TIMEOUT after {a.timeout}s waiting for '{a.text}'", file=sys.stderr)
            return FAIL
        time.sleep(a.poll)


def cmd_assert_text(a):
    udid = resolve_udid(a.udid)
    if text_present(udid, a.text):
        print(f"OK: '{a.text}' present")
        return OK
    print(f"ASSERT FAILED: '{a.text}' not found on screen", file=sys.stderr)
    return FAIL


def cmd_crash_mark(a):
    udid = resolve_udid(a.udid)
    with open(_mark_path(udid), "w") as f:
        f.write(str(time.time()))
    print(f"crash baseline marked for {udid}")
    return OK


def cmd_crashes(a):
    udid = resolve_udid(a.udid)
    mark = 0.0
    mp = _mark_path(udid)
    if os.path.exists(mp):
        try:
            with open(mp) as f:
                mark = float(f.read().strip())
        except ValueError:
            mark = 0.0
    else:
        print("no crash-mark set; reporting all recent reports", file=sys.stderr)

    if not os.path.isdir(DIAG_DIR):
        print("no crashes found (DiagnosticReports dir absent)")
        return OK

    name = a.name
    hits = []
    for path in glob.glob(os.path.join(DIAG_DIR, "*")):
        base = os.path.basename(path)
        if name and not base.lower().startswith(name.lower()):
            continue
        # only .ips/.crash style reports
        if not base.endswith((".ips", ".crash", ".panic")):
            continue
        try:
            if os.path.getmtime(path) >= mark:
                hits.append(base)
        except OSError:
            continue
    if hits:
        print(f"CRASH detected ({len(hits)} new report(s)):", file=sys.stderr)
        for h in hits:
            print("  " + h, file=sys.stderr)
        return FAIL
    print("no new crash reports found")
    return OK


def cmd_shutdown(a):
    udid = a.udid or os.environ.get("SIM_UDID")
    if not udid:
        booted = booted_udids()
        if len(booted) == 1:
            udid = booted[0]
        elif not booted:
            print("no simulator booted")
            return OK
        else:
            raise EnvError("multiple simulators booted; pass --udid <id> "
                           "(or 'xcrun simctl shutdown all')")
    simctl(["shutdown", udid])
    print(f"shut down {udid}")
    return OK


# --- argument parsing -------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="sim_test.py",
        description="Black-box iOS UI testing on the Simulator (simctl + idb).")
    p.add_argument("--udid", help="target simulator UDID (else $SIM_UDID or the "
                                  "sole booted simulator)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("boot", help="boot a simulator (or reuse a booted one) and wait")
    s.add_argument("--device", help="device name, e.g. 'iPhone 15'")
    s.add_argument("--show", action="store_true", help="open the Simulator GUI window")
    s.add_argument("--timeout", type=int, default=180, help="boot timeout seconds")
    s.set_defaults(fn=cmd_boot)

    s = sub.add_parser("install", help="simctl install <.app>")
    s.add_argument("app")
    s.set_defaults(fn=cmd_install)

    s = sub.add_parser("uninstall", help="uninstall a bundle id")
    s.add_argument("bundle")
    s.set_defaults(fn=cmd_uninstall)

    s = sub.add_parser("launch", help="launch an app by bundle id")
    s.add_argument("bundle")
    s.add_argument("--fresh", action="store_true", help="terminate any running instance first")
    s.set_defaults(fn=cmd_launch)

    s = sub.add_parser("running", help="exit 1 if the app is not alive")
    s.add_argument("bundle")
    s.set_defaults(fn=cmd_running)

    s = sub.add_parser("terminate", help="terminate the app")
    s.add_argument("bundle")
    s.set_defaults(fn=cmd_terminate)

    s = sub.add_parser("screenshot", help="save a PNG screenshot")
    s.add_argument("path")
    s.set_defaults(fn=cmd_screenshot)

    s = sub.add_parser("find", help="list accessibility elements matching a query")
    s.add_argument("--by", default="label", choices=["label", "id", "type", "text", "any"])
    s.add_argument("query")
    s.set_defaults(fn=cmd_find)

    s = sub.add_parser("tap-label", help="tap the element with this AXLabel")
    s.add_argument("label")
    s.set_defaults(fn=cmd_tap_label)

    s = sub.add_parser("tap-id", help="tap the element with this AXUniqueId")
    s.add_argument("uid")
    s.set_defaults(fn=cmd_tap_id)

    s = sub.add_parser("tap", help="tap raw coordinates")
    s.add_argument("x", type=int); s.add_argument("y", type=int)
    s.set_defaults(fn=cmd_tap)

    s = sub.add_parser("type", help="type text into the focused field")
    s.add_argument("text")
    s.add_argument("--enter", action="store_true", help="press Return afterwards")
    s.set_defaults(fn=cmd_type)

    s = sub.add_parser("key", help="send a key (enter|tab|esc|...) or hardware button (home|lock|...)")
    s.add_argument("key")
    s.set_defaults(fn=cmd_key)

    s = sub.add_parser("swipe", help="swipe between two points")
    s.add_argument("x1", type=int); s.add_argument("y1", type=int)
    s.add_argument("x2", type=int); s.add_argument("y2", type=int)
    s.add_argument("--duration", type=float, default=0.3, help="seconds")
    s.set_defaults(fn=cmd_swipe)

    s = sub.add_parser("wait-text", help="poll until text appears (test fail on timeout)")
    s.add_argument("text")
    s.add_argument("--timeout", type=int, default=15, help="seconds")
    s.add_argument("--poll", type=float, default=0.7, help="seconds between dumps")
    s.set_defaults(fn=cmd_wait_text)

    s = sub.add_parser("assert-text", help="exit 1 if text is not on screen")
    s.add_argument("text")
    s.set_defaults(fn=cmd_assert_text)

    s = sub.add_parser("crash-mark", help="record the crash baseline timestamp")
    s.set_defaults(fn=cmd_crash_mark)

    s = sub.add_parser("crashes", help="scan for crash reports since the mark (exit 1 if any)")
    s.add_argument("--name", help="restrict to reports whose name starts with this (app name)")
    s.set_defaults(fn=cmd_crashes)

    s = sub.add_parser("shutdown", help="shut the simulator down")
    s.set_defaults(fn=cmd_shutdown)

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
