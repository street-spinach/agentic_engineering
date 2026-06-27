---
name: code-reviewer-flutter-dart
description: Language-specific code-review concerns for Flutter / Dart. Use together with the shared code-reviewer skill when the nearest manifest is pubspec.yaml (or the changed file is .dart). Holds Dart/Flutter idioms, footguns, and anti-patterns only — the shared skill owns the cross-language checklist and severity rules.
---

# Code Reviewer — Flutter / Dart

Language concerns only. The cross-language checklist, severity rules, and report
style live in the shared `skills/code-reviewer/SKILL.md`. Mirror the repo's style.

## Idioms & conventions

`final`/`const` by default; `const` constructors for stateless widgets (rebuild
perf). Sound null safety — avoid `!` unless provably non-null; prefer `?.`, `??`,
and `late` only when justified. Small widgets over deep `build` methods. Use
`Theme`/`MediaQuery` over hardcoded sizes.

## Common bugs & footguns

- **`BuildContext` used across an `async` gap** — guard with `if (!mounted) return;`.
- `!` null-assertion that can actually be null → runtime crash.
- Missing `dispose()` for controllers, `AnimationController`, `StreamSubscription`,
  `FocusNode` — leaks and "setState after dispose".
- Rebuilding expensive widgets because `const` was omitted.
- `==`/`hashCode` not overridden on value types used as keys/in sets.

## Error handling

`try/catch` around `await`ed futures; handle `Future` errors (don't leave them
uncaught). Surface errors to the UI (error state / `SnackBar`), don't swallow.
`FutureBuilder`/`StreamBuilder` must handle `hasError` and the loading state, not
just data.

## Concurrency / async

Don't block the UI isolate with heavy sync work — use `compute`/isolates. Always
cancel `StreamSubscription`s in `dispose`. Avoid `setState` after an `await` if the
widget may be unmounted. Sequential `await`s that could be `Future.wait` waste time.

## Performance notes

`const` widgets to skip rebuilds; `ListView.builder` (lazy) over building all
children; keep `build` cheap and side-effect-free; avoid allocating closures/objects
in `build` on a hot path; use keys to preserve element state across rebuilds.

## Anti-patterns

- Logic, network calls, or heavy work inside `build()`.
- `setState` in a loop, or for state a parent should own.
- Giant single-widget `build` methods; deeply nested ternaries in the tree.
- Swallowing errors in `FutureBuilder`/`StreamBuilder`; ignoring `mounted`.
