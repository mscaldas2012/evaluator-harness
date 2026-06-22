# Runner Maintainability Refactor

## Goal

Improve `src/evaluator_harness/runner.py` file-level maintainability by extracting cohesive concerns from `ExperimentRunner` while preserving current CLI and runtime behavior.

## Quality Targets

- Refactor all good-candidate runner concerns in this pass, not just enough to clear the first gate.
- Remove D-ranked Radon complexity from `runner.py`.
- Improve `runner.py` file-level maintainability index where Radon reflects the split.
- Preserve public behavior for run, review selection, trace metadata, request metadata, campaign, and exports.

## Scope

1. Add characterization coverage around trace/request metadata and review routing behavior.
2. Extract trace and request metadata builders into a dedicated module.
3. Extract review selection and annotation queue routing orchestration into a dedicated module.
4. Reassess remaining `runner.py` C/B hotspots and extract additional cohesive helpers when the move is low risk.
5. Keep `ExperimentRunner` as the public facade used by CLI and tests.

## Verification

- `uv run pytest --no-cov -p no:cacheprovider <focused tests>`
- `uv run ruff check <changed files> --no-cache`
- `uv run pyright src/evaluator_harness/runner.py <new modules>`
- `uv run radon cc src/evaluator_harness/runner.py -s`
- `uv run radon mi src/evaluator_harness/runner.py -s`
- `graphify update .`
