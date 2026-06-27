# Runbook — running the issue loop

How to kick off the autonomous GitHub-issue fixing loop. Design lives in
`issue-loop-design.md`; this is just how to start and what to expect.

## Before the first run

- The `agentic-eng` plugin is installed in the target repo (skills + agents + hooks
  + `settings.json` merged into `.claude/`).
- Issues you want worked are labelled **`agent-ready`**.
- Have ready (the loop will ask before the first deploy — it won't guess):
  1. the repo's **staging deploy / build command**;
  2. the **Postman/Newman collection** location (for backend interface checks).
- Optional — token/cost dashboards live during the run:
  ```
  docker compose -f observability/docker-compose.yml up -d
  ```
  then set `CLAUDE_CODE_ENABLE_TELEMETRY` to `1` in `settings.json` (or export it).

## Kickoff prompt (first run — dry run, then go)

Run from inside the target repo. Replace `<owner/repo>`.

```
Run /issue-loop on <owner/repo>, following docs/issue-loop-design.md.

Scope: open issues labelled `agent-ready`, ordered by linked dependency then
priority. Process sequentially (N=1).

Per issue — triage (type + complexity) and route: low/med bugs straight to
implement; high bugs and all features through /spec-interviewer, adding
/harden-spec for medium/high complexity; park anything too vague to spec
(label needs-human, comment what's missing, continue). Then the inner loop:
implement → unit-test-generator → lint + tests + testcontainers → /code-verifier
must APPROVE → /auto-commit.

Then classify the diff: internal-only → gate on unit+integration, merge, next;
surface-changing → PR + merge to main → /deploy to staging → /post-deploy-verify
(deploy-verifier judges the deployed surface against the issue's acceptance,
scoped to the diff). Green → comment results, add `verified`, close. Red → revert
main, fix, redeploy, iterate until green; after 3 failed verify cycles on one
issue, stop the run with main left green and surface it to me.

Autonomy: push, PR, merge, and staging deploy are authorised — no need to ask.
Production is mine; never deploy to production. Hard-stop on secrets, a
protected-branch commit, or out-of-scope files. Compact at each seam.

Before the first deploy, confirm with me: (1) this repo's staging deploy/build
command, and (2) the Postman/Newman collection location — don't guess.

First: dry run. List the issues you'd work, with the route + complexity you'd
assign to each, then pause for my go-ahead before touching code.
```

## Routine run (after the first is validated)

The `CLAUDE.md` front door already maps issue-backlog intent to the loop:

```
Run /issue-loop for open `agent-ready` issues. Autonomous through staging,
production gated, 3-cycle breaker. Go.
```

## Parallel run (optional, opt-in)

Raise the concurrency dial; fix phase fans out across worktree-isolated workers,
integration stays serial (see the issue-loop skill's *Parallel mode*):

```
Run /issue-loop for open `agent-ready` issues with concurrency N=3. Batch only
issues with disjoint file scope; integration lane stays serial. Go.
```

## Where it will pause / stop

- **Before the first deploy** — to confirm the deploy command + Newman collection.
- **Dry-run go-ahead** — after listing the plan (first run only).
- **A parked issue** — too vague to spec; labelled `needs-human`, loop continues.
- **Circuit breaker** — 3 failed verify cycles on one issue: run halts, `main` left
  green, logs on the issue.
- **Hard-stop** — secrets, a protected-branch commit, or out-of-scope files.
- **Production release** — always yours; the loop never does it.

## See also

- `docs/issue-loop-design.md` — the full design and decisions.
- `docs/context-management.md` — context-health strategy (compact at seams).
- `observability/README.md` — token/cost telemetry.
