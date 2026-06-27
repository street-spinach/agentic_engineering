---
name: Post-Deploy Verify
description: Orchestrates the deployed-surface verification gate — gathers scoped evidence on staging (runs the relevant Postman/Newman requests for a backend, or invokes the android/ios/persona app-testing skills for an app), then runs the fresh-eyes deploy-verifier subagent to judge that evidence against the issue's acceptance. Consolidates a PASS/FAIL verdict and routes /issue-loop's verify gate. Scoped to the diff. Never deploys, commits, or merges.
---

# Post-Deploy Verify

## Purpose

The **"test what you deployed"** gate — `/code-verifier` one layer out. Where
`/code-verifier` drives a fresh-eyes subagent against the diff and `SPEC.md`, this
skill drives the fresh-eyes `deploy-verifier` subagent against the **deployed
behaviour** and the **issue's acceptance**. It keeps the workflow's standing split:
deterministic execution (run the scoped tests, gather evidence) lives here;
judgment (is green real, was the right thing tested) lives in the subagent.

## When to Use

Invoked by `/issue-loop` after `/deploy`, for surface-changing issues. Skipped for
internal-only changes (those gate on unit + integration).

## Workflow

1. Take the **deploy handle** + **changed-surface manifest** from `/deploy`.
2. **Gather scoped evidence:**
   - **Backend** → run the Postman/Newman requests covering the changed endpoints
     (scope inferred from the diff + collection; a `path → surface` manifest is the
     fallback) against the staging URL. Capture the run output.
   - **App** → invoke `/android-app-testing`, `/ios-app-testing`, or
     `/persona-app-testing`, scoped to the changed screens. Capture the results.
3. **Invoke the `deploy-verifier` subagent by name** (Task tool / `@deploy-verifier`),
   handing it the staging handle, the changed-surface manifest, the issue's
   acceptance, and where the evidence lives. It judges — you do not.
4. **Consolidate** its verdict into a Deploy Verification Report.
5. **Route** on the verdict (below).

## Routing

- **PASS** → return green to `/issue-loop`'s gate → comment results, add `verified`,
  close the issue.
- **FAIL** → return the subagent's findings + logs to `/issue-loop`, which reverts
  `main`, fixes (re-enters the inner loop), redeploys, and re-verifies — bounded by
  the 3-cycle circuit breaker.

## Hard Rules

- **Scope to the change** — cover the changed endpoints/screens and their direct
  contracts; never run the whole suite as the gate.
- **Execution vs judgment, split** — this skill runs the scoped tests and gathers
  evidence; the `deploy-verifier` subagent (fresh eyes, no build memory) decides
  PASS/FAIL against acceptance. Don't make the verdict yourself.
- **Don't re-implement app-testing** — delegate to the `android/ios/persona` skills.
- **Verify only** — no deploy, no build, no commit, no merge. Re-deploys are
  `/deploy`'s job, driven by `/issue-loop`.

## Deploy Verification Report Format

```markdown
# Deploy Verification Report
## Verdict — PASS / FAIL, one-line reason.
## Acceptance trace — each criterion → evidence.
## Scope assessment — right surface exercised for this defect?
## Regressions — broken behaviour in the changed surface or neighbours.
## Gaps / flakiness — unverifiable claims, non-determinism.
## Next step — close + verified (PASS) · return to /issue-loop to iterate (FAIL).
```

## Failure Behavior

- **No collection / no scoped requests** for a changed backend interface → **FAIL**
  (a changed endpoint with zero verification is not a pass).
- **Staging unreachable** → FAIL with the connection error (never a silent pass).
- **App harness unavailable** (no emulator/simulator) → surface the setup gap; no
  false green.
