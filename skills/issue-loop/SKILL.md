---
name: Issue Loop
description: Autonomous outer loop that fixes GitHub issues end to end — fetch agent-ready issues, triage and route each, run the existing per-slice build loop, then merge, deploy to staging, and verify the deployed surface, iterating until green before looping to the next issue. Sequential; autonomous through staging; production stays human-gated. The issue-side twin of plan-slices. Orchestrates existing skills, subagents, and hooks — it does not reimplement them.
---

# Issue Loop

## Purpose

The **execution spine for issue-driven work**, exactly as `/plan-slices` is the
spine for spec-driven work. It turns a backlog of GitHub issues into a stream of
fixed-and-verified changes, one issue at a time, incrementally — fix → test →
deploy → test-what-you-deployed → next. It owns only ingestion, routing
orchestration, the deploy→verify stage, and the circuit breaker. **Every gate is
an existing component**; this skill delegates, it does not duplicate.

## When to Use

When the intent is "work the issue backlog" / "fix the open bugs." Skip it for a
single hand-authored feature — that's the `/spec-interviewer` → `/plan-slices`
path.

## Ingestion & Order

- Fetch with `gh issue list --label agent-ready --state open` (plus the repo's
  own filters).
- Order by **linked dependency** first (an issue that unblocks others goes first),
  then by **priority label**.
- Process **sequentially** — one issue fully through the pipeline before the next.
- **Idempotent:** skip issues already closed or carrying the `verified` label, so
  a re-run resumes rather than repeats. (This is what lets the loop run on a
  schedule.)

## Per-Issue Pipeline (delegation map)

Each step is an existing skill/subagent/hook unless marked **[new]**.

1. **Route** — `/issue-triage` returns `implement | spec | spec+harden | park`.
   - `park` → skip, continue to the next issue.
2. **Spec** (only if routed there) — `/spec-interviewer` seeded from the issue
   text + comments (no live interview), then `/harden-spec` (goldfish ×3) when the
   route is `spec+harden`. If harden can't reach readiness from the text, park the
   issue and continue.
3. **Plan** — `/plan-slices` → `TASKS.md` (usually a single slice for a bug). For
   the `implement` route, synthesize that one slice directly from the triage seed
   (acceptance = the issue's expected behaviour); no spec.
4. **Inner build loop (existing, unchanged)** — implement →
   `unit-test-generator` → lint + `test-runner` hooks **including integration
   tests (testcontainers)** → `/code-verifier` must APPROVE → `/auto-commit`.
5. **Classify surface** **[new]** — `/deploy` reads the diff and reports whether
   the change exposes an observable interface.
   - **No surface** (internal/refactor) → confirm unit+integration green, merge,
     close, next.
   - **Has surface** → continue.
6. **Merge-first** — open a PR and merge to `main` on a green inner loop.
7. **Deploy** **[new]** — `/deploy` puts `main` on staging.
8. **Verify** **[new]** — `/post-deploy-verify` runs the scoped tests, then the
   fresh-eyes **`deploy-verifier`** subagent judges the evidence against the
   issue's acceptance (the `code-verifier` pattern, one layer out).
9. **Verify gate**:
   - **green** → comment the results on the issue, add the `verified` label,
     close it → next issue.
   - **red** → revert `main` to green, then fix (re-enter step 4), redeploy, and
     re-verify. **Iterate until green.**
10. **Circuit breaker** **[new]** — after **3** failed verify cycles on one
    issue, halt the run: leave `main` reverted to green, post the accumulated logs
    to the issue, and surface it to a human. (The escape hatch — the queue is
    sequential, so a non-convergent issue would otherwise block everything.)

Repeat until the queue is empty and every processed issue is verified (or parked /
breaker-halted with a human surfaced).

## Subagents in the loop

Most gates here are judged by a **fresh-eyes subagent**, not by this orchestrator —
that is the point of delegating:

- `goldfish-spec-reviewer` — at the harden gate (medium/high complexity), ×3.
- `unit-test-generator` — full behavioural coverage inside the inner loop.
- `code-verifier` — the pre-commit / pre-merge review of the diff against the spec.
- `deploy-verifier` — **[new]** the post-deploy gate: judges the deployed surface
  against the issue's acceptance, with no memory of how the fix was written.

The orchestrator itself stays in the **main thread** (like `/plan-slices`) and runs
`/compact` at each issue boundary to keep its context lean across the queue —
context isolation comes from the subagents and compaction, not from a per-issue
worker agent. **Context budget:** treat each issue close as a `/compact` seam;
mid-issue, if the window passes ~60% off a seam, checkpoint to `TASKS.md` and
compact (see `CLAUDE.md` → Compact Instructions).

## Parallel mode (worktrees) — optional

Sequential (`N = 1`) is the default and needs nothing here. To raise throughput on
independent issues, raise the concurrency dial `N`:

- **Fan-out.** Select a batch of up to `N` issues with *disjoint file scope* (use
  triage's affected-scope hint; never batch two issues that touch the same files).
  Launch one worker per issue with **git-worktree isolation** — its own branch and
  checkout — each running steps 1–4 (triage → spec → inner loop → `code-verifier`
  → local commit) independently. The fresh-eyes subagents run inside each worker,
  so the orchestrator's context stays lean.
- **Fan-in (serialized).** Integrate ready branches one at a time: rebase on latest
  `main` → merge → `/deploy` → `/post-deploy-verify` → close. This lane stays
  serial because `main` and the shared staging env are shared resources.
- **Conflict.** A rebase conflict (an overlapping issue landed first) sends that
  worker back to re-run on fresh `main`, or parks the issue. Disjoint-scope
  batching keeps this rare.
- **Higher throughput (more infra).** To parallelize the integration lane too, give
  each branch an ephemeral preview env and serialize merges through a merge queue
  with re-verify on conflict.

Parallelism multiplies concurrent token spend and adds rework risk; with one shared
staging env the integration lane is the bottleneck, so most of the gain is in
fix + review. Use the telemetry layer (cost per issue, throughput) to decide
whether `N > 1` earns its cost.

## Hard Rules

- **Reuse, don't reimplement.** Every gate above is an existing skill/subagent/
  hook. This skill adds only ingestion, orchestration, deploy→verify, and the
  breaker. If you find yourself restating review, testing, commit, or spec logic
  here, stop — call the skill that owns it.
- **Sequential by default; parallel is an opt-in dial.** Concurrency `N` defaults
  to 1 (today's behaviour). With `N > 1`, the *fix* phase fans out across
  worktree-isolated workers while the *integration* lane (merge → deploy → verify)
  stays serialized — see **Parallel mode**. Never let two issues share a working
  tree or race a merge.
- **Autonomy boundary.** This loop authorizes push, PR, merge, and **staging**
  deploy without prompting. The `/auto-commit` hard-stops still apply unchanged —
  secrets, a direct commit to a protected branch, out-of-scope files all halt.
  The **production release is human-gated and never automatic.**
- **Park or surface — never silently stall.** A parked issue, a non-converging
  inner loop, or a breaker halt must be reported, not swallowed.
- **This and no more.** Fix the issue to its acceptance criteria; extra ideas
  become new issues, not scope creep.

## Failure Behavior

- **`gh` missing/unauthenticated** → stop, explain; do nothing destructive.
- **Triage parks** → skip, continue.
- **Inner loop won't converge** (code-verifier never APPROVEs within the bound) →
  park the issue with the findings, continue.
- **Verify red** → iterate (step 9); breaker at 3 cycles → halt the run.
- **Hard-stop** (secret / protected branch / out-of-scope) → halt and surface;
  never bypass with `--no-verify` or a force-push.
