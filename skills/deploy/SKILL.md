---
name: Deploy
description: Deploy a merged change to a staging target, adapting to what changed — a backend service (api/bff/agent) is deployed to staging; an app change is built and installed on an emulator/simulator. Classifies the change surface from the diff, stands up only what's affected, is idempotent and safe to re-run, and returns a handle (staging URL or device id) plus the changed-surface manifest for verification. Staging only — never production.
---

# Deploy

## Purpose

Stand the change up so it can be tested **as deployed** — the step the spec-driven
loop never had. Invoked by `/issue-loop` after merge. It also owns the
**surface classification** the loop keys its branching on: does this diff expose an
observable interface, and if so, which endpoints/screens changed?

## When to Use

Called by `/issue-loop` after a change is merged to `main`. Re-invoked on every
iterate-until-green cycle (so it must be idempotent). Internal-only changes get
classified and returned without a deploy.

## Classify (from the diff)

Read the diff and determine the **surface**:

- **backend** — service/handler/route/controller files, API schemas, an agent's
  tool/endpoint surface.
- **app** — a mobile screen/module/flow.
- **internal-only** — refactors, helpers, config with no externally observable
  interface change.

Emit `{ surface, changed: [endpoints | screens] }` so `/post-deploy-verify` can
scope itself to exactly what moved.

## Workflow

1. **Classify** surface + changed entities from the diff.
2. **Internal-only** → report "no deploy needed" with the classification and
   return. (`/issue-loop` then gates on unit+integration and merges.)
3. **Backend** → run the project's configured staging deploy entrypoint; wait for
   healthy; return the staging URL.
4. **App** → build the changed app; install on the emulator/simulator; return the
   device handle.
5. **Return** the handle + the changed-surface manifest. On failure, return the
   deploy logs — don't mask them.

## Hard Rules

- **Staging only.** Never deploy to production — that is `/issue-loop`'s human
  gate. Refuse any production target.
- **Project-configured command.** Read the deploy/build entrypoint from project
  config (or `CLAUDE.md`). If none is configured, **stop and ask** for it — never
  guess a deploy command.
- **Idempotent.** Safe to run repeatedly on the iterate-until-green path; replace
  or tear down the prior staging deploy rather than stacking instances.
- **Deploy only.** No commits, no merges, no test execution — return a handle and
  hand off to `/post-deploy-verify`.

## Failure Behavior

- **No deploy command configured** → stop, name what's needed (the per-stack
  entrypoint), deploy nothing.
- **Deploy/build fails or never goes healthy** → return the logs and a failed
  status so `/issue-loop` treats it as a red verify cycle (revert + iterate).
- **Production target requested** → refuse and surface.
