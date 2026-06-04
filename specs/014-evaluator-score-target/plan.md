# Implementation Plan: Judge Evaluator Score Config Targeting

**Branch**: `014-evaluator-score-target` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-evaluator-score-target/spec.md`

## Summary

Ensure every Langfuse LLM-as-Judge evaluator rule created or updated by the
harness explicitly targets the resolved score config for that evaluator. The
score config target must come from score config sync for harness-managed scores
or from configured user-owned score config IDs. The evaluator setup plan,
Langfuse REST payloads, remote rule normalization, audit/reuse logic, CLI
preview output, bindings, and tests will all treat score config targeting as a
first-class part of judge evaluator setup so automated judge scores and human
annotation scores are comparable under the same score definitions.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing `pydantic`, `PyYAML`, `rich`, `httpx`,
`pytest`, Langfuse SDK/API wrapper code, and current harness config, runner,
annotation queue, prompt sync, score config sync, and evaluator setup helpers.

**Python Environment Management**: Use `uv` for dependency setup and command
execution. Prefer `uv run ...` for harness commands and tests.

**Storage**: Filesystem YAML for project configs, evaluator bindings, prompt
bindings, specs, and tests. Langfuse remains the remote system of record for
traces, scores, score configs, annotation queues, and evaluator rules.

**Testing**: `pytest` unit, contract, and integration tests using fake
Langfuse/provider clients and mocked REST transports by default. Live Langfuse
tests remain opt-in.

**Target Platform**: Local developer machines and CI runners.

**Project Type**: Local Python CLI.

**Performance Goals**: Adding score config targeting to evaluator setup should
not materially change sync runtime. The targeted regression suite should remain
small and complete within seconds in local fake-client tests.

**Constraints**: Do not delete or silently recreate evaluator rules to repair
score targeting. Do not take over evaluator rules without local binding or
equivalent harness ownership evidence. Preserve existing evaluator filtering,
variable mapping, catalog/custom source handling, model connection, sampling,
and activation behavior.

**Scale/Scope**: One project config is loaded and synced at a time. The change
must cover all evaluator definitions in a project, including DFE scenario
projects and both custom and Langfuse-managed catalog evaluators.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature strengthens Langfuse-native evaluator
  rules and score configs instead of adding local scoring or comparison logic.
- **Thin harness scope**: PASS. The design updates the existing local Python
  CLI sync path and does not introduce services, orchestration, or custom
  dashboards.
- **Dataset simplicity**: PASS. Dataset loading and CSV requirements are
  unchanged.
- **Reproducibility metadata**: PASS. Evaluator bindings and setup output will
  record score config target identity more accurately, improving auditability.
- **Baseline-centric workflow**: PASS. Baseline/candidate run behavior is
  unchanged; comparison remains delegated to Langfuse scores and dashboards.
- **Minimal local state**: PASS. Local state remains YAML bindings and config
  files. Langfuse remains the system of record for scores and evaluator rules.
- **Human review awareness**: PASS. The feature aligns automated judge scores
  with Human Annotation Queue score configs so human review can calibrate
  judge behavior.
- **Local-first execution**: PASS. The work remains runnable through
  `uv run python run_experiment.py ...` and pytest.

## Project Structure

### Documentation (this feature)

```text
specs/014-evaluator-score-target/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- judge-evaluator-score-targeting.md
|-- checklists/
|   `-- requirements.md
`-- spec.md
```

### Source Code (repository root)

```text
src/
`-- evaluator_harness/
    |-- cli.py
    |-- langfuse_client.py
    `-- langfuse_evaluator_setup.py

tests/
|-- contract/
|   `-- test_cli_sync_judge_evaluators.py
|-- integration/
|   `-- test_sync_judge_evaluators.py
`-- unit/
    |-- test_judge_setup_audit.py
    |-- test_judge_setup_planner.py
    `-- test_langfuse_evaluator_rest.py
```

**Structure Decision**: Keep the change inside existing evaluator setup and
Langfuse client modules. The CLI already displays evaluator score targets, so
only targeted output or validation adjustments should be added if current
output is insufficient. Tests stay near existing judge setup, REST fallback,
and sync behavior coverage.

## Complexity Tracking

No constitution violations.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Treat score config targeting as required evaluator rule setup, not local-only
  binding metadata.
- Use resolved score config IDs as the target value; names remain display and
  audit context.
- Normalize remote evaluator rule score config IDs from both snake_case and
  camelCase field names.
- Include score config target in create and safe update payloads.
- Block or fail clearly when score config targeting is required but no ID is
  available.

## Phase 1 Design

See [data-model.md](./data-model.md), [contracts/judge-evaluator-score-targeting.md](./contracts/judge-evaluator-score-targeting.md),
and [quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Payload targeting**: Add score config ID to evaluator rule create payloads
   and update payloads where supported, preserving existing evaluator rule
   fields.
2. **Remote normalization**: Normalize remote evaluator rule score config IDs
   into `score_config_id` so reuse, audit, and safe-update comparisons can
   detect alignment.
3. **Planning and validation**: Ensure planned evaluator setup blocks apply
   when score config IDs are unavailable and records expected score target name
   and ID.
4. **Mismatch handling**: Include score config target in safe update diffing for
   harness-managed evaluator rules, while preserving missing-binding safeguards.
5. **CLI and docs**: Confirm dry-run/audit output exposes target score config
   name and ID; update docs if existing output is insufficient.
6. **Tests**: Add failing-then-passing unit/contract/integration coverage for
   create payload targeting, catalog/custom evaluators, user-owned score config
   IDs, existing remote mismatch detection, and DFE score alignment.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The design uses Langfuse evaluator rules and score
  configs as intended and avoids local score comparison replacement.
- **Thin harness scope**: PASS. The implementation is a small change to current
  sync and audit paths.
- **Dataset simplicity**: PASS. No dataset changes.
- **Reproducibility metadata**: PASS. Bindings and audit output retain score
  config target context.
- **Baseline-centric workflow**: PASS. No baseline behavior changes.
- **Minimal local state**: PASS. Existing YAML bindings remain the only local
  state touched.
- **Human review awareness**: PASS. Shared score configs make human and judge
  scores comparable.
- **Local-first execution**: PASS. Verification uses `uv run` and local tests.
