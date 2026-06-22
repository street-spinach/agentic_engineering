#!/usr/bin/env python3
"""Render a persona-testing results JSON into a readable Markdown report.

Stdlib only — nothing to install. The persona-app-testing skill collects each
persona's journeys (functional verdict + friction findings + screenshots) into a
results.json, then runs this to produce one consistent report every time instead
of hand-formatting Markdown.

    python persona_report.py results.json --out artifacts/persona-tests/report.md \
        --generated "$(date -u +%FT%TZ)"

See references/results-schema.md for the input schema and a filled example.
Run paths in results.json are interpreted relative to the current directory; the
report embeds screenshots as paths relative to --out so they resolve in place.
"""
import argparse
import json
import os
import sys

RESULT_BADGE = {"pass": "✅ pass", "fail": "❌ fail", "blocked": "⛔ blocked"}
STATUS_BADGE = {"ok": "✓", "warn": "⚠️", "fail": "✗"}
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}
SEV_BADGE = {"high": "🔴 high", "medium": "🟠 medium", "low": "🟡 low"}


def err(msg):
    print(f"persona_report: {msg}", file=sys.stderr)
    return 2


def rel(path, out_dir):
    """Path for embedding, relative to the report's directory."""
    if not path:
        return ""
    try:
        return os.path.relpath(os.path.abspath(path), os.path.abspath(out_dir))
    except ValueError:  # e.g. different drive on Windows
        return path


def md_escape_cell(text):
    """Make a string safe inside a Markdown table cell."""
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def collect_findings(personas):
    """Flatten every friction finding with its persona/journey context."""
    out = []
    for p in personas:
        for j in p.get("journeys", []):
            for f in j.get("friction", []):
                out.append({**f, "_persona": p.get("name", "?"),
                            "_journey": j.get("goal", "?")})
    out.sort(key=lambda f: SEV_ORDER.get(str(f.get("severity", "low")).lower(), 3))
    return out


def render(data, out_dir, generated):
    app = data.get("app", {})
    personas = data.get("personas", [])
    L = []  # lines

    name = app.get("name", "the app")
    L.append(f"# Persona testing report — {name}")
    L.append("")
    meta = []
    if app.get("platform"):
        meta.append(f"**Platform:** {app['platform']}")
    if app.get("build"):
        meta.append(f"**Build:** {app['build']}")
    if app.get("id"):
        meta.append(f"**App id:** `{app['id']}`")
    if generated:
        meta.append(f"**Generated:** {generated}")
    if meta:
        L.append(" · ".join(meta))
        L.append("")

    # ---- counts ----
    journeys = [(p, j) for p in personas for j in p.get("journeys", [])]
    n_pass = sum(1 for _, j in journeys if j.get("result") == "pass")
    n_fail = sum(1 for _, j in journeys if j.get("result") == "fail")
    n_block = sum(1 for _, j in journeys if j.get("result") == "blocked")
    findings = collect_findings(personas)
    sev_counts = {s: sum(1 for f in findings
                         if str(f.get("severity", "")).lower() == s)
                  for s in ("high", "medium", "low")}

    # ---- summary ----
    L.append("## Summary")
    L.append("")
    L.append(f"{len(personas)} personas · {len(journeys)} journeys — "
             f"{n_pass} passed, {n_fail} failed, {n_block} blocked. "
             f"{len(findings)} friction findings "
             f"({sev_counts['high']} high / {sev_counts['medium']} medium / "
             f"{sev_counts['low']} low).")
    L.append("")
    L.append("| Persona | Journey | Result | Friction (H/M/L) |")
    L.append("|---|---|---|---|")
    for p, j in journeys:
        fr = j.get("friction", [])
        h = sum(1 for f in fr if str(f.get("severity")).lower() == "high")
        m = sum(1 for f in fr if str(f.get("severity")).lower() == "medium")
        lo = sum(1 for f in fr if str(f.get("severity")).lower() == "low")
        L.append(f"| {md_escape_cell(p.get('name'))} "
                 f"| {md_escape_cell(j.get('goal'))} "
                 f"| {RESULT_BADGE.get(j.get('result'), j.get('result', '?'))} "
                 f"| {h}/{m}/{lo} |")
    L.append("")

    # ---- findings by severity ----
    if findings:
        L.append("## Findings by severity")
        L.append("")
        L.append("| Severity | Heuristic | Persona | Finding | Detail |")
        L.append("|---|---|---|---|---|")
        for f in findings:
            sev = str(f.get("severity", "low")).lower()
            L.append(f"| {SEV_BADGE.get(sev, sev)} "
                     f"| {md_escape_cell(f.get('heuristic'))} "
                     f"| {md_escape_cell(f.get('_persona'))} "
                     f"| {md_escape_cell(f.get('title'))} "
                     f"| {md_escape_cell(f.get('detail'))} |")
        L.append("")

    # ---- per persona ----
    for p in personas:
        L.append(f"## {p.get('name', 'Persona')}")
        L.append("")
        if p.get("bio"):
            L.append(f"_{p['bio']}_")
            L.append("")
        if p.get("traits"):
            L.append(f"**Traits:** {', '.join(p['traits'])}  ")
        if p.get("rationale"):
            L.append(f"**Why tested:** {p['rationale']}")
        L.append("")

        for j in p.get("journeys", []):
            L.append(f"### {j.get('goal', 'Journey')} — "
                     f"{RESULT_BADGE.get(j.get('result'), j.get('result', '?'))}")
            L.append("")
            fn = j.get("functional", {})
            if fn.get("detail"):
                L.append(f"**Functional ({fn.get('status', '?')}):** {fn['detail']}")
                L.append("")

            steps = j.get("steps", [])
            if steps:
                L.append("| # | Action | Observation | | Screenshot |")
                L.append("|---|---|---|---|---|")
                for s in steps:
                    shot = rel(s.get("screenshot"), out_dir)
                    img = f"![step {s.get('n', '')}]({shot})" if shot else ""
                    L.append(f"| {s.get('n', '')} "
                             f"| {md_escape_cell(s.get('action'))} "
                             f"| {md_escape_cell(s.get('observation'))} "
                             f"| {STATUS_BADGE.get(s.get('status'), '')} "
                             f"| {img} |")
                L.append("")

            fr = j.get("friction", [])
            if fr:
                fr_sorted = sorted(fr, key=lambda f: SEV_ORDER.get(
                    str(f.get("severity", "low")).lower(), 3))
                L.append("**Friction findings:**")
                L.append("")
                for f in fr_sorted:
                    sev = str(f.get("severity", "low")).lower()
                    line = (f"- {SEV_BADGE.get(sev, sev)} "
                            f"**{f.get('title', '(untitled)')}** "
                            f"_({f.get('heuristic', 'n/a')})_ — {f.get('detail', '')}")
                    L.append(line)
                    shot = rel(f.get("screenshot"), out_dir)
                    if shot:
                        L.append(f"  ![{md_escape_cell(f.get('title'))}]({shot})")
                L.append("")

    L.append("---")
    L.append("")
    L.append("_Generated by the persona-app-testing skill. "
             "Findings are scored per persona against references/friction-rubric.md._")
    return "\n".join(L) + "\n"


def main(argv):
    ap = argparse.ArgumentParser(description="Render persona-testing results to Markdown.")
    ap.add_argument("results", help="path to results.json")
    ap.add_argument("--out", default="-",
                    help="output Markdown path (default: stdout)")
    ap.add_argument("--generated", default="",
                    help="timestamp string to stamp in the report (e.g. date -u +%%FT%%TZ)")
    a = ap.parse_args(argv)

    try:
        with open(a.results, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return err(f"results file not found: {a.results}")
    except json.JSONDecodeError as e:
        return err(f"invalid JSON in {a.results}: {e}")

    if not isinstance(data, dict) or "personas" not in data:
        return err("results JSON must be an object with a 'personas' array "
                   "(see references/results-schema.md).")

    out_dir = os.path.dirname(os.path.abspath(a.out)) if a.out != "-" else os.getcwd()
    md = render(data, out_dir, a.generated)

    if a.out == "-":
        sys.stdout.write(md)
    else:
        os.makedirs(out_dir, exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"wrote {a.out} "
              f"({len(data.get('personas', []))} personas)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
