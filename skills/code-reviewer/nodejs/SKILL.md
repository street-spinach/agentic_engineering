---
name: code-reviewer-nodejs
description: Language-specific code-review concerns for Node.js / JavaScript / TypeScript. Use together with the shared code-reviewer skill when the nearest manifest is package.json (or the changed file is .js/.ts/.mjs). Holds JS/TS idioms, footguns, and anti-patterns only — the shared skill owns the cross-language checklist and severity rules.
---

# Code Reviewer — Node.js / JS / TS

Language concerns only. The cross-language checklist, severity rules, and report
style live in the shared `skills/code-reviewer/SKILL.md`. Mirror the repo's style.

## Idioms & conventions

`const`/`let`, never `var`; `===` over `==`. `async/await` over raw `.then` chains.
Optional chaining `?.` and nullish coalescing `??` (not `||`, which eats `0`/`""`).
In TS: prefer precise types over `any`; `unknown` at boundaries; narrow before use.

## Common bugs & footguns

- `||` for defaults swallows falsy values (`0`, `""`, `false`) — use `??`.
- Floating promises — an `async` call not awaited or `.catch`-ed loses errors.
- `this` rebinding in callbacks; use arrow functions or bind.
- Mutating shared objects/arrays passed by reference; spread/clone before changing.
- `for...in` over arrays (iterates keys/proto) — use `for...of` / `.map`.
- `JSON.parse` without a try/catch on untrusted input.

## Error handling

`await` inside `try/catch`; an unhandled rejection can crash the process. Don't
`catch` and silently `return`. Reject/throw `Error` objects, not strings. In
Express-style code, forward errors to the error middleware (`next(err)`), don't
swallow. Clean up (timers, listeners, handles) in `finally`.

## Concurrency / async

Single-threaded event loop — never block it with sync CPU work or sync FS calls in
a request path. Parallelize independent awaits with `Promise.all` instead of
serial `await`s. Beware unbounded concurrency (fan-out with no limit). Always
remove event listeners you add to avoid leaks.

## Performance notes

Avoid `await` in a loop when calls are independent (`Promise.all`); don't rebuild
big objects per request; stream large payloads instead of buffering. Avoid sync
APIs (`fs.readFileSync`) on the hot path.

## Anti-patterns

- `any` everywhere in TS; `// @ts-ignore` masking a real type error.
- Empty `catch {}`; mixing callbacks and promises for the same flow.
- Deeply nested `.then`; new `Promise` wrapping an already-promise API.
- Mutating function arguments; module-level mutable singletons holding request state.
