---
name: unit-testing-flutter-dart
description: Stack-specific unit-testing idioms for Flutter / Dart. Use together with the shared unit-testing policy when the nearest manifest is pubspec.yaml (or the changed file is .dart). Holds runner, layout, mocking, assertion, and coverage idioms only — the shared skill owns classification, coverage depth, and guardrails.
---

# Unit Testing — Flutter / Dart

Stack idioms only. Classification, coverage depth, and guardrails live in the
shared `skills/unit-testing/SKILL.md`. Mirror whatever the repo already uses.

## Framework & runner

`flutter_test` for code that imports Flutter; plain `dart test` for pure Dart
packages. Run via `flutter test` / `dart test`. Don't introduce a second runner.

## File naming & location

`*_test.dart` under `test/`, mirroring `lib/`'s structure
(`lib/auth/token.dart` → `test/auth/token_test.dart`).

## Mocking / stubbing idiom

`mocktail` (no codegen) or `mockito` (`@GenerateMocks` + build_runner) — match
the package the repo already uses. Mock boundaries only; use real value objects.

## Assertion style

`group` / `test` / `expect` with matchers (`equals`, `throwsA`, `isA<T>()`,
`closeTo`). For async, `await expectLater(..., emitsInOrder([...]))`.

## Idiomatic patterns

- `setUp` / `tearDown` for fixtures; one behavior per `test`.
- Inject `Clock` / dependencies via constructor; never read wall-clock in a test.
- `widget_test` (`testWidgets` + `WidgetTester` + `pumpWidget`) only for widget
  behavior — keep pure logic in plain unit tests.

## Measuring coverage

`flutter test --coverage` / `dart test --coverage=coverage` → `coverage/lcov.info`.

## Stack-specific anti-patterns

- Don't `pumpWidget` to test logic that has no widget.
- Don't assert on rendered pixels / golden files for branching logic.
- Don't over-stub with `any()` everywhere — it hides contract drift.
