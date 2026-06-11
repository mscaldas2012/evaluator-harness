# Implementation Plan: Langfuse Item Comparison Sessions

**Branch**: `017-item-comparison-sessions` | **Date**: 2026-06-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/017-item-comparison-sessions/spec.md`

## Summary

Add official Langfuse session grouping to project runs so each dataset item has
one comparison session containing the baseline trace and candidate trace(s) for
the same baseline anchor. The implementation will compute a deterministic,
Langfuse-valid session identifier from existing project, dataset, baseline, and
item identity fields; pass that identifier through the official Langfuse
session field when traces are logged; and retain it in metadata/export output
for diagnostics. Run IDs and baseline references remain the authoritative model
for reports and aggregate comparisons.

## Technical Context

**Language/Version**: Python >=3.11

**Primary Dependencies**: Pydantic, Typer, Rich, PyYAML, pytest, Langfuse SDK;
existing provider dependencies remain unchanged

**Python Environment Management**: Use `uv` for environment management,
dependency setup, lockfile management, and command execution. Prefer `uv sync`
and `uv run ...`.

**Storage**: Langfuse traces/sessions and existing local report/export files;
no database or new durable local state

**Testing**: pytest unit, integration, and CLI contract tests

**Target Platform**: Local CLI execution on developer machines with optional
live Langfuse connectivity

**Project Type**: Python CLI evaluation harness

**Performance Goals**: Session ID computation must be deterministic and
constant-time per trace, adding no noticeable latency to dataset runs.

**Constraints**: Use the official Langfuse session field, not only metadata;
session identifiers must be US-ASCII and under 200 characters; preserve existing
run metadata, baseline references, evaluator targeting, and report behavior.

**Scale/Scope**: Applies to baseline and candidate project runs that log
model-generation traces. Typical datasets are tens to hundreds of items, with
multiple candidate runs comparing against one baseline.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The design uses Langfuse-native sessions for trace
  grouping and does not replace Langfuse trace inspection, scores, dashboards,
  or comparisons.
- **Thin harness scope**: PASS. The change is limited to deterministic session
  identity generation and existing trace logging paths. No services,
  schedulers, APIs, or orchestration are introduced.
- **Dataset simplicity**: PASS. CSV dataset support and the existing
  `input`-column contract remain unchanged.
- **Reproducibility metadata**: PASS. Existing run, dataset, prompt, evaluator,
  provider, model, parameter, timing, and baseline metadata are preserved.
  Session ID is added as correlation metadata, not as a replacement.
- **Baseline-centric workflow**: PASS. Candidate sessions are anchored to an
  explicit baseline reference, and candidate validation fails when no baseline
  reference exists.
- **Minimal local state**: PASS. No new local state store is added; the
  computed session ID is derived from existing run context.
- **Human review awareness**: PASS. Review items retain trace links and gain a
  Langfuse session grouping that helps reviewers inspect same-item context.
- **Local-first execution**: PASS. Feature remains runnable through existing
  `uv run python run_experiment.py ...` commands.

## Project Structure

### Documentation (this feature)

```text
specs/017-item-comparison-sessions/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- session-logging-contract.md
|-- checklists/
|   `-- requirements.md
`-- spec.md
```

### Source Code (repository root)

```text
src/evaluator_harness/
|-- runner.py              # compute and propagate item comparison sessions
|-- langfuse_client.py     # pass official session field to live Langfuse traces
|-- exports.py             # include diagnostic session ID in CSV exports
`-- errors.py              # existing ConfigError/LangfuseError behavior reused

tests/
|-- unit/
|   |-- test_session_identity.py
|   `-- test_live_trace_metadata.py
|-- integration/
|   `-- test_item_comparison_sessions.py
`-- contract/
    `-- test_cli_item_comparison_sessions.py
```

**Structure Decision**: Use the existing single Python CLI structure. Put the
session identity helper close to run/trace construction, keep Langfuse SDK field
mapping inside `LangfuseClient`, and add focused tests for identity generation,
baseline/candidate grouping, export visibility, and missing-baseline failure.

## Complexity Tracking

No constitution violations.

## Phase 0: Research

See [research.md](research.md).

## Phase 1: Design And Contracts

See [data-model.md](data-model.md), [contracts/session-logging-contract.md](contracts/session-logging-contract.md), and [quickstart.md](quickstart.md).

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The design uses the official Langfuse session
  contract and only stores the same ID in metadata for diagnostics.
- **Thin harness scope**: PASS. The implementation remains a small extension of
  existing runner and client code.
- **Dataset simplicity**: PASS. Dataset shape and sync behavior do not change.
- **Reproducibility metadata**: PASS. Run metadata remains authoritative and
  complete; session ID is an added correlation field.
- **Baseline-centric workflow**: PASS. Candidate runs without explicit baseline
  references fail before session logging.
- **Minimal local state**: PASS. Session IDs are derived and logged, not stored
  in a new local registry.
- **Human review awareness**: PASS. Human Annotation Queue selection behavior is
  unchanged while trace context becomes easier to inspect in Langfuse.
- **Local-first execution**: PASS. Verification uses existing `uv run` commands.
