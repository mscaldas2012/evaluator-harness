# Implementation Plan: Model Output Observation Targeting

**Branch**: `015-model-output-targeting` | **Date**: 2026-06-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/015-model-output-targeting/spec.md`

## Summary

Ensure each completed dataset item contributes exactly one evaluator-targetable
final model output observation to Langfuse. The implementation will preserve
the existing observation-level evaluator filters by making `model_output` a
provider-neutral final-output role, moving parent/container observations to a
non-model-output role, and documenting the provider integration contract for
manual and native Langfuse tracing paths.

## Technical Context

**Language/Version**: Python >=3.11

**Primary Dependencies**: Langfuse SDK/API, Pydantic, Typer, Rich, HTTPX,
PyYAML, pytest

**Python Environment Management**: Use `uv` for environment management,
dependency setup, lockfile management, and command execution. Prefer `uv sync`
and `uv run ...`.

**Storage**: Langfuse is the system of record; local files only for project
YAML, prompts, datasets, bindings, and test fixtures.

**Testing**: pytest unit, integration, contract, and optional live smoke tests

**Target Platform**: Local CLI execution on developer machines; no hosted
service required.

**Project Type**: Python CLI evaluation harness with provider adapters

**Performance Goals**: Avoid duplicate evaluator matches and duplicated judge
execution; no additional model calls or extra Langfuse writes beyond existing
trace structure.

**Constraints**: Keep evaluator filters provider-neutral; preserve dry-run
verification; preserve existing Langfuse-native trace, score, evaluator, and
human review workflows.

**Scale/Scope**: Applies to all new baseline and candidate traces created by
the harness and to provider adapters that participate in harness tracing.
Historical traces are not rewritten.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The design keeps Langfuse traces, observations,
  evaluator rules, scores, dashboards, and comparisons as the system of record.
  Manual tracing remains limited to provider paths that already use it.
- **Thin harness scope**: PASS. The change stays within existing runner,
  provider metadata, evaluator filter, docs, and tests. No services or new
  orchestration are introduced.
- **Dataset simplicity**: PASS. CSV datasets with an `input` column remain the
  default and dataset loading is unchanged.
- **Reproducibility metadata**: PASS. The existing metadata contract is
  preserved and clarified; parent and final-output roles become more explicit.
- **Baseline-centric workflow**: PASS. Baseline generation, candidate
  comparison, and Langfuse comparison remain unchanged.
- **Minimal local state**: PASS. No database or durable local service is added.
- **Human review awareness**: PASS. Score config alignment and Human Annotation
  Queue comparison workflows remain intact.
- **Local-first execution**: PASS. The feature is runnable through existing
  `uv run python run_experiment.py ...` commands.

## Project Structure

### Documentation (this feature)

```text
specs/015-model-output-targeting/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- provider-final-output-contract.md
|-- checklists/
|   `-- requirements.md
`-- spec.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
|-- runner.py                  # run metadata and trace/span role assignment
|-- evaluators.py              # evaluator target summaries and validation hooks
|-- langfuse_client.py          # trace/generation span helpers and fake state
|-- providers/
|   |-- base.py                 # provider response/request metadata contract
|   |-- openai_compatible.py    # manual generation span path
|   |-- dry_run.py              # local verification path
|   `-- ollama.py               # manual/non-SDK provider path
`-- config.py                   # evaluator target config model

tests/
|-- unit/
|   |-- test_progress_reporting.py
|   |-- test_config.py
|   `-- test_provider_tracing_metadata.py
|-- integration/
|   `-- test_model_output_targeting.py
|-- contract/
|   `-- test_cli_run_baseline.py
`-- fixtures/
```

**Structure Decision**: Use the existing single Python CLI structure. Add or
extend focused tests near runner/provider/evaluator behavior; avoid new modules
unless the metadata contract becomes duplicated enough to justify a small helper.

## Complexity Tracking

No constitution violations.

## Phase 0: Research

See [research.md](research.md).

## Phase 1: Design And Contracts

See [data-model.md](data-model.md), [contracts/provider-final-output-contract.md](contracts/provider-final-output-contract.md), and [quickstart.md](quickstart.md).

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The contract uses Langfuse observations and
  metadata rather than local score processing or custom dashboards.
- **Thin harness scope**: PASS. The design updates metadata assignment and
  provider contract documentation in the existing CLI.
- **Dataset simplicity**: PASS. Dataset format remains unchanged.
- **Reproducibility metadata**: PASS. The final-output role is additive and
  clarifies trace semantics.
- **Baseline-centric workflow**: PASS. Baseline/candidate lifecycle remains
  unchanged.
- **Minimal local state**: PASS. No new state store.
- **Human review awareness**: PASS. Human/eval score comparison remains the
  same and benefits from avoiding duplicate judge scores.
- **Local-first execution**: PASS. Verification uses existing `uv run` commands.
