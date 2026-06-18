---
name: unit-testing-python
description: Stack-specific unit-testing idioms for Python. Use together with the shared unit-testing policy when the nearest manifest is pyproject.toml/setup.py (or the changed file is .py). Holds runner, layout, mocking, assertion, and coverage idioms only — the shared skill owns classification, coverage depth, and guardrails.
---

# Unit Testing — Python

Stack idioms only. Classification, coverage depth, and guardrails live in the
shared `skills/unit-testing/SKILL.md`. Mirror whatever the repo already uses.

## Framework & runner

`pytest`. Run via `pytest`. If the repo uses `unittest` instead, match it rather
than introducing pytest alongside it.

## File naming & location

`test_*.py` under `tests/` mirroring the package, or alongside the module —
follow the repo's existing layout.

## Mocking / stubbing idiom

`monkeypatch` for attributes / env, `unittest.mock` (`patch`, `MagicMock`) for
collaborators. Patch where the name is *used*, not where it's defined. Freeze the
clock; mock only boundaries.

## Assertion style

Plain `assert`; `pytest.raises(SomeError)` for negatives; `pytest.approx` for
floats. `assert x == expected`, not custom assert helpers that hide the diff.

## Idiomatic patterns

- `@pytest.fixture` for setup; `@pytest.mark.parametrize` for table-driven cases.
- One behavior per test, named `test_<behavior>`.
- Inject dependencies (clock, client) via args / fixtures for determinism.

## Measuring coverage

`pytest --cov=<package>` (pytest-cov). Scope a change by passing the test path:
`pytest tests/auth/test_token.py`.

## Stack-specific anti-patterns

- Don't patch deep internals when you can inject a fake collaborator.
- Don't assert on dict / set ordering, or on full `repr()` strings.
- Don't let a fixture hit a real network / DB — that's an integration test.
