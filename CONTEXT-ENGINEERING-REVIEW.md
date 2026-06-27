# Context-Engineering Review — `agentic_eng`

Review of the artefact library against your caching / model-choice / context
recommendations, mapped to the levers you actually control in a Claude Code
setup. Prioritized, file-anchored. Nothing here has been changed — these are
recommendations.

---

## The reframe (read this first)

Your pasted recommendations are mostly **API / application-layer** techniques:
manual `cache_control` breakpoints, `max_tokens: 0` pre-warm, in-code model
routing, reading `cache_read_input_tokens`, RAG retrieval. Those apply when *you*
own the request loop.

This repo is a **Claude Code artefact library** (your `settings.json` `_comment`
says so — it's merged into target projects). In Claude Code the **harness owns the
request loop**: caching is automatic, breakpoints are placed for you, compaction
is built in. So the principles still hold, but the levers you actually touch are:

| Principle (yours) | API-layer lever | Your actual lever in this repo |
|---|---|---|
| Caching | manual breakpoints, pre-warm | keep `CLAUDE.md` + skill descriptions + settings **stable & small**; don't put volatile data in the cached prefix |
| Model choice / cascade | route in code | **`model:` in subagent frontmatter**; model-free hooks; main model |
| Minimal context | trim the prompt, RAG | **progressive disclosure** (skill bodies load on demand), **subagent isolation**, tool/MCP surface |
| Compaction / context editing | manage history yourself | `/compact` at slice gates; `TASKS.md`+`SPEC.md` as rehydration memory |

The rest of this doc works through each, highest-leverage first.

---

## P0 — biggest win, lowest effort

### 1. Assign models to your subagents — your cascade is unbuilt

This is your "router/cascade" recommendation, and right now it's missing.

None of `agents/code-reviewer.md`, `agents/goldfish-spec-reviewer.md`, or
`agents/unit-test-generator.md` set a `model:` in frontmatter, so all three
**inherit the main model**. You have the *structure* of a cascade (cheap
deterministic hooks → judgment subagents) but no actual model tiering on the
expensive tier.

You already nailed the cheapest tier: `hooks/lint-dispatch.sh` and
`hooks/test-runner.sh` **call no model at all** — that's the "deterministic first
pass" of a cascade done perfectly. Build the rest on top:

- `unit-test-generator` → **Sonnet 4.6**. Bounded, idiom-driven test writing.
- `code-reviewer` → **Sonnet 4.6** default; promote to **Opus 4.8** only in its
  `deep` mode (large / high-risk diffs — the mode already exists in the agent).
- `goldfish-spec-reviewer` → **Sonnet 4.6** for Comprehension (G1) and Readiness
  (G3); consider **Opus 4.8** for the Critic pass (G2), where catching subtle
  correctness gaps is exactly where escalation pays back.
- Main orchestrator → **Sonnet 4.6** (your stated default).
- **Haiku**: none of the three qualify — they're all judgment work. Don't force
  it; that's the right call, not a gap.

Add to each subagent's YAML frontmatter, e.g.:

```yaml
---
name: code-reviewer
model: sonnet        # deep-mode runs can be promoted to opus
...
---
```

Honor your own rule — "escalate to Opus only where you can **measure** you need
it." So: default everything to Sonnet, ship, and promote G2-critic / deep-review
to Opus only if you observe missed findings.

### 2. Actually measure caching (you can't tune what you don't watch)

Your last caching bullet — confirm via `cache_read_input_tokens` — is the one to
keep, but in Claude Code you read it differently:

- Run `/cost` in a session to see token split and cache hit rate.
- If you've enabled OpenTelemetry, the same `cache_read_input_tokens` /
  `cache_creation_input_tokens` fields are emitted as metrics.

Make this a habit before/after the changes below, so every optimization is
evidence-based rather than assumed.

---

## P1 — real savings, modest effort

### 3. Trim duplicated text in the long skill bodies

A skill's **body loads in full into context the moment it's invoked**. Several of
yours restate the same rule 3–4×, which inflates active-context tokens (cost +
attention dilution) every time that skill is active.

Worst offender: `skills/spec-interviewer/SKILL.md` (158 lines) states the
vertical-slice / value-check rule in **four** places — the `## Value Check`
section, `## Workflow` step 3, and two bullets under `## Rules`. Same pattern in
`skills/auto-commit/SKILL.md` (the "stage only vetted files / never `git add .`"
rule appears in Hard Rules, Workflow step 6, **and** the Do/Don't list) and
`skills/code-review/SKILL.md` (Routing logic restated across Workflow, Routing,
and Hard Rules).

Action: collapse each rule to **one** authoritative statement and let the
workflow steps *reference* it. Target the four longest bodies first
(spec-interviewer, plan-slices, code-review, auto-commit). Keep the descriptions
untouched — those are your trigger index (see #6).

### 4. Make compaction explicit at slice boundaries

You've already built the right substrate for "compaction / context editing for
long agents": `plan-slices/SKILL.md` itself says that if the agent loses context
mid-build, re-reading `TASKS.md` (and the `SPEC.md` it points to) re-orients it.
That's durable external memory done right.

Make it active, not just a fallback: treat each **slice gate** (`/auto-commit`
success) as a natural `/compact` checkpoint. The inner loop is bounded, the
outcome is already persisted to `TASKS.md`, so compacting there reclaims the
window with near-zero information loss. Add one line to the CLAUDE.md gate #2 or
the plan-slices loop: "compact at the slice boundary; `TASKS.md`/`SPEC.md`
rehydrate the next slice."

---

## P2 — hygiene & situational

### 5. Curate the MCP / tool surface in target projects

Every connected MCP server's tool schemas sit in the **cached prefix** — stable
(good for cache) but they still consume tokens and dilute attention on every
turn. When you merge this library into a real project, load only the MCP servers
that project needs. (Your `settings.json` `allow`/`deny` lists are broad, but
that's *permissions*, not context — they don't cost tokens. The thing to watch is
MCP **server count**, not allow-list length.)

Your subagent tool sets are already tight — `goldfish-spec-reviewer` is
Read/Glob/Grep only; keep them minimal as you add agents.

### 6. Keep `CLAUDE.md` minimal and volatile-free (guardrail)

`CLAUDE.md` is the most-cached, always-loaded text in the project — it's 1,962
bytes today, which is excellent. Two guardrails so it stays that way:

- Never put **volatile data** (dates, counts, "current status") into the file
  itself — it would bust the cached prefix on every change. (Yours is clean; the
  `currentDate`/`userEmail` you see are injected by the harness, not in your
  file — leave it that way.)
- Keep honoring "rules live in the skill, don't restate here" (line 31). That one
  line is doing a lot of context-hygiene work.

### 7. Optional: constrain `code-reviewer` Bash to read-only in settings

`agents/code-reviewer.md` grants `Bash` and *instructs* it to stay read-only
(`git diff`/`gh pr view` only). That's prompt-level enforcement. If you want it
mechanical, scope the agent's Bash via settings to the read-only git/gh verbs
rather than relying on instruction-following. Low priority — but it's the same
"deterministic > model judgment" principle your hooks already embody.

---

## What you're already doing right (don't "fix" these)

- **Model-free deterministic hooks** (`lint-dispatch.sh`, `test-runner.sh`) — the
  cheapest possible tier of a cascade. Optimal.
- **Fresh-eyes subagents as context isolation** — the Goldfish "no memory" design
  isn't just bias-removal; it's *context editing as a feature*. The main thread
  never carries the reviewer's working set. This is your strongest existing
  context-engineering move.
- **`unit-testing` shared + per-stack split** — textbook progressive disclosure:
  only the one relevant stack body (python/go/nodejs/flutter-dart) loads, never
  all four. This is your "RAG" — the skill **description** is the retrieval index,
  the body is the chunk fetched on demand.
- **`SPEC.md` + `TASKS.md` as durable memory** — the correct answer to
  long-agent context growth.
- **Sharp skill descriptions** — accurate triggering means the *right* body
  loads, so you don't pay context for a wrongly-invoked skill.

---

## One-glance priority list

1. **P0** — Add `model:` frontmatter to the 3 subagents; tier Sonnet→Opus by risk. *(your cascade)*
2. **P0** — Start reading `/cost` cache stats; measure before/after. *(your "confirm caching")*
3. **P1** — Dedupe repeated rules in the 4 longest skill bodies. *(minimal context)*
4. **P1** — `/compact` at slice gates; lean on `TASKS.md`/`SPEC.md` to rehydrate. *(compaction)*
5. **P2** — Curate MCP server count in target projects. *(minimal context / caching)*
6. **P2** — Keep `CLAUDE.md` small & volatile-free. *(caching guardrail)*
7. **P2** — Optionally lock `code-reviewer` to read-only Bash in settings. *(determinism)*

RAG over an external knowledge base isn't applicable here — your skill library
*is* the retrievable knowledge, already lazy-loaded by description. Pre-warming
with `max_tokens: 0` and manual breakpoints aren't reachable from Claude Code;
the harness handles them.
