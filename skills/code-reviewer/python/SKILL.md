---
name: code-reviewer-python
description: Language-specific code-review concerns for Python. Use together with the shared code-reviewer skill when the nearest manifest is pyproject.toml/setup.py (or the changed file is .py). Holds Python idioms, footguns, and anti-patterns only — the shared skill owns the cross-language checklist and severity rules.
---

# Code Reviewer — Python

Language concerns only. The cross-language checklist, severity rules, and report
style live in the shared `skills/code-reviewer/SKILL.md`. Mirror the repo's style.

## Idioms & conventions

Comprehensions over manual loops where they read clearly; `enumerate`/`zip` over
index math; context managers (`with`) for any resource; f-strings over `%`/
`.format`; `pathlib` over `os.path` string juggling; dataclasses / `NamedTuple`
for plain records. Prefer EAFP (`try/except`) over LBYL when it's idiomatic.

## Common bugs & footguns

- **Mutable default args** (`def f(x=[])`) — shared across calls; use `None`.
- **Late binding in closures / loops** — lambdas capturing the loop variable.
- Truthiness traps: `if x:` rejects `0`/`""`/empty — use `is None` when you mean None.
- `==` vs `is` (only `is` for `None`/singletons); integer caching masking `is` bugs.
- Aliasing: assigning a list/dict copies the reference, not the data.

## Error handling

Catch the **narrowest** exception; never bare `except:` (it eats
`KeyboardInterrupt`). Don't swallow — re-raise or log with context. Use
`raise ... from e` to preserve the cause. `finally` / context managers for cleanup.

## Concurrency / async

The **GIL** means threads don't parallelize CPU work — use processes for CPU,
async/threads for I/O. In `async` code: never call blocking I/O in a coroutine;
don't forget to `await`; gather with `asyncio.gather`. Watch shared state across tasks.

## Performance notes

Avoid building large intermediate lists when a generator suffices; hoist invariant
work out of loops; use `set`/`dict` membership over list scans; prefer
`str.join` over `+=` in a loop. Don't micro-optimize cold paths.

## Anti-patterns

- `except: pass` (silent failure); broad `except Exception` with no handling.
- Mutating a list/dict while iterating it.
- `from module import *`; deep monkeypatching of internals.
- Type hints that lie (annotated `str`, returns `None`).
