# Implementation Plan: LLM-as-Judges

**Branch**: `004-llm-as-judges` | **Date**: 2026-05-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-llm-as-judges/spec.md`

## Summary

Add project-level LLM-as-Judge evaluator setup to the existing headless
evaluation harness. The harness will validate evaluator definitions, prepare
versioned judge prompt assets, synchronize or identify Langfuse score configs,
document Langfuse evaluator filter profiles, and ensure model-output
observations carry metadata required for Langfuse observation-level evaluators.

The feature remains Langfuse-first: Langfuse owns evaluator execution, score
storage, dashboards, and comparisons. The harness prepares configuration,
metadata, prompts, and score targets so users can configure Langfuse evaluators
without building a local judging engine.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `langfuse>=3.0`, `pydantic`, `PyYAML`, `typer`,
`rich`, `pytest`

**Python Environment Management**: Use `uv` for environment creation,
dependency setup, lockfile management, and command execution. Canonical setup is
`uv sync`; canonical run and test commands use `uv run ...`.

**Storage**: Langfuse is the system of record for evaluator execution, score
configs, scores, traces, observations, comparisons, and dashboards. Local files
store project config, evaluator prompt templates, expected result schemas,
documentation, and tests only. No local score database, local judge result
store, or post-run judge-result inspection/export path is introduced for the
MVP.

**Testing**: `pytest` with unit, contract, fake integration, and optional live
integration tests. Default tests must not require Langfuse credentials, live
LLM provider credentials, or network access.

**Target Platform**: Local developer machine and CI runners. Optional live
checks require network access to Langfuse.

**Project Type**: Headless Python CLI.

**Performance Goals**: Evaluator validation and prompt rendering should
complete in under 10 seconds for a normal project. Observation metadata
construction should add negligible overhead relative to provider latency.

**Constraints**: Do not run LLM judges locally in the MVP. Do not build custom
dashboards, aggregate score engines, or a local evaluator scheduler. Default
judge target is the final model-output observation identified by
`observation_role=model_output` and project metadata. The current Azure/OpenAI
provider emits that observation as `OpenAI-generation`, but evaluator filters
must not depend solely on provider-specific observation names. Trace-level
judging is allowed only for evaluators that explicitly require full workflow
context.

**Scale/Scope**: Multiple evaluator definitions per project, one score target
per evaluator dimension shared by automated judges and Human Annotation Queues,
reusable judge prompt files, generated/manual Langfuse evaluator setup
guidance, and validation that evaluator filters are project-scoped and
observation-safe. First concrete project remains `rewrite-quality` with a
clarity judge.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. Langfuse remains responsible for LLM-as-a-Judge
  execution, score writes, dashboards, and comparison. The harness prepares
  evaluator definitions, prompt assets, score configs, and metadata filters.
- **Thin harness scope**: PASS. The feature extends config validation and CLI
  documentation/export paths only. No service runtime, local evaluator engine,
  orchestration framework, or UI is introduced.
- **Dataset simplicity**: PASS. CSV with an `input` column remains valid.
  Optional `ground_truth` continues to be supported only when an evaluator
  requires reference output.
- **Reproducibility metadata**: PASS. Evaluator names, versions, score targets,
  prompt versions, run identity, project identity, dataset identity, and
  observation filter metadata are required on relevant traces/observations.
- **Baseline-centric workflow**: PASS. Baseline and candidate outputs can be
  judged by the same evaluator definitions, and comparisons remain score-based
  in Langfuse.
- **Minimal local state**: PASS. Local state is limited to versioned files in
  the repo. Langfuse remains the store for evaluator results and scores.
- **Human review awareness**: PASS. Human Annotation Queues remain the
  calibration and manual review path for sampled or disputed automated scores.
- **Local-first execution**: PASS. All harness interactions remain runnable
  with `uv run python run_experiment.py ...`.

## Project Structure

### Documentation (this feature)

```text
specs/004-llm-as-judges/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- cli.md
|   `-- langfuse-evaluators.md
`-- checklists/
```

### Source Code (repository root)

```text
configs/
`-- projects/
    `-- rewrite_quality.yaml

prompts/
`-- rewrite_quality/
    |-- task_prompt.md
    `-- evaluators/
        `-- clarity.md

src/
`-- evaluator_harness/
    |-- cli.py
    |-- config.py
    |-- langfuse_client.py
    |-- runner.py
    |-- errors.py
    `-- providers/

tests/
|-- unit/
|-- contract/
|-- integration/
`-- fixtures/

docs/
```

**Structure Decision**: Extend the existing single-package CLI and config model.
Add evaluator setup/validation helpers only where they keep runner and Langfuse
client behavior clear. Keep prompts as project files under `prompts/`.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Use Langfuse observation-level evaluators by default because Langfuse
  currently recommends observations for precise, cost-controlled live
  LLM-as-Judge evaluation.
- Scope evaluator filters primarily with `observation_role=model_output` and
  project metadata rather than full trace names or provider-specific
  observation names. Trace names are item-specific and useful for inspection
  but too granular for evaluator targeting.
- Store filter metadata directly on model-output observations to avoid relying
  on parent trace metadata propagation.
- Keep the expected judge result contract structured with `reasoning`, `score`,
  and `confidence`; the harness validates the setup contract, while Langfuse
  owns evaluator execution and score writes.
- Sync only harness-managed score configs and fail on incompatible schemas.
  LLM-as-Judge evaluators and Human Annotation Queues must share the same
  canonical score config for a given evaluator dimension. Score origin is
  distinguished by Langfuse's native score `source`, normalized by the harness
  as `llm_judge` for `EVAL` and `human_annotation` for `ANNOTATION`.
- Treat Human Annotation Queues as the calibration path, not as a replacement
  for automated scoring.

## Phase 1 Design

See [data-model.md](./data-model.md),
[contracts/cli.md](./contracts/cli.md),
[contracts/langfuse-evaluators.md](./contracts/langfuse-evaluators.md), and
[quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Evaluator config model**: extend project evaluator config with target,
   required inputs, judging mode, blind-by-default flag, non-blind reason,
   prompt reference, output schema, filter profile, and run-type eligibility.
2. **Validation**: reject evaluators without versions, score targets, prompt
   refs, output schema, or project-scoped filter profiles; reject blind prompts
   that expose provider/model placeholders.
3. **Observation metadata**: ensure model-output observations carry the
   metadata needed by evaluator filters, regardless of provider-specific
   observation name.
4. **Prompt setup**: provide versioned evaluator prompt assets and a CLI/docs
   path to render or inspect Langfuse-ready judge prompts.
5. **Score config sync**: reuse existing harness-managed score config sync,
   verify evaluator-to-score mappings, and verify Human Annotation Queue score
   config alignment for the same evaluator dimension.
6. **Langfuse setup guidance**: document the manual Langfuse evaluator setup
   steps and expected filters for each evaluator.
7. **Coverage**: add unit, contract, fake integration, and optional live tests
   for evaluator validation, prompt rendering, score mapping, and observation
   filter metadata.

## Test Strategy

- **Unit tests**: evaluator schema validation, one-dimension enforcement,
  required input validation, blind placeholder rejection, filter profile
  construction, score range validation, shared human/judge score config
  validation, prompt rendering, and observation metadata construction.
- **Contract tests**: CLI validation output for valid/invalid evaluator config,
  prompt rendering/export output, and score config sync with evaluator
  mappings.
- **Fake integration tests**: baseline and candidate runs produce
  observation-level metadata suitable for evaluator filters; score configs are
  reused; Human Annotation Queue and LLM-as-Judge score targets align;
  incompatible configs fail with clear remediation.
- **Live tests**: opt-in smoke checks verify live model-output observations
  expose project filter metadata and live score config sync is compatible with
  the evaluator definitions.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The plan explicitly avoids local judge execution
  and delegates evaluation, scoring, dashboards, and comparisons to Langfuse.
- **Thin harness scope**: PASS. The design adds validation, prompt assets, and
  documentation without a service, UI, queue, or scheduler.
- **Dataset simplicity**: PASS. Existing dataset formats remain valid.
- **Reproducibility metadata**: PASS. Evaluator identity, version, prompt,
  filter, score target, and run metadata are captured in config and
  observations.
- **Baseline-centric workflow**: PASS. Baseline and candidate outputs use the
  same evaluator definitions and compare through Langfuse scores.
- **Minimal local state**: PASS. No new runtime state is introduced.
- **Human review awareness**: PASS. Calibration and dispute workflows continue
  through Langfuse Human Annotation Queues using the same canonical score
  configs as automated judges for each evaluator dimension.
- **Local-first execution**: PASS. Quickstart commands use `uv run python
  run_experiment.py`.

## Complexity Tracking

No constitution violations.
