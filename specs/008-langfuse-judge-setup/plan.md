# Implementation Plan: Langfuse Judge Setup

**Branch**: `008-langfuse-judge-setup` | **Date**: 2026-05-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-langfuse-judge-setup/spec.md`

## Summary

Automate the Langfuse LLM-as-Judge evaluator setup that was previously exported
as manual guidance. The harness will validate evaluator setup definitions,
resolve score configs and judge inputs, create or reuse Langfuse evaluators,
safely update only harness-managed operational fields, inactivate superseded
harness-managed evaluator versions when Langfuse supports it, and persist
non-secret local binding records that prove ownership for later updates.

The design remains Langfuse-first: Langfuse owns evaluator execution, judge
model calls, score writes, dashboards, backfill execution, and comparisons. The
harness only prepares and applies Langfuse configuration, then reports the
effective target, filters, variables, score target, judge model/connection,
sampling, backfill policy, activation state, and binding status.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `langfuse>=3.0`, `pydantic`, `PyYAML`, `typer`,
`rich`, `pytest`

**Python Environment Management**: Use `uv` for environment creation,
dependency setup, lockfile management, and command execution. Canonical setup is
`uv sync`; canonical run and test commands use `uv run ...`.

**Storage**: Langfuse remains the system of record for evaluator execution,
scores, traces, observations, dashboards, and comparisons. Local storage is
limited to project YAML, prompt files, generated setup reports, tests, and a
non-secret evaluator binding file that maps project evaluator identities to
remote Langfuse evaluator IDs created or updated by the harness.

**Testing**: `pytest` with unit, contract, fake integration, and optional live
integration tests. Default tests must not require Langfuse credentials, live
LLM provider credentials, or network access.

**Target Platform**: Local developer machine and CI runners. Optional live
checks require network access to Langfuse.

**Project Type**: Headless Python CLI.

**Performance Goals**: Preview/audit should complete in under 10 seconds for a
normal project using fake clients. Apply should add negligible local overhead
relative to Langfuse service latency and should report per-evaluator status for
all evaluators in a project.

**Constraints**: Do not run judge LLM calls locally. Do not implement a local
evaluator scheduler, score store, dashboard, or comparison engine. Do not
delete Langfuse evaluators. Do not mutate user-owned evaluators. Do not rely on
Langfuse evaluator metadata for ownership because current docs do not establish
that evaluator resources expose arbitrary metadata. Default evaluation target
remains observation-level model-output data; trace and experiment targets are
allowed only when explicitly configured.

**Scale/Scope**: Multiple evaluator setup definitions per project; one
canonical score config per evaluator dimension shared by LLM-as-Judge and Human
Annotation Queues; support for Langfuse catalog evaluators and custom
project-defined evaluators; project-level judge model/connection defaults with
evaluator-level overrides; local binding records for harness-managed evaluator
ownership; no historical backfill unless explicitly requested and supported by
Langfuse.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. Langfuse remains responsible for LLM-as-a-Judge
  execution, judge model calls, score writes, dashboards, comparisons, and
  backfill execution. The harness configures Langfuse resources only.
- **Thin harness scope**: PASS. The feature extends the existing Python CLI,
  config model, Langfuse client wrapper, and report helpers. No service,
  scheduler, dashboard, orchestration framework, or local API is introduced.
- **Dataset simplicity**: PASS. Existing CSV and Langfuse dataset workflows are
  preserved. No new dataset shape is required for evaluator setup.
- **Reproducibility metadata**: PASS. Evaluator identity, evaluator version,
  source type, target, score target, prompt/catalog reference, judge
  model/connection, filters, sampling, backfill policy, and binding status are
  captured in setup summaries and binding records.
- **Baseline-centric workflow**: PASS. Baseline and candidate runs remain
  comparable in Langfuse through the same evaluator dimensions and score
  configs. This feature does not alter baseline selection or comparison logic.
- **Minimal local state**: PASS. Local binding records are non-secret project
  artifacts required to prove ownership for safe update/inactivation; Langfuse
  remains the system of record for evaluator execution and scores.
- **Human review awareness**: PASS. Existing Human Annotation Queue alignment
  remains required for evaluator score targets.
- **Local-first execution**: PASS. New workflows remain runnable through
  `uv run python run_experiment.py ...`.

## Project Structure

### Documentation (this feature)

```text
specs/008-langfuse-judge-setup/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- cli.md
|   `-- langfuse-evaluator-setup.md
|-- checklists/
|   `-- requirements.md
`-- spec.md
```

### Source Code (repository root)

```text
configs/
|-- langfuse/
|   `-- evaluator_bindings/
|       `-- rewrite-quality.yaml
`-- projects/
    `-- rewrite_quality.yaml

prompts/
`-- rewrite_quality/
    `-- evaluators/
        `-- clarity.md

src/
`-- evaluator_harness/
    |-- cli.py
    |-- config.py
    |-- evaluators.py
    |-- langfuse_client.py
    |-- langfuse_evaluator_setup.py
    |-- evaluator_bindings.py
    |-- annotation_queues.py
    |-- runner.py
    `-- errors.py

tests/
|-- unit/
|-- contract/
|-- integration/
`-- fixtures/
```

**Structure Decision**: Extend the existing single-package CLI and config
model. Add focused helper modules for evaluator setup planning/apply/audit and
binding-file persistence so `langfuse_client.py` remains a thin Langfuse
adapter and `runner.py` remains workflow orchestration.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Use Langfuse observation-level evaluators by default because Langfuse
  recommends observations for precise, lower-latency live evaluation.
- Support both Langfuse catalog evaluators and custom evaluators, matching the
  Langfuse setup flow.
- Require a project-level default judge model/LLM connection or an
  evaluator-level override. Langfuse docs state LLM-as-Judge setup requires an
  LLM Connection and that structured output support matters.
- Default sampling to 100% matching observations when not configured, but show
  the effective sampling policy in preview/apply/audit summaries.
- Disable historical backfill by default. Allow explicit opt-in only when
  Langfuse supports it for the selected target; otherwise block with
  remediation.
- Use local non-secret binding records plus remote compatibility checks for
  ownership proof. Do not depend on evaluator metadata unless Langfuse exposes
  it.
- Apply evaluator setup independently per evaluator, preserving successful
  changes and reporting failures without rollback or deletes.

## Phase 1 Design

See [data-model.md](./data-model.md),
[contracts/cli.md](./contracts/cli.md),
[contracts/langfuse-evaluator-setup.md](./contracts/langfuse-evaluator-setup.md),
and [quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Config model**: add evaluator setup source type, catalog reference,
   custom prompt setup, judge model/connection defaults and overrides, sampling
   policy, historical backfill policy, and binding path defaults.
2. **Binding records**: add non-secret local binding file load/save, schema
   validation, compatibility checks, and status reporting.
3. **Setup planner**: produce preview plans with create/reuse/update/
   inactivate/skip/block/fail decisions, managed evaluator names, score target
   IDs, variables, filters, judge model/connection, sampling, backfill, and
   binding status.
4. **Langfuse apply/audit adapter**: add fake-client and live-client surfaces
   for listing, creating, updating operational fields, inactivating when
   supported, and auditing evaluator resources. Fail clearly when the current
   Langfuse SDK/API surface cannot perform a requested operation.
5. **CLI**: add `sync-judge-evaluators` with `--dry-run`, `--audit`, and
   default apply modes; update validate/export commands to include setup
   readiness and effective setup policies.
6. **Docs and examples**: update project YAML examples, generated setup report,
   quickstart, README/user guide, and automation backlog.
7. **Coverage**: add unit, contract, fake integration, and optional live tests
   for config validation, setup planning, binding persistence, partial success,
   idempotency, update/inactivation safety, and CLI output.

## Test Strategy

- **Unit tests**: config schema defaults and overrides; managed evaluator name
  generation; catalog/custom validation; sampling and backfill defaults;
  binding schema and compatibility; safe-update field detection; user-owned
  mutation rejection; historical backfill unsupported failure; judge
  model/connection selection.
- **Contract tests**: CLI output for dry-run, apply, audit, partial success,
  missing judge model/connection, missing binding, unsupported backfill, and
  incompatible remote evaluator.
- **Fake integration tests**: fake Langfuse client create/reuse/update/
  inactivate paths; no rollback on partial failure; binding file creation and
  refresh; score config alignment with Human Annotation Queues; repeated apply
  idempotency.
- **Live tests**: opt-in smoke check to verify the current Langfuse SDK/API can
  create or resolve evaluator setup for a disposable project. Live tests must
  skip or fail with a precise message if evaluator creation/update is not
  exposed by the installed Langfuse surface.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The design delegates evaluator execution, judge
  model calls, score writes, dashboards, comparisons, and backfill execution to
  Langfuse.
- **Thin harness scope**: PASS. The design adds CLI/config/client helpers only;
  no service, scheduler, dashboard, or local evaluator engine.
- **Dataset simplicity**: PASS. Existing dataset formats remain valid.
- **Reproducibility metadata**: PASS. Setup summaries and binding records
  capture evaluator identity, versions, target, filters, score target,
  prompt/catalog reference, judge model/connection, sampling, backfill, and
  binding status.
- **Baseline-centric workflow**: PASS. Baseline/candidate comparison remains
  score-based in Langfuse with shared evaluator dimensions.
- **Minimal local state**: PASS. The only new persistent state is a non-secret
  binding file required for safe ownership checks.
- **Human review awareness**: PASS. Human Annotation Queues remain aligned to
  canonical score configs, while automated judge scores are compared by
  evaluator dimension, evaluator score name, and Langfuse score source.
- **Local-first execution**: PASS. Commands use `uv run python run_experiment.py`.

## Complexity Tracking

No constitution violations.
